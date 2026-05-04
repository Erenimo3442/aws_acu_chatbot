"""Web scraping processor for Acibadem University pages.

Handles two site architectures:
  - acibadem.edu.tr  : Drupal CMS — requests + BeautifulSoup
  - obs.acibadem.edu.tr: ASP.NET/Bologna — direct dynConPage.aspx access

Design decisions:
  - No JavaScript/Playwright needed for ongoing scraping — all content
    is accessible via direct HTTP requests (URLs discovered via one-time
    Playwright exploration on 2026-05-04).
  - Extracts main content only, strips navigation/footer/boilerplate.
  - Content deduplication via SHA-256 fingerprinting.
"""

import hashlib
import os
import re
from logging import getLogger

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = getLogger(__name__)

# Graceful degradation if scraping deps are missing
try:
    import requests
    from bs4 import BeautifulSoup

    HAS_SCRAPER_DEPS = True
except ImportError:
    HAS_SCRAPER_DEPS = False
    requests = None  # type: ignore
    BeautifulSoup = None  # type: ignore


# ---------------------------------------------------------------------------
# Boilerplate removal patterns
# ---------------------------------------------------------------------------

# CSS selectors for elements to remove before text extraction
BOILERPLATE_SELECTORS = [
    "script", "style", "noscript",
    "nav", "header", "footer",
    ".nav", ".navbar", ".menu", ".sidebar",
    '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
    ".breadcrumb", ".pager",
    # Social media / sharing widgets
    ".social-links", ".share-links",
    # Cookie banners, popups
    ".cookie-banner", ".popup",
]

# Tag names to decompose entirely (and their children)
BOILERPLATE_TAG_NAMES = {"script", "style", "noscript", "nav", "header", "footer"}


# ---------------------------------------------------------------------------
# Web Scrape Processor
# ---------------------------------------------------------------------------


class WebScrapeProcessor:

    def __init__(self):
        self.default_chunk_size = int(os.getenv("CHUNK_SIZE", "600"))
        self.default_chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "120"))
        self.min_content_length = int(os.getenv("MIN_CONTENT_LENGTH", "40"))
        self.request_timeout = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "20"))
        self._session: "requests.Session | None" = None

    # ------------------------------------------------------------------
    # HTTP session (lazy)
    # ------------------------------------------------------------------

    def _get_session(self) -> "requests.Session":
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": (
                    "ACUChatbot/1.0 (university-project; educational-use-only; "
                    "contact: info@acibadem.edu.tr)"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en,tr;q=0.9",
            })
        return self._session

    # ------------------------------------------------------------------
    # Text normalization
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        """Remove control chars and collapse whitespace."""
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", str(text))
        return re.sub(r"\s+", " ", cleaned).strip()

    def _normalize_source(self, source: str) -> str:
        normalized = str(source).strip()
        return normalized or "manual_input"

    def _content_fingerprint(self, source: str, content: str) -> str:
        return hashlib.sha256(
            f"{source}|{content.lower()}".encode("utf-8")
        ).hexdigest()

    # ------------------------------------------------------------------
    # Boilerplate removal
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_boilerplate(soup: "BeautifulSoup") -> "BeautifulSoup":
        """Remove navigation, header, footer, scripts, and other non-content
        elements from the parse tree.  Mutates soup in-place."""
        # Tag-name based removal
        for tag_name in BOILERPLATE_TAG_NAMES:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # CSS-selector based removal (classes / attributes)
        for selector in BOILERPLATE_SELECTORS:
            try:
                for tag in soup.select(selector):
                    tag.decompose()
            except Exception:
                pass  # Some selectors may not be supported by html.parser

        return soup

    # ------------------------------------------------------------------
    #  Site A — Drupal (acibadem.edu.tr)
    # ------------------------------------------------------------------

    def fetch_drupal_page(self, url: str, title: str = "",
                          source_tag: str = "") -> Document | None:
        """Fetch a single Drupal page and return a cleaned LangChain Document.

        Strategy:
          1. HTTP GET the page
          2. Parse HTML
          3. Strip boilerplate (header, footer, nav, sidebar)
          4. Extract text content from <main> (fallback to <body>)
          5. Build Document with rich metadata
        """
        if not HAS_SCRAPER_DEPS:
            logger.warning("requests/BeautifulSoup not installed; cannot scrape")
            return None

        logger.info("Fetching Drupal page: %s", url)
        try:
            resp = self._get_session().get(url, timeout=self.request_timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Failed to fetch %s: %s (%s)", url, type(exc).__name__, exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        self._remove_boilerplate(soup)

        # Prefer <main> content; fall back to <body>
        main = soup.find("main") or soup.find("body")
        if main is None:
            logger.warning("No <main> or <body> found in %s", url)
            return None

        # Extract text with sensible newline separation
        text = main.get_text(separator="\n", strip=True)
        cleaned = self._normalize_text(text)

        if len(cleaned) < self.min_content_length:
            logger.warning("Skipping %s: content too short (%d chars)", url, len(cleaned))
            return None

        # Title resolution
        resolved_title = title or (
            soup.title.string.strip() if soup.title else url.rstrip("/").split("/")[-1] or "Untitled"
        )
        resolved_source = source_tag or url

        return Document(
            page_content=cleaned,
            metadata={
                "title": self._normalize_text(resolved_title),
                "source": resolved_source,
                "url": url,
                "ingestion_type": "drupal_scrape",
                "content_type": resp.headers.get("Content-Type", ""),
            },
        )

    def fetch_drupal_page_and_ingest(self, url: str, title: str = "",
                                     source_tag: str = "") -> dict:
        """Fetch a Drupal page, chunk it, and return ingestion status."""
        doc = self.fetch_drupal_page(url, title=title, source_tag=source_tag)
        if doc is None:
            return {"status": "failed", "url": url, "title": title, "chunk_count": 0}

        chunks = self.split_documents_into_chunks([doc])
        if not chunks:
            return {"status": "failed", "url": url, "title": title, "chunk_count": 0}

        return {
            "status": "ingested",
            "url": url,
            "title": title,
            "chunk_count": len(chunks),
            "chunks": chunks,
        }

    # ------------------------------------------------------------------
    #  Site B — Bologna / ASP.NET (obs.acibadem.edu.tr)
    # ------------------------------------------------------------------

    def fetch_bologna_static_page(self, url: str, title: str = "",
                                   source_tag: str = "") -> Document | None:
        """Fetch a Bologna dynConPage.aspx static page.

        These pages are ASP.NET WebForms — content lives inside <form> tags.
        Do NOT decompose forms or we lose all text.
        """
        if not HAS_SCRAPER_DEPS:
            logger.warning("requests/BeautifulSoup not installed; cannot scrape")
            return None

        logger.info("Fetching Bologna page: %s", url)
        try:
            resp = self._get_session().get(url, timeout=self.request_timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Failed to fetch %s: %s (%s)", url, type(exc).__name__, exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        body = soup.find("body")
        if body is None:
            logger.warning("No <body> in %s", url)
            return None

        # Remove only empty/hidden form elements, not the main content form
        for form_tag in body.find_all("form"):
            form_text = self._normalize_text(form_tag.get_text())
            if len(form_text) < 20:  # Empty or nearly empty form
                form_tag.decompose()

        # Also strip boilerplate (scripts, styles, Bootstrap nav elements)
        self._remove_boilerplate(soup)

        text = body.get_text(separator="\n", strip=True)
        cleaned = self._normalize_text(text)

        if len(cleaned) < self.min_content_length:
            logger.warning("Skipping %s: content too short (%d chars)", url, len(cleaned))
            return None

        resolved_title = title or (
            soup.title.string.strip() if soup.title else url.split("/")[-1]
        )
        resolved_source = source_tag or url

        return Document(
            page_content=cleaned,
            metadata={
                "title": self._normalize_text(resolved_title),
                "source": resolved_source,
                "url": url,
                "ingestion_type": "bologna_static",
                "content_type": resp.headers.get("Content-Type", ""),
            },
        )

    def fetch_bologna_program_listing(self, url: str, degree_level: str
                                      ) -> list[dict] | None:
        """Fetch a unitSelection.aspx page and extract program links.

        Returns list of dicts with keys: cur_unit, cur_sunit, program_name, url
        These can be fed into fetch_bologna_program_detail().
        """
        if not HAS_SCRAPER_DEPS:
            logger.warning("requests/BeautifulSoup not installed; cannot scrape")
            return None

        logger.info("Fetching Bologna program listing: %s (%s)", url, degree_level)
        try:
            resp = self._get_session().get(url, timeout=self.request_timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        programs: list[dict] = []

        # Program links have pattern: index.aspx?lang=en&curOp=showPac&curUnit=X&curSunit=Y
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "curOp=showPac" not in href and "curSunit=" not in href:
                continue

            # Extract query parameters
            params: dict[str, str] = {}
            if "?" in href:
                query_string = href.split("?", 1)[1]
                for pair in query_string.split("&"):
                    if "=" in pair:
                        key, val = pair.split("=", 1)
                        params[key] = val

            cur_unit_str = params.get("curUnit", "")
            cur_sunit_str = params.get("curSunit", "")

            if not cur_sunit_str:
                continue

            try:
                cur_unit = int(cur_unit_str) if cur_unit_str else 0
                cur_sunit = int(cur_sunit_str)
            except ValueError:
                continue

            program_name = self._normalize_text(link.get_text())

            # Avoid duplicates
            if any(p["cur_sunit"] == cur_sunit for p in programs):
                continue

            programs.append({
                "cur_unit": cur_unit,
                "cur_sunit": cur_sunit,
                "program_name": program_name,
                "degree_level": degree_level,
                "url": f"{url.rsplit('/', 1)[0]}/{href.lstrip('/')}"
                       if not href.startswith("http")
                       else href,
            })

        logger.info("Found %d programs for %s", len(programs), degree_level)
        return programs

    def fetch_bologna_program_detail(self, url: str, title: str = ""
                                     ) -> Document | None:
        """Fetch a single Bologna program detail sub-page.

        These are ASP.NET pages — content lives inside <form> tags.
        Do NOT decompose the main form or we lose all text.
        """
        if not HAS_SCRAPER_DEPS:
            return None

        logger.info("Fetching Bologna program detail: %s", url)
        try:
            resp = self._get_session().get(url, timeout=self.request_timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Failed to fetch %s: %s (%s)", url, type(exc).__name__, exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove only empty/hidden forms, not content forms
        for form_tag in soup.find_all("form"):
            form_text = self._normalize_text(form_tag.get_text())
            if len(form_text) < 20:
                form_tag.decompose()

        self._remove_boilerplate(soup)

        body = soup.find("body")
        if body is None:
            return None

        text = body.get_text(separator="\n", strip=True)
        cleaned = self._normalize_text(text)

        if len(cleaned) < self.min_content_length:
            logger.warning("Skipping %s: content too short (%d chars)", url, len(cleaned))
            return None

        resolved_title = title or (soup.title.string.strip() if soup.title else url)

        return Document(
            page_content=cleaned,
            metadata={
                "title": self._normalize_text(resolved_title),
                "source": url,
                "url": url,
                "ingestion_type": "bologna_program_detail",
                "content_type": resp.headers.get("Content-Type", ""),
            },
        )

    # ------------------------------------------------------------------
    #  Chunking
    # ------------------------------------------------------------------

    def split_documents_into_chunks(self, documents: list[Document]) -> list[Document]:
        """Split documents into overlapping chunks for embedding."""
        logger.info("Splitting %d documents into chunks (chunk_size=%d, overlap=%d)...",
                     len(documents), self.default_chunk_size, self.default_chunk_overlap)
        if not documents:
            return []

        for i, doc in enumerate(documents):
            logger.info("  Doc %d: %d chars, title=%s", i,
                        len(doc.page_content), doc.metadata.get("title", "?")[:60])

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.default_chunk_size,
            chunk_overlap=self.default_chunk_overlap,
        )
        chunks = splitter.split_documents(documents)
        logger.info("  → %d chunks created", len(chunks))
        return chunks

    # ------------------------------------------------------------------
    #  Legacy: demo seed documents
    # ------------------------------------------------------------------

    def _build_demo_documents(self) -> list[Document]:
        """Demo-safe starter set for first-stage ingestion."""
        raw_docs = [
            {
                "title": "ACU General Overview",
                "source": "https://www.acibadem.edu.tr",
                "content": (
                    "Acibadem University is a foundation university in Istanbul. "
                    "The university provides undergraduate and graduate education in multiple disciplines "
                    "with a strong focus on health sciences and technology."
                ),
            },
            {
                "title": "Admission and Application Context",
                "source": "https://www.acibadem.edu.tr/en/prospective-students",
                "content": (
                    "Prospective students can find admission-related announcements, application details, "
                    "and program-specific requirements on the official university website."
                ),
            },
            {
                "title": "Bologna Information System",
                "source": "https://obs.acibadem.edu.tr",
                "content": (
                    "The Bologna information system provides curriculum data, course descriptions, "
                    "credit information, and learning outcomes for academic programs."
                ),
            },
            {
                "title": "Campus and Student Life",
                "source": "https://www.acibadem.edu.tr/en/life-at-acibadem",
                "content": (
                    "Campus life pages include information on student services, social opportunities, "
                    "and support resources available at Acibadem University."
                ),
            },
        ]

        documents: list[Document] = []
        for item in raw_docs:
            cleaned = self._normalize_text(item["content"])
            documents.append(
                Document(
                    page_content=cleaned,
                    metadata={
                        "title": item["title"],
                        "source": item["source"],
                        "ingestion_type": "demo_seed",
                    },
                )
            )
        return documents

    # ------------------------------------------------------------------
    #  Legacy: payload-based document building
    # ------------------------------------------------------------------

    def build_documents_from_payload(
        self, items: list[dict]
    ) -> tuple[list[Document], dict]:
        """Validate, clean, and deduplicate ingestion payload into LangChain documents."""
        stats = {
            "received": len(items),
            "accepted": 0,
            "skipped_non_dict": 0,
            "skipped_empty": 0,
            "skipped_too_short": 0,
            "skipped_duplicate": 0,
        }

        documents: list[Document] = []
        seen_fingerprints: set[str] = set()

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                stats["skipped_non_dict"] += 1
                continue

            cleaned_content = self._normalize_text(item.get("content", ""))
            if not cleaned_content:
                stats["skipped_empty"] += 1
                continue

            if len(cleaned_content) < self.min_content_length:
                stats["skipped_too_short"] += 1
                continue

            source = self._normalize_source(item.get("source", "manual_input"))
            fingerprint = self._content_fingerprint(source, cleaned_content)
            if fingerprint in seen_fingerprints:
                stats["skipped_duplicate"] += 1
                continue
            seen_fingerprints.add(fingerprint)

            title = self._normalize_text(item.get("title", "")) or f"Custom Document {index}"
            documents.append(
                Document(
                    page_content=cleaned_content,
                    metadata={
                        "title": title,
                        "source": source,
                        "ingestion_type": "api_payload",
                    },
                )
            )

        stats["accepted"] = len(documents)
        return documents, stats

    # ------------------------------------------------------------------
    #  Legacy: process_all_documents
    # ------------------------------------------------------------------

    def process_all_documents(self) -> tuple[list[Document], int]:
        """Process all demo documents and return list of chunks and document count."""
        documents = self._build_demo_documents()
        chunks = self.split_documents_into_chunks(documents)
        return chunks, len(documents)
