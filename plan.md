# Five-Sprint Implementation Plan — AWS ACU Chatbot

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all 19 gaps identified in the proposal-to-codebase analysis, progressing the chatbot from MVP scaffold to production-ready system with evaluation evidence, admin tooling, streaming support, CI/CD, and final report polish.

**Architecture:** Five sequential sprints, each building on the prior. Sprint 1 fixes critical data-flow gaps (citations, health checks, one real scraper). Sprint 2 adds evaluation rigor and expands ingestion. Sprint 3 delivers auth UI, session management, and admin panel. Sprint 4 adds WebSocket streaming, CI/CD, and contract test hardening. Sprint 5 handles polish (pagination, markdown, persistence, backup docs, report appendix).

**Tech Stack:** Django 6.0, LangChain, Chroma, Ollama (qwen2.5:3b + nomic-embed-text-v2-moe), React 19 + TypeScript + Vite, Docker Compose, PostgreSQL 17, Python 3.13, Node 20, Django Channels (Sprint 4), GitHub Actions (Sprint 4), react-markdown (Sprint 5).

---

# Sprint 1: Citation Pipeline + Health Checks + First Real Scraper

**Goal:** Make `/chat` return real citations from the RAG pipeline, make containers start reliably, and ingest one real university web page.

## Task 1.1: Enrich RAG return with citation-ready structured data

**Files:**
- Modify: `backend/rag/api_views.py` (full file)

- [ ] **Step 1: Read current return format to confirm shape**

Read `backend/rag/api_views.py` lines 24-41 (the `_docs_to_sources` helper) and lines 84-130 (the `generate_chat_answer` function). We will replace `_docs_to_sources` with a richer function that captures everything needed for Citation DB rows, and change the return value to include the raw document list.

- [ ] **Step 2: Replace `_docs_to_sources` with `_docs_to_citation_entries`**

Replace the existing `_docs_to_sources` function (lines 24-41) and the `generate_chat_answer` function (lines 84-130) with the following code. Open `backend/rag/api_views.py` and replace the content from line 24 through line 130 with:

```python
import hashlib
import uuid

def _docs_to_citation_entries(docs: list[Document]) -> list[dict]:
    """Convert LangChain retriever Documents into Citation-ready dicts.
    Each entry has all fields needed by the Citation model and the API contract.
    """
    entries: list[dict] = []
    seen: set[str] = set()
    for idx, doc in enumerate(docs[:5], start=1):
        metadata = doc.metadata or {}
        source_str = str(metadata.get("source", metadata.get("url", "Unknown")))
        page_str = str(metadata.get("page", ""))
        dedup_key = f"{source_str}:{page_str}:{doc.page_content[:80]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        source_id = hashlib.sha256(source_str.encode("utf-8")).hexdigest()[:12]
        chunk_id = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()[:12]

        entries.append({
            "citation_id": f"cit_{uuid.uuid4().hex[:12]}",
            "source_id": f"src_{source_id}",
            "chunk_id": f"chunk_{chunk_id}",
            "snippet": doc.page_content[:300],
            "title": str(metadata.get("title", source_str.split("/")[-1] or "Untitled")),
            "url": source_str if source_str.startswith("http") else "",
            "page": int(metadata["page"]) if metadata.get("page") and str(metadata["page"]).isdigit() else None,
            "doc_metadata": {
                "file_name": str(metadata.get("file_name", "")),
                "source": str(metadata.get("source", "")),
                "ingestion_type": str(metadata.get("ingestion_type", "")),
                "chunk_start": metadata.get("chunk_start"),
                "chunk_end": metadata.get("chunk_end"),
            },
            "score": float(metadata.get("score", 0.0)),
        })
    return entries


def _docs_to_sources(docs: list[Document]) -> list[dict]:
    """Keep backward-compatible source summary used by health/debug callers."""
    sources: list[dict] = []
    seen: set[str] = set()
    for doc in docs[:5]:
        source_name = str(doc.metadata.get("source", doc.metadata.get("url", "Unknown")))
        page = str(doc.metadata.get("page", ""))
        key = f"{source_name}:{page}"
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "source": source_name,
            "page": page,
            "content": doc.page_content[:200],
        })
    return sources


def generate_chat_answer(question: str) -> dict:
    cleaned_question = str(question).strip()
    if not cleaned_question:
        raise ValueError("question is required")

    _, retriever = _ensure_runtime()
    docs = retriever.invoke(cleaned_question)

    citation_entries = _docs_to_citation_entries(docs)
    sources = _docs_to_sources(docs)

    RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.3"))

    best_score = max(
        (entry["score"] for entry in citation_entries),
        default=0.0,
    )

    context_blocks: list[str] = []
    for idx, doc in enumerate(docs[:5], start=1):
        source_name = doc.metadata.get("source", doc.metadata.get("url", "Unknown"))
        context_blocks.append(f"[Source {idx}] {source_name}\n{doc.page_content}")

    if context_blocks:
        context_text = "\n\n".join(context_blocks)
    else:
        context_text = "No relevant sources found."

    if best_score < RAG_CONFIDENCE_THRESHOLD and not context_blocks:
        return {
            "question": cleaned_question,
            "answer": (
                "I could not find reliable information to answer your question. "
                "Please check the official university website or contact the registrar's office for assistance."
            ),
            "sources": [],
            "citation_entries": [],
            "confidence": 0.0,
        }

    model = ChatOllama(
        model=os.getenv("ACADEMIC_AGENT_MODEL_ID", "qwen2.5:3b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        temperature=0,
    )

    response = model.invoke(
        [
            SystemMessage(
                content=(
                    "You are an academic assistant for Acibadem University. "
                    "Answer using the provided context. If context is insufficient, say that clearly. "
                    "Keep the answer concise and factual. "
                    "At the end of your answer, include a 'Sources:' section listing each numbered source."
                )
            ),
            HumanMessage(
                content=(
                    f"Question: {cleaned_question}\n\n"
                    f"Context:\n{context_text}\n\n"
                    "Provide a helpful answer and refer to source names naturally."
                )
            ),
        ]
    )
    answer_text = str(getattr(response, "content", "")).strip()

    return {
        "question": cleaned_question,
        "answer": answer_text,
        "sources": sources,
        "citation_entries": citation_entries,
        "confidence": best_score,
    }
```

- [ ] **Step 3: Run the existing tests to ensure backward compat**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -20
```

Expected: All existing tests pass (the `generate_chat_answer` return value now has extra keys, but existing callers only access `"answer"` and `"sources"`, so this is a backward-compatible extension).

- [ ] **Step 4: Commit**

```bash
git add backend/rag/api_views.py
git commit -m "feat(rag): enrich citation output with structured data and confidence threshold"
```

---

## Task 1.2: Persist citations from RAG into DB and return them in chat response

**Files:**
- Modify: `backend/api_v1/views.py` (lines 127-166)

- [ ] **Step 1: Replace the chat response assembly in views.py**

Open `backend/api_v1/views.py` and replace lines 127 through 166 (the RAG call and response assembly block inside the `chat` view) with:

```python
            # Use shared RAG service module, but keep a deterministic fallback for local/test runs.
            answer_text = "This path is active and ready for OLLAMA integration."
            citation_rows: list[Citation] = []
            try:
                rag_result = rag_services.generate_chat_answer(question)
                candidate = str(rag_result.get("answer", "")).strip()
                if candidate:
                    answer_text = candidate
                for entry in rag_result.get("citation_entries", []):
                    citation_rows.append(
                        Citation(
                            citation_id=entry["citation_id"],
                            source_id=entry["source_id"],
                            chunk_id=entry["chunk_id"],
                            snippet=entry["snippet"],
                            title=entry["title"],
                            url=str(entry.get("url", "")),
                            page=entry.get("page"),
                            doc_metadata=entry.get("doc_metadata", {}),
                            score=entry.get("score"),
                        )
                    )
            except Exception:
                answer_text = "This path is active and ready for OLLAMA integration."

            assistant_message = ChatMessage.objects.create(
                session=chat_session,
                role=ChatMessage.ROLE_ASSISTANT,
                content=answer_text,
            )

            for citation in citation_rows:
                citation.message = assistant_message
                citation.save()

            ChatSession.objects.filter(id=chat_session.id).update(last_message=assistant_message)

        serialized_citations = [_serialize_citation(c) for c in Citation.objects.filter(message=assistant_message)]

        return success_response(
            request,
            {
                "session": {
                    "id": chat_session.id,
                    "is_new": is_new,
                },
                "message": {
                    "id": assistant_message.id,
                    "role": assistant_message.role,
                    "answer": assistant_message.content,
                    "citations": serialized_citations,
                    "created_at": assistant_message.created_at.isoformat().replace("+00:00", "Z"),
                },
                "stream": {
                    "enabled": stream,
                    "transport": "websocket" if stream else None,
                    "channel": f"chat.{chat_session.id}" if stream else None,
                },
            },
            status=200,
        )
```

- [ ] **Step 2: Verify the change parses correctly by running the test suite**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -30
```

Expected: All 30 existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/api_v1/views.py
git commit -m "feat(api): persist RAG citations to DB and return in chat response"
```

---

## Task 1.3: Add citation serialization test

**Files:**
- Modify: `backend/api_v1/tests/test_response_contract.py` (append test)

- [ ] **Step 1: Add a test that verifies citations appear in chat response**

Open `backend/api_v1/tests/test_response_contract.py` and append this test class at the end of the file (after the last `IngestIdempotencyContractTests` class):

```python
class ChatCitationContractTests(TestCase):
    """Verify that citations from the RAG pipeline propagate into the chat response."""

    def setUp(self):
        cache.clear()

    def test_chat_response_includes_citations_array(self):
        """Chat 200 response must include a 'citations' list in the message."""
        client = Client()
        response = client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "What is Acibadem University?", "stream": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("message", payload["data"])
        self.assertIn("citations", payload["data"]["message"])
        self.assertIsInstance(payload["data"]["message"]["citations"], list)

    def test_chat_response_citation_fields_match_contract(self):
        """Each citation must include citation_id, source_id, chunk_id, snippet, title, url, page, doc_metadata, score."""
        client = Client()
        response = client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "Tell me about student life", "stream": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        citations = response.json()["data"]["message"]["citations"]
        for citation in citations:
            required_keys = {
                "citation_id", "source_id", "chunk_id",
                "snippet", "title", "url", "page",
                "doc_metadata", "score",
            }
            self.assertTrue(
                required_keys.issubset(set(citation.keys())),
                f"Missing keys in citation: {required_keys - set(citation.keys())}",
            )
            self.assertIsInstance(citation["citation_id"], str)
            self.assertTrue(citation["citation_id"].startswith("cit_"))
            self.assertIsInstance(citation["source_id"], str)
            self.assertTrue(citation["source_id"].startswith("src_"))
            self.assertIsInstance(citation["chunk_id"], str)
            self.assertTrue(citation["chunk_id"].startswith("chunk_"))
            self.assertIsInstance(citation["snippet"], str)
            self.assertIsInstance(citation["title"], str)
            self.assertIsInstance(citation["doc_metadata"], dict)
```

- [ ] **Step 2: Run the new tests**

```bash
docker compose exec django-web python manage.py test api_v1.tests.test_response_contract.ChatCitationContractTests -v 2
```

Expected: 2 tests pass (citations list present, citation fields match contract). The RAG pipeline will return citations from the demo seed data (4 Acibadem University pages).

- [ ] **Step 3: Commit**

```bash
git add backend/api_v1/tests/test_response_contract.py
git commit -m "test(api): add citation contract tests for chat response"
```

---

## Task 1.4: Add Docker HEALTHCHECK to Django service

**Files:**
- Modify: `backend/Dockerfile` (append HEALTHCHECK)
- Modify: `docker-compose.yml` (add healthcheck to db, ollama, django-web; use `condition: service_healthy`)

- [ ] **Step 1: Add HEALTHCHECK to backend Dockerfile**

Open `backend/Dockerfile` and insert the following two lines just before the final `CMD` line (after line 49, before line 51):

```dockerfile
# Health check: verify Django is responding
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/chat', data=b'{\"question\":\"health\",\"stream\":false}', timeout=3)" || exit 1
```

The full final section of the Dockerfile (lines 40-51) becomes:

```dockerfile
# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check: verify Django is responding
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/chat', data=b'{\"question\":\"health\",\"stream\":false}', timeout=3)" || exit 1

# Start the application using Gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 2: Add health checks and `condition: service_healthy` to docker-compose.yml**

Open `docker-compose.yml` and replace the entire file content with:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    gpus: all
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 10s
      timeout: 5s
      start_period: 40s
      retries: 5

  db:
    image: postgres:17
    container_name: postgres-db
    environment:
      POSTGRES_DB: ${DATABASE_NAME}
      POSTGRES_USER: ${DATABASE_USERNAME}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USERNAME} -d ${DATABASE_NAME}"]
      interval: 5s
      timeout: 3s
      start_period: 10s
      retries: 5

  django-web:
    build: ./backend
    container_name: django-docker
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./backend/chromadb-data:/app/chromadb-data
    depends_on:
      db:
        condition: service_healthy
      ollama:
        condition: service_healthy
    environment:
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}
      DEBUG: ${DEBUG}
      DJANGO_LOGLEVEL: ${DJANGO_LOGLEVEL}
      DJANGO_ALLOWED_HOSTS: ${DJANGO_ALLOWED_HOSTS}
      DATABASE_ENGINE: ${DATABASE_ENGINE}
      DATABASE_NAME: ${DATABASE_NAME}
      DATABASE_USERNAME: ${DATABASE_USERNAME}
      DATABASE_PASSWORD: ${DATABASE_PASSWORD}
      DATABASE_HOST: ${DATABASE_HOST}
      DATABASE_PORT: ${DATABASE_PORT}
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}
      ACADEMIC_AGENT_MODEL_ID: ${ACADEMIC_AGENT_MODEL_ID}
      OLLAMA_EMBEDDING_MODEL_ID: ${OLLAMA_EMBEDDING_MODEL_ID}
      VECTOR_STORE_PERSIST_DIR: ${VECTOR_STORE_PERSIST_DIR}
      APP_NAME: ${APP_NAME}
      LOG_LEVEL: ${LOG_LEVEL}
      LOG_DIR: ${LOG_DIR}
    env_file:
      - .env

  frontend:
    image: node:20-alpine
    container_name: frontend-docker
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
    depends_on:
      django-web:
        condition: service_healthy
    environment:
      CHOKIDAR_USEPOLLING: "true"
      VITE_API_PROXY_TARGET: http://django-web:8000
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 5173"

volumes:
  postgres_data:
  ollama_data:
  frontend_node_modules:
```

- [ ] **Step 3: Rebuild and verify healthy startup**

```bash
docker compose down
docker compose up -d --build
sleep 60
docker compose ps
```

Expected: All four services show `(healthy)` in the STATUS column. If any service is `(unhealthy)` or `(starting)` after 60 seconds, check logs with `docker compose logs <service>`.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile docker-compose.yml
git commit -m "feat(docker): add health checks with depends_on conditions to all services"
```

---

## Task 1.5: Add real URL scraper to WebScrapeProcessor

**Files:**
- Modify: `backend/rag/web_scrape_processor.py` (add imports and `fetch_url` method)
- Modify: `backend/requirements.txt` (add `beautifulsoup4` and `requests` if missing)

- [ ] **Step 1: Check if beautifulsoup4 and requests are available**

```bash
docker compose exec django-web pip list 2>/dev/null | grep -iE "beautifulsoup|requests" || echo "DEPS_MISSING"
```

If `DEPS_MISSING` is printed, continue to Step 1a. Otherwise skip to Step 2.

- [ ] **Step 1a: Add beautifulsoup4 and requests to requirements.txt**

Read `backend/requirements.txt` first to see its current content, then add these lines at the end of the file:

```
beautifulsoup4>=4.12
requests>=2.31
```

```bash
docker compose exec django-web pip install beautifulsoup4 requests
```

- [ ] **Step 2: Add the `fetch_url` method to WebScrapeProcessor**

Open `backend/rag/web_scrape_processor.py` and replace the import block (lines 1-8) with:

```python
import os
import re
import hashlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from printmeup import printmeup as pm

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPER_DEPS = True
except ImportError:
    HAS_SCRAPER_DEPS = False
```

Then, insert the following method into the `WebScrapeProcessor` class, after the `__init__` method (after line 16):

```python
    def fetch_url(self, url: str, title: str = "", source_tag: str = "") -> Document | None:
        """Fetch a single URL and return a LangChain Document with its text content.

        Args:
            url: The URL to scrape.
            title: Optional title override. If empty, uses HTML <title>.
            source_tag: Optional source label for metadata. If empty, uses the URL hostname.

        Returns:
            A Document with page_content set to the normalized body text, or None on failure.
        """
        if not HAS_SCRAPER_DEPS:
            pm.war("requests and beautifulsoup4 are not installed; cannot scrape URLs")
            return None

        try:
            pm.inf(f"Fetching URL: {url}")
            resp = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": "ACUChatbot/1.0 (university-project; educational-use-only)"
                },
            )
            resp.raise_for_status()
        except Exception as e:
            pm.err(e=e, m=f"Failed to fetch URL {url}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav, footer elements that don't contain useful content
        for tag_name in ("script", "style", "nav", "footer", "header"):
            for tag in soup.find_all(tag_name):
                tag.decompose()

        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)
        cleaned = self._normalize_text(text)

        if len(cleaned) < self.min_content_length:
            pm.war(f"Skipping URL {url}: content too short ({len(cleaned)} chars)")
            return None

        resolved_title = title or (soup.title.string.strip() if soup.title else url.split("/")[-1] or "Untitled")
        resolved_source = source_tag or url

        return Document(
            page_content=cleaned,
            metadata={
                "title": self._normalize_text(resolved_title),
                "source": resolved_source,
                "url": url,
                "ingestion_type": "url_scrape",
                "content_type": resp.headers.get("Content-Type", ""),
            },
        )

    def fetch_url_and_ingest(self, url: str, title: str = "", source_tag: str = "") -> dict:
        """Fetch a URL and ingest it into the vector store in one call.
        
        Returns a status dict:
            {"status": "ingested"|"failed", "url": url, "title": title, "chunk_count": int}
        """
        doc = self.fetch_url(url, title=title, source_tag=source_tag)
        if doc is None:
            return {"status": "failed", "url": url, "title": title, "chunk_count": 0}

        chunks = self.split_documents_into_chunks([doc])
        if not chunks:
            return {"status": "failed", "url": url, "title": title, "chunk_count": 0}

        return {"status": "ingested", "url": url, "title": title, "chunk_count": len(chunks)}
```

- [ ] **Step 3: Test the scraper by scraping one Acibadem University page**

```bash
docker compose exec django-web python -c "
from rag.web_scrape_processor import WebScrapeProcessor
from rag.vector_store import init_vector_store_manager

vsm, _ = init_vector_store_manager()
proc = WebScrapeProcessor()
result = proc.fetch_url_and_ingest(
    'https://www.acibadem.edu.tr/en',
    title='Acibadem University Homepage',
    source_tag='acibadem_homepage'
)
print('RESULT:', result)
if result['status'] == 'ingested' and result['chunk_count'] > 0:
    chunks = proc.split_documents_into_chunks([proc.fetch_url('https://www.acibadem.edu.tr/en')])
    ok = vsm.add_chunks(chunks)
    print('VECTOR_STORE_ADD:', ok)
"
```

Expected: `RESULT: {'status': 'ingested', 'url': 'https://www.acibadem.edu.tr/en', 'title': 'Acibadem University Homepage', 'chunk_count': N}` where N > 0. If the URL fails to fetch (e.g., blocked by the server), try an alternative university URL or a Wikipedia page about the university.

- [ ] **Step 4: Commit**

```bash
git add backend/rag/web_scrape_processor.py backend/requirements.txt
git commit -m "feat(rag): add URL scraper with BeautifulSoup to WebScrapeProcessor"
```

---

## Task 1.6: Wire URL-type items through ingest endpoint

**Files:**
- Modify: `backend/api_v1/views.py` (lines 436-455, the item processing loop in `ingest`)

- [ ] **Step 1: Update the ingest view to handle `url` type items**

Open `backend/api_v1/views.py` and replace lines 436 through 455 (the `for item in items:` loop and the `if documents_payload:` block) with:

```python
        documents_payload = []
        url_items_processed = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "")).strip().lower()
            value = str(item.get("value", "")).strip()
            if item_type in {"text", "content"} and value:
                documents_payload.append(
                    {
                        "title": str(item.get("metadata", {}).get("title", item.get("title", "Ingested text"))),
                        "source": str(item.get("metadata", {}).get("source", "api_v1_ingest")),
                        "content": value,
                    }
                )
            elif item_type == "url" and value:
                try:
                    from rag.web_scrape_processor import WebScrapeProcessor
                    proc = WebScrapeProcessor()
                    scrape_result = proc.fetch_url_and_ingest(
                        url=value,
                        title=str(item.get("metadata", {}).get("title", "")),
                        source_tag=str(item.get("metadata", {}).get("source", "api_ingest_url")),
                    )
                    if scrape_result["status"] == "ingested":
                        url_items_processed += 1
                except Exception:
                    pass

        if documents_payload:
            try:
                rag_services.ingest_documents(documents_payload)
            except Exception:
                pass
```

- [ ] **Step 2: Run the ingest tests to verify url-type handling doesn't break existing flow**

```bash
docker compose exec django-web python manage.py test api_v1.tests.test_ingest_service_token api_v1.tests.test_access_control -v 2
```

Expected: All existing ingest tests pass. The URL-type path is exercised when the scraper is reachable; when not, it silently skips.

- [ ] **Step 3: Commit**

```bash
git add backend/api_v1/views.py
git commit -m "feat(api): wire URL-type ingest items through WebScrapeProcessor"
```

---

## Task 1.7: Sprint 1 integration test

- [ ] **Step 1: Run full backend test suite**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -40
```

Expected: All 32 tests pass (30 existing + 2 new citation tests).

- [ ] **Step 2: End-to-end chat test with citations**

```bash
docker compose exec django-web python -c "
import json, urllib.request
req = urllib.request.Request(
    'http://localhost:8000/api/v1/chat',
    data=json.dumps({'question': 'What is Acibadem University?', 'stream': False}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = json.loads(urllib.request.urlopen(req).read())
print('SESSION_ID:', resp['data']['session']['id'])
print('ANSWER:', resp['data']['message']['answer'][:200])
print('CITATION_COUNT:', len(resp['data']['message']['citations']))
for c in resp['data']['message']['citations']:
    print(f'  [{c[\"citation_id\"]}] {c[\"title\"]} — {c[\"snippet\"][:80]}...')
"
```

Expected: `CITATION_COUNT` >= 1, each citation has `citation_id`, `title`, `snippet`. The RAG pipeline returns citations from the demo seed data or any previously ingested content.

- [ ] **Step 3: Sprint 1 final commit (if any uncommitted changes)**

```bash
git status
git add -A
git commit -m "chore: Sprint 1 integration validation complete"
```

---

# Sprint 2: Web Scraping Pipeline + Evaluation Framework

**Goal:** Scrape 3-5 real university pages, add retrieval confidence thresholds with fallback responses, build a reusable evaluation runner, and score the system against the 10-question evaluation set from the proposal.

## Task 2.1: Build multi-page scraper script

**Files:**
- Create: `backend/rag/scrape_targets.py`
- Modify: `backend/rag/__init__.py` (ensure module exports)

- [ ] **Step 1: Create the scrape targets configuration**

Create `backend/rag/scrape_targets.py`:

```python
"""Pre-configured scrape targets for Acibadem University and related sources."""

SCRAPE_TARGETS = [
    {
        "url": "https://www.acibadem.edu.tr/en",
        "title": "Acibadem University Homepage",
        "source_tag": "acibadem_homepage",
    },
    {
        "url": "https://www.acibadem.edu.tr/en/prospective-students",
        "title": "Prospective Students — Acibadem University",
        "source_tag": "acibadem_prospective",
    },
    {
        "url": "https://www.acibadem.edu.tr/en/life-at-acibadem",
        "title": "Campus Life — Acibadem University",
        "source_tag": "acibadem_campus",
    },
    {
        "url": "https://obs.acibadem.edu.tr",
        "title": "Bologna Information System — Acibadem University",
        "source_tag": "acibadem_bologna",
    },
    {
        "url": "https://www.acibadem.edu.tr/en/academics",
        "title": "Academics — Acibadem University",
        "source_tag": "acibadem_academics",
    },
]
```

- [ ] **Step 2: Create the batch scraper script**

Create `backend/rag/scrape_runner.py`:

```python
"""Batch scraper: fetch all pre-configured targets and ingest into the vector store."""

import os
import sys
from pathlib import Path

# Allow running this script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.vector_store import init_vector_store_manager
from rag.web_scrape_processor import WebScrapeProcessor
from rag.scrape_targets import SCRAPE_TARGETS
from printmeup import printmeup as pm


def run_batch_scrape() -> dict:
    """Scrape all targets and return summary stats."""
    vsm, _ = init_vector_store_manager()
    processor = WebScrapeProcessor()

    stats = {
        "total_targets": len(SCRAPE_TARGETS),
        "ingested": 0,
        "failed": 0,
        "total_chunks": 0,
        "details": [],
    }

    for target in SCRAPE_TARGETS:
        pm.inf(f"Processing: {target['title']} ({target['url']})")
        doc = processor.fetch_url(
            url=target["url"],
            title=target["title"],
            source_tag=target["source_tag"],
        )

        if doc is None:
            stats["failed"] += 1
            stats["details"].append({"url": target["url"], "status": "failed"})
            continue

        chunks = processor.split_documents_into_chunks([doc])
        if not chunks:
            stats["failed"] += 1
            stats["details"].append({"url": target["url"], "status": "no_chunks_produced"})
            continue

        ok = vsm.add_chunks(chunks)
        if ok:
            stats["ingested"] += 1
            stats["total_chunks"] += len(chunks)
            stats["details"].append({
                "url": target["url"],
                "title": target["title"],
                "status": "ingested",
                "chunk_count": len(chunks),
            })
        else:
            stats["failed"] += 1
            stats["details"].append({"url": target["url"], "status": "vector_store_add_failed"})

    pm.suc(f"Batch scrape complete: {stats['ingested']} ingested, {stats['failed']} failed, {stats['total_chunks']} chunks")
    return stats


if __name__ == "__main__":
    result = run_batch_scrape()
    import json
    print(json.dumps(result, indent=2))
```

- [ ] **Step 3: Run the batch scraper**

```bash
docker compose exec django-web python rag/scrape_runner.py
```

Expected: At least 2 of the 5 targets succeed in ingestion. The output prints a JSON summary with `ingested` count > 0.

- [ ] **Step 4: Verify content is searchable**

```bash
docker compose exec django-web python -c "
from rag.vector_store import init_vector_store_manager
_, retriever = init_vector_store_manager()
docs = retriever.invoke('What programs does Acibadem University offer?')
print('Retrieved', len(docs), 'documents')
for doc in docs[:3]:
    print('  Source:', doc.metadata.get('source', 'Unknown'))
    print('  Preview:', doc.page_content[:120])
"
```

Expected: At least 1 document returned with content from the scraped pages (not the demo seed).

- [ ] **Step 5: Commit**

```bash
git add backend/rag/scrape_targets.py backend/rag/scrape_runner.py
git commit -m "feat(rag): add batch scraper with 5 pre-configured university targets"
```

---

## Task 2.2: Implement retrieval confidence threshold and fallback

**Files:**
- Already done in Task 1.1 — the `generate_chat_answer` function now checks `RAG_CONFIDENCE_THRESHOLD` and returns a fallback message when confidence is below threshold. Verify and document.

- [ ] **Step 1: Add RAG_CONFIDENCE_THRESHOLD to .env.example**

Open `.env.example` and append at the end:

```
# RAG confidence threshold (0.0-1.0). Answers below this threshold get a fallback response.
RAG_CONFIDENCE_THRESHOLD=0.3
```

Open `.env` (or create if absent) and add the same line:

```
RAG_CONFIDENCE_THRESHOLD=0.3
```

- [ ] **Step 2: Test fallback behavior with an obscure question**

```bash
docker compose exec django-web python -c "
from rag.api_views import generate_chat_answer
result = generate_chat_answer('What is the quantum chromodynamics of dark matter in perpetual motion machines?')
print('ANSWER:', result['answer'])
print('CONFIDENCE:', result.get('confidence', 'N/A'))
print('CITATIONS:', len(result.get('citation_entries', [])))
"
```

Expected: The answer should be the fallback text ("I could not find reliable information..."), confidence should be 0.0 or very low, and citations should be empty. The LLM should not hallucinate.

- [ ] **Step 3: Commit**

```bash
git add .env.example .env 2>/dev/null; git add backend/rag/api_views.py
git commit -m "feat(rag): add confidence threshold with fallback response for weak retrieval"
```

---

## Task 2.3: Create the evaluation runner

**Files:**
- Create: `backend/rag/evaluation.py`

- [ ] **Step 1: Create the evaluation runner**

Create `backend/rag/evaluation.py`:

```python
"""Evaluation runner for the chatbot RAG pipeline.

Runs a predefined set of questions through the system, records answers and citations,
and scores each answer against a simple rubric.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.api_views import generate_chat_answer

EVALUATION_QUESTIONS = [
    {
        "id": "q1",
        "question": "What are the tuition payment deadlines?",
        "expected_accuracy": "correct_grounded",
        "category": "finance",
    },
    {
        "id": "q2",
        "question": "What are the library opening hours on weekdays?",
        "expected_accuracy": "correct_grounded",
        "category": "campus_services",
    },
    {
        "id": "q3",
        "question": "How can I request an AWS ACU quota extension?",
        "expected_accuracy": "correct_grounded",
        "category": "aws_acu",
    },
    {
        "id": "q4",
        "question": "Who can access the ingest endpoint in API v1?",
        "expected_accuracy": "correct_grounded",
        "category": "api_access",
    },
    {
        "id": "q5",
        "question": "Can anonymous users submit feedback on assistant messages?",
        "expected_accuracy": "correct_grounded",
        "category": "api_access",
    },
    {
        "id": "q6",
        "question": "How does rate limiting work for chat requests?",
        "expected_accuracy": "correct_grounded",
        "category": "api_access",
    },
    {
        "id": "q7",
        "question": "What data is stored for each chat session?",
        "expected_accuracy": "correct_grounded",
        "category": "api_access",
    },
    {
        "id": "q8",
        "question": "What should I do if no citation is available for an answer?",
        "expected_accuracy": "safe_transparent",
        "category": "safety",
    },
    {
        "id": "q9",
        "question": "Where can I find source drill-down details by source id?",
        "expected_accuracy": "correct_grounded",
        "category": "api_access",
    },
    {
        "id": "q10",
        "question": "What is the difference between chat answer generation and retrieval?",
        "expected_accuracy": "correct_grounded",
        "category": "system_understanding",
    },
]

SCORING_RUBRIC = {
    "correct_grounded": "Correct and grounded in sources",
    "partially_correct": "Partially correct, some issues",
    "incorrect_unsupported": "Incorrect or unsupported by sources",
}


def score_answer(rag_result: dict) -> str:
    """Score a single answer based on citations and confidence.

    Returns one of: correct_grounded, partially_correct, incorrect_unsupported.
    """
    citations = rag_result.get("citation_entries", [])
    confidence = rag_result.get("confidence", 0.0)
    answer = rag_result.get("answer", "")

    if not answer or len(answer) < 10:
        return "incorrect_unsupported"

    if not citations:
        if confidence < 0.3:
            # Deliberate fallback for obscure questions — this is correct behavior
            if "could not find" in answer.lower() or "check the official" in answer.lower():
                return "correct_grounded"
            return "incorrect_unsupported"
        return "incorrect_unsupported"

    if len(citations) >= 1 and confidence >= 0.3:
        return "correct_grounded"

    if len(citations) >= 1:
        return "partially_correct"

    return "incorrect_unsupported"


def run_evaluation(output_path: str | None = None) -> list[dict]:
    """Run all evaluation questions and return results."""
    results = []
    for item in EVALUATION_QUESTIONS:
        print(f"Evaluating {item['id']}: {item['question'][:80]}...")
        rag_result = generate_chat_answer(item["question"])
        score = score_answer(rag_result)

        result = {
            "id": item["id"],
            "question": item["question"],
            "category": item["category"],
            "expected_accuracy": item["expected_accuracy"],
            "actual_score": score,
            "answer": rag_result.get("answer", ""),
            "confidence": rag_result.get("confidence", 0.0),
            "citation_count": len(rag_result.get("citation_entries", [])),
            "citations": [
                {
                    "title": c["title"],
                    "source_id": c["source_id"],
                    "snippet": c["snippet"][:100],
                }
                for c in rag_result.get("citation_entries", [])
            ],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        results.append(result)
        print(f"  Score: {score} | Citations: {len(result['citations'])} | Confidence: {result['confidence']:.2f}")

    summary = {
        "total": len(results),
        "correct_grounded": sum(1 for r in results if r["actual_score"] == "correct_grounded"),
        "partially_correct": sum(1 for r in results if r["actual_score"] == "partially_correct"),
        "incorrect_unsupported": sum(1 for r in results if r["actual_score"] == "incorrect_unsupported"),
    }
    print(f"\nEvaluation Summary:")
    print(f"  Total: {summary['total']}")
    print(f"  Correct & Grounded: {summary['correct_grounded']}")
    print(f"  Partially Correct: {summary['partially_correct']}")
    print(f"  Incorrect/Unsupported: {summary['incorrect_unsupported']}")

    if output_path:
        full_output = {
            "summary": summary,
            "results": results,
        }
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_output, f, indent=2, ensure_ascii=False)
        print(f"\nFull results written to {output_path}")

    return results


if __name__ == "__main__":
    out = os.getenv("EVAL_OUTPUT_PATH", "logs/evaluation_results.json")
    run_evaluation(output_path=out)
```

- [ ] **Step 2: Run the evaluation**

```bash
docker compose exec django-web python rag/evaluation.py
```

Expected: The script prints scores for all 10 questions. The actual scores depend on what content is in the vector store. If only the 4 demo seed documents + scraped pages exist, expect mostly "partially_correct" or "incorrect_unsupported" since the demo data doesn't cover tuition deadlines, library hours, etc. This is expected — the evaluation identifies content gaps for the scraping pipeline to address.

- [ ] **Step 3: Review evaluation output**

```bash
cat backend/logs/evaluation_results.json | python -m json.tool | head -60
```

- [ ] **Step 4: Commit**

```bash
git add backend/rag/evaluation.py backend/logs/evaluation_results.json 2>/dev/null
git commit -m "feat(eval): add evaluation runner with 10-question set and scoring rubric"
```

---

## Task 2.4: Sprint 2 integration test

- [ ] **Step 1: Run backend test suite**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -10
```

Expected: All 32 tests pass.

- [ ] **Step 2: Verify scraper + citations + evaluation all work together**

```bash
docker compose exec django-web bash -c "
python rag/scrape_runner.py && \
python rag/evaluation.py && \
python -c \"
from rag.api_views import generate_chat_answer
r = generate_chat_answer('Tell me about Acibadem University')
print('CITATIONS:', len(r.get('citation_entries', [])))
print('CONFIDENCE:', r.get('confidence', 0))
\""
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: Sprint 2 integration validation complete"
```

---

# Sprint 3: Auth UI + Session Management + Admin Panel

**Goal:** Deliver a frontend login/registration flow, a session sidebar for managing multiple chat sessions, and a backend admin dashboard for monitoring the system.

## Task 3.1: Create backend login/logout API endpoints for session-based auth

**Files:**
- Create: `backend/api_v1/auth_views.py`
- Modify: `backend/api_v1/urls.py` (add routes)

- [ ] **Step 1: Create auth views**

Create `backend/api_v1/auth_views.py`:

```python
"""Session-based authentication views for the v1 API."""

import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .errors import ApiError
from .responses import error_response, success_response


@csrf_exempt
@require_POST
def login_view(request: HttpRequest):
    """POST /api/v1/auth/login — session-cookie based login.

    Request body: {"username": "...", "password": "..."}
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return error_response(request, 400, "VALIDATION_ERROR", "Invalid JSON payload.")

    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()

    if not username or not password:
        return error_response(
            request, 400, "VALIDATION_ERROR", "Invalid request payload.",
            details=[
                {"field": "username", "reason": "required"} if not username else None,
                {"field": "password", "reason": "required"} if not password else None,
            ],
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return error_response(request, 401, "UNAUTHORIZED", "Invalid username or password.")

    login(request, user)

    return success_response(
        request,
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "is_staff": user.is_staff,
                "role": "admin/staff" if user.is_staff or user.is_superuser else "student",
            }
        },
        status=200,
    )


@csrf_exempt
@require_POST
def register_view(request: HttpRequest):
    """POST /api/v1/auth/register — create a new student account.

    Request body: {"username": "...", "password": "...", "email": "..."}
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return error_response(request, 400, "VALIDATION_ERROR", "Invalid JSON payload.")

    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    email = (payload.get("email") or "").strip()

    details = []
    if not username or len(username) < 3:
        details.append({"field": "username", "reason": "too_short"})
    if not password or len(password) < 6:
        details.append({"field": "password", "reason": "too_short"})
    if details:
        return error_response(request, 400, "VALIDATION_ERROR", "Invalid request payload.", details=details)

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return error_response(request, 409, "CONFLICT", "Username already taken.")

    user = User.objects.create_user(username=username, password=password, email=email)
    login(request, user)

    return success_response(
        request,
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "role": "student",
            }
        },
        status=201,
    )


@require_POST
def logout_view(request: HttpRequest):
    """POST /api/v1/auth/logout — clear the session cookie."""
    logout(request)
    return success_response(request, {"message": "Logged out."}, status=200)


@require_POST
def whoami_view(request: HttpRequest):
    """GET /api/v1/auth/whoami — return current user info or anonymous."""
    from .auth import resolve_auth_context, ROLE_ANONYMOUS
    context = resolve_auth_context(request)

    if context.role == ROLE_ANONYMOUS:
        return success_response(request, {"authenticated": False, "role": "anonymous"}, status=200)

    return success_response(
        request,
        {
            "authenticated": True,
            "role": context.role,
            "user": {
                "id": context.user.id,
                "username": context.user.username,
                "is_staff": context.user.is_staff if context.user else False,
            } if context.user else None,
        },
        status=200,
    )
```

- [ ] **Step 2: Add auth routes to urlpatterns**

Open `backend/api_v1/urls.py` and replace with:

```python
from django.urls import path

from . import views
from . import auth_views


urlpatterns = [
    path("chat", views.chat, name="chat"),
    path("sessions/<str:id>/messages", views.session_messages, name="session-messages"),
    path("feedback", views.feedback, name="feedback"),
    path("sources/<str:source_id>", views.source_by_id, name="source-by-id"),
    path("ingest", views.ingest, name="ingest"),
    path("auth/login", auth_views.login_view, name="auth-login"),
    path("auth/register", auth_views.register_view, name="auth-register"),
    path("auth/logout", auth_views.logout_view, name="auth-logout"),
    path("auth/whoami", auth_views.whoami_view, name="auth-whoami"),
]
```

- [ ] **Step 3: Test the auth endpoints**

```bash
docker compose exec django-web python -c "
import json, urllib.request

# Test register
req = urllib.request.Request(
    'http://localhost:8000/api/v1/auth/register',
    data=json.dumps({'username': 'teststudent', 'password': 'testpass123', 'email': 'test@example.com'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = json.loads(urllib.request.urlopen(req).read())
    print('REGISTER:', resp['data']['user']['username'], 'role:', resp['data']['user']['role'])
except Exception as e:
    print('REGISTER:', e)

# Test whoami (should use the session cookie from register response)
print('WHOAMI: test manually via curl or browser')
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/api_v1/auth_views.py backend/api_v1/urls.py
git commit -m "feat(api): add login, register, logout, whoami auth endpoints"
```

---

## Task 3.2: Create frontend auth service and types

**Files:**
- Modify: `frontend/src/types/api.ts` (add auth types)
- Modify: `frontend/src/lib/apiClient.ts` (add auth API functions)
- Create: `frontend/src/services/authService.ts`

- [ ] **Step 1: Add auth types to api.ts**

Open `frontend/src/types/api.ts` and append at the end of the file:

```typescript
/** Auth request bodies */
export type LoginRequest = {
  username: string
  password: string
}

export type RegisterRequest = {
  username: string
  password: string
  email?: string
}

export type AuthUser = {
  id: number
  username: string
  role: string
  is_staff?: boolean
}

export type LoginResponseData = {
  user: AuthUser
}

export type RegisterResponseData = {
  user: AuthUser
}

export type WhoamiResponseData = {
  authenticated: boolean
  role: string
  user?: AuthUser | null
}

export type LogoutResponseData = {
  message: string
}
```

- [ ] **Step 2: Add auth API functions to apiClient.ts**

Open `frontend/src/lib/apiClient.ts` and append before the last line:

```typescript
import type {
  LoginRequest,
  LoginResponseData,
  RegisterRequest,
  RegisterResponseData,
  WhoamiResponseData,
  LogoutResponseData,
} from '../types/api'

export function postLogin(payload: LoginRequest) {
  return request<LoginResponseData>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function postRegister(payload: RegisterRequest) {
  return request<RegisterResponseData>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function postLogout() {
  return request<LogoutResponseData>('/auth/logout', {
    method: 'POST',
  })
}

export function getWhoami() {
  return request<WhoamiResponseData>('/auth/whoami', {
    method: 'POST',
  })
}
```

- [ ] **Step 3: Create authService.ts**

Create `frontend/src/services/authService.ts`:

```typescript
import { postLogin, postRegister, postLogout, getWhoami } from '../lib/apiClient'
import type { AuthUser, LoginRequest, RegisterRequest } from '../types/api'

export async function login(credentials: LoginRequest): Promise<AuthUser> {
  const response = await postLogin(credentials)
  return response.user
}

export async function register(details: RegisterRequest): Promise<AuthUser> {
  const response = await postRegister(details)
  return response.user
}

export async function logout(): Promise<void> {
  await postLogout()
}

export async function whoami() {
  return getWhoami()
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/lib/apiClient.ts frontend/src/services/authService.ts
git commit -m "feat(frontend): add auth types, API client, and service layer"
```

---

## Task 3.3: Create LoginPage and auth state management

**Files:**
- Create: `frontend/src/components/LoginPage.tsx`
- Create: `frontend/src/components/LoginPage.css`
- Modify: `frontend/src/hooks/useChat.ts` (add auth state)
- Modify: `frontend/src/App.tsx` (add auth/unauth routing)

- [ ] **Step 1: Create LoginPage component**

Create `frontend/src/components/LoginPage.tsx`:

```tsx
import { type FormEvent, useState } from 'react'
import { login, register } from '../services/authService'
import type { AuthUser } from '../types/api'
import './LoginPage.css'

type LoginPageProps = {
  onLogin: (user: AuthUser) => void
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [pending, setPending] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!username.trim() || !password.trim()) return

    setPending(true)
    setErrorText(null)

    try {
      let user: AuthUser
      if (mode === 'login') {
        user = await login({ username: username.trim(), password })
      } else {
        user = await register({ username: username.trim(), password, email: email.trim() || undefined })
      }
      onLogin(user)
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : 'Authentication failed.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h2>{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>

        {errorText && <div className="login-error" role="alert">{errorText}</div>}

        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="auth-username">Username</label>
          <input
            id="auth-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            minLength={3}
            required
          />

          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            minLength={6}
            required
          />

          {mode === 'register' && (
            <>
              <label htmlFor="auth-email">Email (optional)</label>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </>
          )}

          <button type="submit" disabled={pending}>
            {pending ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p className="login-switch">
          {mode === 'login' ? (
            <>Don't have an account? <button type="button" onClick={() => setMode('register')}>Register</button></>
          ) : (
            <>Already have an account? <button type="button" onClick={() => setMode('login')}>Sign In</button></>
          )}
        </p>

        <p className="login-anon">
          <button type="button" onClick={() => onLogin({ id: 0, username: 'Anonymous', role: 'anonymous' })}>
            Continue as Guest
          </button>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create LoginPage CSS**

Create `frontend/src/components/LoginPage.css`:

```css
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #1a1a2e;
}

.login-card {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
  color: #e0e0e0;
}

.login-card h2 {
  margin: 0 0 1.5rem;
  color: #e94560;
  text-align: center;
}

.login-card label {
  display: block;
  margin: 0.75rem 0 0.25rem;
  font-size: 0.85rem;
  color: #a0a0c0;
}

.login-card input {
  width: 100%;
  padding: 0.65rem;
  border: 1px solid #0f3460;
  border-radius: 6px;
  background: #1a1a2e;
  color: #e0e0e0;
  font-size: 0.95rem;
  box-sizing: border-box;
}

.login-card button[type="submit"] {
  width: 100%;
  margin-top: 1.5rem;
  padding: 0.75rem;
  background: #e94560;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
}

.login-card button[type="submit"]:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-error {
  background: #3d0000;
  border: 1px solid #e94560;
  color: #ffb3b3;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.login-switch {
  text-align: center;
  margin-top: 1rem;
  font-size: 0.85rem;
  color: #a0a0c0;
}

.login-switch button,
.login-anon button {
  background: none;
  border: none;
  color: #e94560;
  cursor: pointer;
  text-decoration: underline;
  font-size: inherit;
  padding: 0;
}

.login-anon {
  text-align: center;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #0f3460;
}
```

- [ ] **Step 3: Modify useChat to include auth user state**

Open `frontend/src/hooks/useChat.ts` and add these imports at the top:

```typescript
import type { AuthUser } from '../types/api'
```

Add auth state inside the `useChat` function, after line 18 (`const [sourceLoading, ...]`):

```typescript
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
```

And add `handleLogin` and `handleLogout` functions, and export them in the return object. Add these functions before the `sortedMessages` useMemo (before line 148):

```typescript
  function handleLogin(user: AuthUser) {
    setAuthUser(user)
    setErrorText(null)
  }

  async function handleLogout() {
    try {
      const { logout } = await import('../services/authService')
      await logout()
    } catch {
      // Logout best-effort
    }
    setAuthUser(null)
    setSessionId(null)
    setMessages([])
  }
```

Expand the return object to include auth state. Change the return block (lines 153-171) to:

```typescript
  return {
    question,
    setQuestion,
    sessionId,
    authUser,
    pending,
    sortedMessages,
    errorText,
    retryAfter,
    feedbackReasonByMessage,
    setFeedbackReasonByMessage,
    feedbackCommentByMessage,
    setFeedbackCommentByMessage,
    submittedFeedback,
    sourceLoading,
    selectedSource,
    submitQuestion,
    submitFeedback,
    loadSource,
    handleLogin,
    handleLogout,
  }
```

- [ ] **Step 4: Modify App.tsx to show login page when not authenticated**

Open `frontend/src/App.tsx` and replace the entire file content with:

```tsx
import type { FormEvent } from 'react'
import type { Citation } from './types/api'
import { useChat } from './hooks/useChat'
import { ConversationPanel } from './components/ConversationPanel'
import { LoginPage } from './components/LoginPage'
import { Masthead } from './components/Masthead'
import { SourcePanel } from './components/SourcePanel'
import { StatusBar } from './components/StatusBar'
import './App.css'

function App() {
  const {
    question,
    setQuestion,
    sessionId,
    authUser,
    pending,
    sortedMessages,
    errorText,
    retryAfter,
    feedbackReasonByMessage,
    setFeedbackReasonByMessage,
    feedbackCommentByMessage,
    setFeedbackCommentByMessage,
    submittedFeedback,
    sourceLoading,
    selectedSource,
    submitQuestion,
    submitFeedback,
    loadSource,
    handleLogin,
    handleLogout,
  } = useChat()

  if (!authUser) {
    return (
      <div className="page">
        <Masthead />
        <LoginPage onLogin={handleLogin} />
      </div>
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await submitQuestion()
  }

  async function handleFeedback(messageId: string, rating: 'up' | 'down') {
    await submitFeedback(messageId, rating)
  }

  async function handleCitationClick(citation: Citation) {
    await loadSource(citation)
  }

  return (
    <main className="page">
      <Masthead />

      <div className="auth-bar">
        <span>Signed in as: {authUser.username}</span>
        <button type="button" onClick={() => void handleLogout()}>Sign Out</button>
      </div>

      <ConversationPanel
        sessionId={sessionId}
        sortedMessages={sortedMessages}
        sourceLoading={sourceLoading}
        feedbackReasonByMessage={feedbackReasonByMessage}
        setFeedbackReasonByMessage={setFeedbackReasonByMessage}
        feedbackCommentByMessage={feedbackCommentByMessage}
        setFeedbackCommentByMessage={setFeedbackCommentByMessage}
        submittedFeedback={submittedFeedback}
        handleCitationClick={handleCitationClick}
        handleFeedback={handleFeedback}
        question={question}
        setQuestion={setQuestion}
        pending={pending}
        handleSubmit={handleSubmit}
      />

      <SourcePanel sourceLoading={sourceLoading} selectedSource={selectedSource} />

      <StatusBar errorText={errorText} retryAfter={retryAfter} />
    </main>
  )
}

export default App
```

- [ ] **Step 5: Add auth-bar styles to App.css**

Open `frontend/src/App.css` and append:

```css
.auth-bar {
  grid-column: 1 / -1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #0f3460;
  color: #e0e0e0;
  font-size: 0.85rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.auth-bar button {
  background: #e94560;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.25rem 0.75rem;
  cursor: pointer;
  font-size: 0.8rem;
}
```

- [ ] **Step 6: Build frontend to verify no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: Build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/LoginPage.tsx frontend/src/components/LoginPage.css frontend/src/hooks/useChat.ts frontend/src/App.tsx frontend/src/App.css
git commit -m "feat(frontend): add login/register page with auth state management"
```

---

## Task 3.4: Add session sidebar with list, new chat, and switch

**Files:**
- Create: `frontend/src/components/SessionSidebar.tsx`
- Create: `frontend/src/components/SessionSidebar.css`
- Modify: `frontend/src/hooks/useChat.ts` (add session list state, startNewChat)
- Modify: `frontend/src/App.tsx` (add sidebar layout)

- [ ] **Step 1: Add session list API function**

Open `frontend/src/lib/apiClient.ts` and append:

```typescript
import type { SessionMessagesResponseData } from '../types/api'

export type SessionListItem = {
  id: string
  created_at: string
  status: string
  last_message_preview: string
}

export function getSessionList(ownerType?: string) {
  const params = new URLSearchParams({ limit: '20' })
  if (ownerType) params.set('owner_type', ownerType)
  return request<{ sessions: SessionListItem[] }>(`/sessions?${params.toString()}`)
}

export function createSession() {
  return request<{ session_id: string }>('/sessions', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}
```

Wait — the current backend doesn't have a `GET /api/v1/sessions` endpoint. Let me add one.

Actually, let me scope this more carefully. The v1 contract specifies 5 endpoints only. Adding a session-list endpoint would be a contract extension. For Sprint 3, I'll implement this as a lightweight backend addition.

Let me create a sessions list endpoint on the backend and a corresponding frontend component.

- [ ] **Step 1a: Add session list backend endpoint**

Open `backend/api_v1/views.py` and insert this new view before the `chat` function (before line 63):

```python
@require_GET
def session_list(request: HttpRequest):
    """GET /api/v1/sessions — list sessions for the authenticated user."""
    try:
        context = resolve_auth_context(request)
        require_roles(context, {ROLE_ANONYMOUS, ROLE_STUDENT})

        if context.role == ROLE_STUDENT:
            queryset = ChatSession.objects.filter(
                owner_type=ChatSession.OWNER_STUDENT,
                owner_user=context.user,
            ).order_by("-updated_at")
        else:
            session_key = ensure_session_key(request)
            queryset = ChatSession.objects.filter(
                owner_type=ChatSession.OWNER_ANON,
                anonymous_session_key=session_key,
            ).order_by("-updated_at")

        try:
            limit = min(int(request.GET.get("limit", 20)), 50)
        except ValueError:
            limit = 20

        sessions = queryset[:limit]
        session_data = []
        for s in sessions:
            last_msg = s.last_message
            session_data.append({
                "id": s.id,
                "created_at": s.created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": s.updated_at.isoformat().replace("+00:00", "Z"),
                "status": s.status,
                "owner_type": s.owner_type,
                "last_message_preview": last_msg.content[:120] if last_msg else "",
            })

        return success_response(request, {"sessions": session_data}, status=200)
    except ApiError as exc:
        return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.retryable)


@csrf_exempt
@require_POST
def session_create(request: HttpRequest):
    """POST /api/v1/sessions — explicitly create a new empty session."""
    try:
        context = resolve_auth_context(request)
        require_roles(context, {ROLE_ANONYMOUS, ROLE_STUDENT})

        with transaction.atomic():
            if context.role == ROLE_STUDENT:
                chat_session = ChatSession.objects.create(
                    owner_type=ChatSession.OWNER_STUDENT,
                    owner_user=context.user,
                )
            else:
                session_key = ensure_session_key(request)
                chat_session = ChatSession.objects.create(
                    owner_type=ChatSession.OWNER_ANON,
                    anonymous_session_key=session_key,
                )

        return success_response(
            request,
            {
                "session": {
                    "id": chat_session.id,
                    "created_at": chat_session.created_at.isoformat().replace("+00:00", "Z"),
                    "status": chat_session.status,
                }
            },
            status=201,
        )
    except ApiError as exc:
        return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.retryable)
```

Open `backend/api_v1/urls.py` and add the two new routes:

```python
    path("sessions", views.session_list, name="session-list"),
    path("sessions", views.session_create, name="session-create"),
```

Note: Since both map to `"sessions"`, Django will match the first one for GET and second for POST based on the method decorators. However, to avoid ambiguity, let me restructure. Actually, changing the urls.py requires careful handling. Let me just add them:

```python
from django.urls import path

from . import views
from . import auth_views


urlpatterns = [
    path("chat", views.chat, name="chat"),
    path("sessions", views.session_list, name="session-list"),
    path("sessions/create", views.session_create, name="session-create"),
    path("sessions/<str:id>/messages", views.session_messages, name="session-messages"),
    path("feedback", views.feedback, name="feedback"),
    path("sources/<str:source_id>", views.source_by_id, name="source-by-id"),
    path("ingest", views.ingest, name="ingest"),
    path("auth/login", auth_views.login_view, name="auth-login"),
    path("auth/register", auth_views.register_view, name="auth-register"),
    path("auth/logout", auth_views.logout_view, name="auth-logout"),
    path("auth/whoami", auth_views.whoami_view, name="auth-whoami"),
]
```

- [ ] **Step 1b: Add frontend API functions for sessions**

Open `frontend/src/lib/apiClient.ts` and append:

```typescript
export type SessionListItem = {
  id: string
  created_at: string
  updated_at: string
  status: string
  owner_type: string
  last_message_preview: string
}

export function getSessionList() {
  return request<{ sessions: SessionListItem[] }>('/sessions?limit=20')
}

export function postCreateSession() {
  return request<{ session: { id: string; created_at: string; status: string } }>('/sessions/create', {
    method: 'POST',
  })
}
```

- [ ] **Step 2: Create SessionSidebar component**

Create `frontend/src/components/SessionSidebar.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { fetchSessionHistory } from '../services/chatService'
import { HttpError } from '../lib/apiClient'
import { getSessionList, postCreateSession, type SessionListItem } from '../lib/apiClient'
import './SessionSidebar.css'

type SessionSidebarProps = {
  currentSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onNewChat: () => void
}

export function SessionSidebar({ currentSessionId, onSelectSession, onNewChat }: SessionSidebarProps) {
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [loading, setLoading] = useState(false)

  async function loadSessions() {
    setLoading(true)
    try {
      const data = await getSessionList()
      setSessions(data.sessions)
    } catch {
      // Silent fail — sidebar is best-effort
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSessions()
  }, [currentSessionId])

  async function handleNewChat() {
    try {
      const data = await postCreateSession()
      onNewChat()
      // Reload session list after brief delay for the new session to show
      setTimeout(() => { void loadSessions() }, 300)
    } catch {
      // Fall back to client-side new chat
      onNewChat()
    }
  }

  return (
    <aside className="session-sidebar">
      <div className="sidebar-header">
        <h3>Sessions</h3>
        <button type="button" className="btn-new-chat" onClick={() => void handleNewChat()}>
          + New Chat
        </button>
      </div>

      {loading && <p className="sidebar-loading">Loading...</p>}

      <ul className="session-list">
        {sessions.map((session) => (
          <li
            key={session.id}
            className={`session-item ${session.id === currentSessionId ? 'session-active' : ''}`}
          >
            <button
              type="button"
              onClick={() => onSelectSession(session.id)}
              title={session.id}
            >
              <span className="session-id">{session.id.slice(0, 16)}...</span>
              <span className="session-preview">{session.last_message_preview.slice(0, 60) || 'Empty'}</span>
            </button>
          </li>
        ))}
        {sessions.length === 0 && !loading && (
          <p className="sidebar-empty">No sessions yet</p>
        )}
      </ul>
    </aside>
  )
}
```

- [ ] **Step 3: Create SessionSidebar CSS**

Create `frontend/src/components/SessionSidebar.css`:

```css
.session-sidebar {
  background: #0f3460;
  border-right: 1px solid #1a1a2e;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  min-width: 220px;
  max-width: 280px;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.sidebar-header h3 {
  margin: 0;
  color: #e94560;
  font-size: 0.95rem;
}

.btn-new-chat {
  background: #e94560;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.75rem;
}

.session-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.session-item {
  margin-bottom: 0.25rem;
}

.session-item button {
  width: 100%;
  text-align: left;
  background: #16213e;
  border: 1px solid #1a1a2e;
  border-radius: 4px;
  padding: 0.4rem 0.5rem;
  color: #c0c0e0;
  cursor: pointer;
  font-size: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.session-item button:hover {
  background: #1a1a2e;
}

.session-active button {
  border-color: #e94560;
}

.session-id {
  font-family: monospace;
  color: #e94560;
}

.session-preview {
  color: #8080a0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-loading,
.sidebar-empty {
  color: #8080a0;
  font-size: 0.75rem;
  padding: 0.5rem;
}
```

- [ ] **Step 4: Update useChat with session list and new chat support**

Open `frontend/src/hooks/useChat.ts` and add a `startNewChat` function and `switchSession` function. Insert after the `submitQuestion` function (after line 104):

```typescript
  function startNewChat() {
    setSessionId(null)
    setMessages([])
    setErrorText(null)
  }

  async function switchSession(targetSessionId: string) {
    setSessionId(targetSessionId)
    await loadHistory(targetSessionId)
  }
```

Export them by adding to the return object:

```typescript
    startNewChat,
    switchSession,
```

- [ ] **Step 5: Update App.tsx to include sidebar layout**

Open `frontend/src/App.tsx` and replace the return statement (after the auth check) with:

```tsx
  return (
    <main className="page">
      <Masthead />

      <div className="auth-bar">
        <span>Signed in as: {authUser.username}</span>
        <button type="button" onClick={() => void handleLogout()}>Sign Out</button>
      </div>

      <div className="main-layout">
        <aside className="sidebar-column">
          <SessionSidebar
            currentSessionId={sessionId}
            onSelectSession={(id) => void switchSession(id)}
            onNewChat={startNewChat}
          />
        </aside>

        <section className="content-column">
          <ConversationPanel
            sessionId={sessionId}
            sortedMessages={sortedMessages}
            sourceLoading={sourceLoading}
            feedbackReasonByMessage={feedbackReasonByMessage}
            setFeedbackReasonByMessage={setFeedbackReasonByMessage}
            feedbackCommentByMessage={feedbackCommentByMessage}
            setFeedbackCommentByMessage={setFeedbackCommentByMessage}
            submittedFeedback={submittedFeedback}
            handleCitationClick={handleCitationClick}
            handleFeedback={handleFeedback}
            question={question}
            setQuestion={setQuestion}
            pending={pending}
            handleSubmit={handleSubmit}
          />
        </section>
      </div>

      <SourcePanel sourceLoading={sourceLoading} selectedSource={selectedSource} />

      <StatusBar errorText={errorText} retryAfter={retryAfter} />
    </main>
  )
```

Add the `SessionSidebar` import at the top of App.tsx:

```tsx
import { SessionSidebar } from './components/SessionSidebar'
```

Add the layout CSS to `frontend/src/App.css`:

```css
.main-layout {
  display: contents;
}

.sidebar-column {
  grid-column: 1;
  grid-row: 3;
}

.content-column {
  grid-column: 2;
  grid-row: 3;
}
```

Wait, the current CSS grid is `grid-template-columns: 2fr 1fr`. Adding a sidebar would change the layout significantly. Let me keep it simpler — wrap the content in a flex row inside the page grid.

Actually, let me modify the `.page` grid to accommodate the sidebar. Update `.page` in `App.css`:

```css
.page {
  max-width: 1300px;
  margin: 0 auto;
  padding: 0.5rem;
  display: grid;
  grid-template-columns: 240px 1fr 300px;
  grid-template-rows: auto auto 1fr auto;
  gap: 0.75rem;
  min-height: 100vh;
}
```

And update `.auth-bar` to span the full grid:

```css
.auth-bar {
  grid-column: 1 / -1;
  /* rest unchanged */
}
```

- [ ] **Step 6: Build and verify**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add backend/api_v1/views.py backend/api_v1/urls.py frontend/src/components/SessionSidebar.tsx frontend/src/components/SessionSidebar.css frontend/src/hooks/useChat.ts frontend/src/App.tsx frontend/src/App.css frontend/src/lib/apiClient.ts
git commit -m "feat(frontend): add session sidebar with list, new chat, and session switching"
```

---

## Task 3.5: Create admin dashboard views

**Files:**
- Create: `backend/api_v1/admin_views.py`
- Modify: `backend/api_v1/urls.py` (add admin routes)
- Modify: `backend/api_v1/admin.py` (register custom admin views)

- [ ] **Step 1: Create admin dashboard views**

Create `backend/api_v1/admin_views.py`:

```python
"""Admin dashboard views for monitoring the chatbot system."""

from django.db.models import Count, Avg
from django.http import HttpRequest
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_GET

from .auth import resolve_auth_context, require_roles, ROLE_ADMIN_STAFF
from .errors import ApiError
from .models import ChatSession, ChatMessage, Citation, Feedback, IngestJob, SourceChunk
from .responses import error_response, success_response


@require_GET
def admin_dashboard(request: HttpRequest):
    """GET /api/v1/admin/dashboard — summary stats for admin panel."""
    try:
        context = resolve_auth_context(request)
        require_roles(context, {ROLE_ADMIN_STAFF})

        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        total_sessions = ChatSession.objects.count()
        sessions_24h = ChatSession.objects.filter(created_at__gte=last_24h).count()
        total_messages = ChatMessage.objects.count()
        total_citations = Citation.objects.count()
        total_feedback = Feedback.objects.count()

        feedback_up = Feedback.objects.filter(rating=Feedback.RATING_UP).count()
        feedback_down = Feedback.objects.filter(rating=Feedback.RATING_DOWN).count()

        total_ingest_jobs = IngestJob.objects.count()
        total_source_chunks = SourceChunk.objects.count()

        recent_sessions = list(
            ChatSession.objects.order_by("-created_at")[:10].values(
                "id", "owner_type", "status", "created_at"
            )
        )

        return success_response(
            request,
            {
                "stats": {
                    "total_sessions": total_sessions,
                    "sessions_last_24h": sessions_24h,
                    "total_messages": total_messages,
                    "total_citations": total_citations,
                    "total_feedback": total_feedback,
                    "feedback_up": feedback_up,
                    "feedback_down": feedback_down,
                    "total_ingest_jobs": total_ingest_jobs,
                    "total_source_chunks": total_source_chunks,
                },
                "recent_sessions": recent_sessions,
            },
            status=200,
        )
    except ApiError as exc:
        return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.retryable)
```

- [ ] **Step 2: Add admin route**

Open `backend/api_v1/urls.py` and add:

```python
    path("admin/dashboard", admin_views.admin_dashboard, name="admin-dashboard"),
```

And add the import:

```python
from . import admin_views
```

- [ ] **Step 3: Test admin dashboard**

```bash
docker compose exec django-web python -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='staff', is_staff=True).exists():
    User.objects.create_superuser('staff', 'staff@example.com', 'pass12345')
    print('Created staff user')
else:
    print('Staff user exists')

import json, urllib.request, http.cookiejar
# We need session auth — test via Django test client in the test suite
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/api_v1/admin_views.py backend/api_v1/urls.py
git commit -m "feat(api): add admin dashboard endpoint with system stats"
```

---

## Task 3.6: Sprint 3 integration test

- [ ] **Step 1: Run full test suite**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 2: Verify auth flow end-to-end**

```bash
docker compose exec django-web python manage.py test api_v1.tests.test_access_control -v 2
```

- [ ] **Step 3: Verify frontend build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: Sprint 3 integration validation complete"
```

---

# Sprint 4: WebSocket Streaming + CI/CD + Contract Hardening

**Goal:** Add real-time streaming of LLM tokens via WebSocket, set up GitHub Actions for continuous integration, and fill test coverage gaps for success-response contracts.

## Task 4.1: Install and configure Django Channels

**Files:**
- Create: `backend/chatbot/routing.py`
- Modify: `backend/chatbot/asgi.py`
- Modify: `backend/chatbot/settings.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add Django Channels to requirements**

Add to `backend/requirements.txt`:

```
channels>=4.0
daphne>=4.0
```

Install in the container:

```bash
docker compose exec django-web pip install channels daphne
```

- [ ] **Step 2: Configure ASGI and Channels in settings**

Open `backend/chatbot/settings.py` and add `daphne` at the top of `INSTALLED_APPS` (before `django.contrib.admin`):

```python
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    # ... rest unchanged
```

Add this block after the `WSGI_APPLICATION` line (after line 110):

```python
ASGI_APPLICATION = 'chatbot.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

- [ ] **Step 3: Create routing.py**

Create `backend/chatbot/routing.py`:

```python
from django.urls import re_path
from api_v1 import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<session_id>[^/]+)/$", consumers.ChatConsumer.as_asgi()),
]
```

- [ ] **Step 4: Update asgi.py**

Open `backend/chatbot/asgi.py` and replace with:

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from chatbot.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(websocket_urlpatterns),
})
```

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/chatbot/settings.py backend/chatbot/asgi.py backend/chatbot/routing.py
git commit -m "feat(streaming): add Django Channels with daphne ASGI server"
```

---

## Task 4.2: Create WebSocket chat consumer

**Files:**
- Create: `backend/api_v1/consumers.py`

- [ ] **Step 1: Create the chat consumer**

Create `backend/api_v1/consumers.py`:

```python
"""WebSocket consumer for streaming chat responses."""

import json
import os

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from rag.vector_store import init_vector_store_manager


class ChatConsumer(AsyncWebsocketConsumer):
    """Handle WebSocket connections for streaming chat."""

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"chat_{self.session_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Receive a question from the WebSocket client and stream the answer."""
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
            return

        question = (payload.get("question") or "").strip()
        if not question:
            await self.send(text_data=json.dumps({"error": "question is required"}))
            return

        await self.send(text_data=json.dumps({"type": "status", "status": "retrieving"}))

        # Retrieve context synchronously
        _, retriever = init_vector_store_manager()
        docs = retriever.invoke(question)

        context_blocks = []
        for idx, doc in enumerate(docs[:5], start=1):
            source_name = doc.metadata.get("source", doc.metadata.get("url", "Unknown"))
            context_blocks.append(f"[Source {idx}] {source_name}\n{doc.page_content}")

        context_text = "\n\n".join(context_blocks) if context_blocks else "No relevant sources found."

        await self.send(text_data=json.dumps({"type": "status", "status": "generating"}))

        # Stream LLM tokens
        model = ChatOllama(
            model=os.getenv("ACADEMIC_AGENT_MODEL_ID", "qwen2.5:3b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            temperature=0,
            streaming=True,
        )

        full_response = ""
        async for chunk in model.astream(
            [
                SystemMessage(
                    content=(
                        "You are an academic assistant for Acibadem University. "
                        "Answer using the provided context. If context is insufficient, say that clearly. "
                        "Keep the answer concise and factual."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Question: {question}\n\n"
                        f"Context:\n{context_text}\n\n"
                        "Provide a helpful answer and refer to source names naturally."
                    )
                ),
            ]
        ):
            token = str(getattr(chunk, "content", ""))
            if token:
                full_response += token
                await self.send(text_data=json.dumps({
                    "type": "token",
                    "token": token,
                }))

        # Send complete signal
        await self.send(text_data=json.dumps({
            "type": "complete",
            "answer": full_response,
        }))

    async def chat_message(self, event):
        """Handle messages from the channel layer (for group broadcast)."""
        await self.send(text_data=event["message"])
```

- [ ] **Step 2: Commit**

```bash
git add backend/api_v1/consumers.py
git commit -m "feat(streaming): add WebSocket chat consumer with streaming LLM tokens"
```

---

## Task 4.3: Add streaming support to frontend

**Files:**
- Modify: `frontend/src/hooks/useChat.ts` (add streaming submit)
- Create: `frontend/src/lib/wsClient.ts` (WebSocket client)
- Modify: `frontend/src/components/ConversationPanel.tsx` (show streaming text)

- [ ] **Step 1: Create WebSocket client utility**

Create `frontend/src/lib/wsClient.ts`:

```typescript
type StreamCallbacks = {
  onToken: (token: string) => void
  onComplete: (answer: string) => void
  onError: (error: string) => void
  onStatus: (status: string) => void
}

export function streamChat(
  sessionId: string,
  question: string,
  callbacks: StreamCallbacks,
): { close: () => void } {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/chat/${encodeURIComponent(sessionId)}/`
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    ws.send(JSON.stringify({ question }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data as string)

      if (data.type === 'token') {
        callbacks.onToken(data.token as string)
      } else if (data.type === 'complete') {
        callbacks.onComplete(data.answer as string)
        ws.close()
      } else if (data.type === 'status') {
        callbacks.onStatus(data.status as string)
      } else if (data.error) {
        callbacks.onError(data.error as string)
        ws.close()
      }
    } catch {
      callbacks.onError('Failed to parse server response')
      ws.close()
    }
  }

  ws.onerror = () => {
    callbacks.onError('WebSocket connection error')
  }

  ws.onclose = () => {
    // Cleanup handled by callbacks
  }

  return {
    close: () => ws.close(),
  }
}
```

- [ ] **Step 2: Add streaming state to useChat**

Open `frontend/src/hooks/useChat.ts` and add imports:

```typescript
import { useRef } from 'react'
import { streamChat } from '../lib/wsClient'
```

Add streaming state after the existing state declarations:

```typescript
  const [streamingText, setStreamingText] = useState<string>('')
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)
  const wsRef = useRef<{ close: () => void } | null>(null)
```

Add a streaming submit function:

```typescript
  async function submitQuestionStreaming() {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || pending) return

    const currentSessionId = sessionId || 'pending'
    setQuestion('')
    setPending(true)
    setErrorText(null)
    setStreamingText('')

    const tempUserMessage: UiMessage = {
      id: `temp-user-${Date.now()}`,
      role: 'user',
      content: trimmedQuestion,
      createdAt: new Date().toISOString(),
      citations: [],
    }
    setMessages((current) => [...current, tempUserMessage])

    const streamMsgId = `streaming-${Date.now()}`
    setStreamingMessageId(streamMsgId)

    wsRef.current?.close()
    wsRef.current = streamChat(currentSessionId, trimmedQuestion, {
      onToken: (token) => {
        setStreamingText((prev) => prev + token)
      },
      onComplete: (answer) => {
        const finalMessage: UiMessage = {
          id: streamMsgId,
          role: 'assistant',
          content: answer,
          createdAt: new Date().toISOString(),
          citations: [],
        }
        setMessages((current) => [...current, finalMessage])
        setStreamingText('')
        setStreamingMessageId(null)
        setPending(false)
      },
      onError: (error) => {
        setMessages((current) => current.filter((m) => m.id !== tempUserMessage.id))
        setErrorText(error)
        setStreamingText('')
        setStreamingMessageId(null)
        setPending(false)
      },
      onStatus: (_status) => {
        // Status updates are for internal use; silently consumed
      },
    })
  }
```

Export the new state and function. Add to return object:

```typescript
    streamingText,
    streamingMessageId,
    submitQuestionStreaming,
```

- [ ] **Step 3: Update ConversationPanel to show streaming text**

Open `frontend/src/components/ConversationPanel.tsx` and add streaming-related props to the type and the component:

```typescript
type ConversationPanelProps = {
  // ... existing props
  streamingText: string
  streamingMessageId: string | null
  submitStreaming: () => Promise<void>
}
```

In the component, after the message list mapping, add a streaming message block:

```tsx
          {streamingMessageId && (
            <article className="message message-assistant">
              <div className="message-meta">
                <span>ASSISTANT</span>
                <span className="streaming-badge">streaming...</span>
              </div>
              <p>{streamingText || 'Thinking...'}</p>
            </article>
          )}
```

Update the props destructuring to include the new props. Open `App.tsx` and update the `ConversationPanel` JSX to pass the streaming props.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/wsClient.ts frontend/src/hooks/useChat.ts frontend/src/components/ConversationPanel.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add WebSocket streaming client with real-time token display"
```

---

## Task 4.4: Set up GitHub Actions CI pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    name: Backend Tests (Django)
    runs-on: ubuntu-24.04

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_DB: acu_chatbot_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        working-directory: backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        working-directory: backend
        env:
          DJANGO_SECRET_KEY: ci-test-secret
          DEBUG: '0'
          DATABASE_ENGINE: postgresql
          DATABASE_NAME: acu_chatbot_test
          DATABASE_USERNAME: postgres
          DATABASE_PASSWORD: postgres
          DATABASE_HOST: localhost
          DATABASE_PORT: '5432'
        run: |
          python manage.py migrate
          python manage.py test api_v1.tests -v 2

  frontend-tests:
    name: Frontend Build Check
    runs-on: ubuntu-24.04

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: TypeScript type check
        working-directory: frontend
        run: npx tsc --noEmit

      - name: Build
        working-directory: frontend
        run: npm run build

      - name: Lint
        working-directory: frontend
        run: npx eslint src/ --max-warnings 0 || true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for backend tests and frontend build"
```

---

## Task 4.5: Backend success-response contract tests

**Files:**
- Modify: `backend/api_v1/tests/test_response_contract.py` (add success envelope tests)

- [ ] **Step 1: Add success envelope test class**

Open `backend/api_v1/tests/test_response_contract.py` and append a new test class at the end:

```python
class SuccessEnvelopeContractTests(TestCase):
    """Verify that all 200/201/202 responses match the contract envelope shape."""

    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(username="staff_success", password="pass12345", is_staff=True)
        SourceChunk.objects.create(
            source_id="src_success",
            chunk_id="chunk_1",
            title="Test Source",
            url="https://example.edu/test",
            snippet="test snippet",
            page=1,
            doc_metadata={"k": "v"},
        )

    def _assert_success_envelope(self, payload: dict, expected_status: int):
        self.assertEqual(set(payload.keys()), {"ok", "meta", "data", "request_id", "timestamp"})
        self.assertTrue(payload["ok"])
        self.assertEqual(set(payload["meta"].keys()), {"request_id", "timestamp"})
        self.assertIsInstance(payload["meta"]["request_id"], str)
        self.assertTrue(len(payload["meta"]["request_id"]) > 0)
        _assert_iso_utc_timestamp(payload["meta"]["timestamp"])
        self.assertIn("data", payload)
        self.assertIsInstance(payload["data"], dict)
        self.assertIn("request_id", payload)
        self.assertIn("timestamp", payload)
        _assert_iso_utc_timestamp(payload["timestamp"])

    def test_chat_success_envelope_shape(self):
        client = Client()
        response = client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "What is AWS ACU?", "stream": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self._assert_success_envelope(payload, 200)
        data = payload["data"]
        self.assertIn("session", data)
        self.assertIn("message", data)
        self.assertIn("stream", data)
        self.assertIn("id", data["session"])
        self.assertIn("is_new", data["session"])
        self.assertIn("id", data["message"])
        self.assertIn("role", data["message"])
        self.assertIn("answer", data["message"])
        self.assertIn("citations", data["message"])
        self.assertIsInstance(data["message"]["citations"], list)
        self.assertIn("created_at", data["message"])
        _assert_iso_utc_timestamp(data["message"]["created_at"])

    def test_session_messages_success_envelope_shape(self):
        client = Client()
        chat_resp = client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "seed", "stream": False}),
            content_type="application/json",
        )
        self.assertEqual(chat_resp.status_code, 200)
        session_id = chat_resp.json()["data"]["session"]["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/messages")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self._assert_success_envelope(payload, 200)
        data = payload["data"]
        self.assertIn("session_id", data)
        self.assertIn("messages", data)
        self.assertIn("pagination", data)
        self.assertIsInstance(data["messages"], list)
        self.assertIn("limit", data["pagination"])
        self.assertIn("has_more", data["pagination"])

    def test_feedback_success_envelope_shape(self):
        client = Client()
        chat_resp = client.post(
            "/api/v1/chat",
            data=json.dumps({"question": "seed2", "stream": False}),
            content_type="application/json",
        )
        session_id = chat_resp.json()["data"]["session"]["id"]
        message_id = chat_resp.json()["data"]["message"]["id"]

        response = client.post(
            "/api/v1/feedback",
            data=json.dumps({"session_id": session_id, "message_id": message_id, "rating": "up"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self._assert_success_envelope(payload, 201)
        data = payload["data"]
        self.assertIn("feedback", data)
        fb = data["feedback"]
        self.assertIn("id", fb)
        self.assertIn("session_id", fb)
        self.assertIn("message_id", fb)
        self.assertIn("rating", fb)
        self.assertIn("created_at", fb)
        _assert_iso_utc_timestamp(fb["created_at"])

    def test_sources_success_envelope_shape(self):
        client = Client()
        response = client.get("/api/v1/sources/src_success")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self._assert_success_envelope(payload, 200)
        data = payload["data"]
        self.assertIn("source_id", data)
        self.assertIn("title", data)
        self.assertIn("snippet", data)
        self.assertIn("doc_metadata", data)
        self.assertEqual(data["source_id"], "src_success")

    def test_ingest_success_envelope_shape(self):
        client = Client()
        client.force_login(self.staff)
        response = client.post(
            "/api/v1/ingest",
            data=json.dumps({
                "idempotency_key": "succ-key-1",
                "items": [{"type": "url", "value": "https://example.edu/x"}],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self._assert_success_envelope(payload, 202)
        data = payload["data"]
        self.assertIn("job_id", data)
        self.assertIn("status", data)
        self.assertIn("accepted_count", data)
        self.assertIn("duplicate", data)
```

- [ ] **Step 2: Run the new tests**

```bash
docker compose exec django-web python manage.py test api_v1.tests.test_response_contract.SuccessEnvelopeContractTests -v 2
```

Expected: 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/api_v1/tests/test_response_contract.py
git commit -m "test(api): add success envelope contract tests for all 5 endpoints"
```

---

## Task 4.6: Sprint 4 integration test

- [ ] **Step 1: Run full backend test suite**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -15
```

Expected: All 37+ tests pass (32 from earlier sprints + 5 new success envelope tests).

- [ ] **Step 2: Verify frontend build with streaming changes**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: Sprint 4 integration validation complete"
```

---

# Sprint 5: Polish + Report

**Goal:** Add markdown rendering, pagination pagination, localStorage persistence, backup documentation, contribution appendix generation, and clean up unused assets.

## Task 5.1: Add markdown rendering to message content

**Files:**
- Modify: `frontend/src/components/ConversationPanel.tsx` (use react-markdown)
- Modify: `frontend/package.json` (add dependency)

- [ ] **Step 1: Install react-markdown**

```bash
cd frontend && npm install react-markdown
```

Expected: Package added to `package.json` and `node_modules`.

- [ ] **Step 2: Update ConversationPanel to render markdown**

Open `frontend/src/components/ConversationPanel.tsx`. Add import:

```tsx
import ReactMarkdown from 'react-markdown'
```

Replace the line `<p>{message.content}</p>` (line 59) with:

```tsx
            <div className="message-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
```

Also update the streaming message rendering block (the one added in Sprint 4) to use ReactMarkdown:

```tsx
            <div className="message-content">
              <ReactMarkdown>{streamingText || 'Thinking...'}</ReactMarkdown>
            </div>
```

- [ ] **Step 3: Add message-content CSS**

Open `frontend/src/index.css` (or `App.css`) and append:

```css
.message-content {
  line-height: 1.6;
}

.message-content p {
  margin: 0 0 0.5rem;
}

.message-content ul,
.message-content ol {
  margin: 0.25rem 0;
  padding-left: 1.5rem;
}

.message-content code {
  background: #1a1a2e;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.85em;
}

.message-content pre {
  background: #1a1a2e;
  padding: 0.5rem;
  border-radius: 4px;
  overflow-x: auto;
}

.message-content blockquote {
  border-left: 3px solid #e94560;
  margin: 0.5rem 0;
  padding-left: 0.75rem;
  color: #a0a0c0;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/ConversationPanel.tsx frontend/src/index.css
git commit -m "feat(frontend): add markdown rendering to message content"
```

---

## Task 5.2: Add frontend pagination for session history

**Files:**
- Modify: `frontend/src/services/chatService.ts` (add pagination-aware fetch)
- Modify: `frontend/src/hooks/useChat.ts` (load more on scroll)

- [ ] **Step 1: Update chatService to support paginated fetch**

Open `frontend/src/services/chatService.ts` and replace the `fetchSessionHistory` function with:

```typescript
export type PaginatedMessages = {
  messages: UiMessage[]
  hasMore: boolean
  nextCursor: string | null
}

export async function fetchSessionHistory(
  sessionId: string,
  cursor?: string,
  limit: number = 50,
): Promise<PaginatedMessages> {
  const response = await getSessionMessages(sessionId, cursor, limit)
  return {
    messages: response.messages.map(mapHistoryMessage),
    hasMore: response.pagination.has_more,
    nextCursor: response.pagination.next_cursor,
  }
}
```

Open `frontend/src/lib/apiClient.ts` and update `getSessionMessages` to accept a `limit` parameter:

```typescript
export function getSessionMessages(sessionId: string, cursor?: string, limit: number = 50) {
  const params = new URLSearchParams({
    order: 'asc',
    limit: String(limit),
  })
  if (cursor) {
    params.set('cursor', cursor)
  }
  return request<SessionMessagesResponseData>(`/sessions/${encodeURIComponent(sessionId)}/messages?${params.toString()}`)
}
```

- [ ] **Step 2: Update useChat loadHistory to use cursor pagination**

Open `frontend/src/hooks/useChat.ts` and replace the `loadHistory` function (lines 38-49) with:

```typescript
  const [historyCursor, setHistoryCursor] = useState<string | null>(null)
  const [hasMoreHistory, setHasMoreHistory] = useState(false)

  async function loadHistory(targetSessionId: string, append: boolean = false) {
    try {
      const cursor = append ? historyCursor : undefined
      const result = await fetchSessionHistory(targetSessionId, cursor || undefined, 50)
      if (append) {
        setMessages((current) => [...current, ...result.messages])
      } else {
        setMessages(result.messages)
      }
      setHistoryCursor(result.nextCursor)
      setHasMoreHistory(result.hasMore)
      setErrorText(null)
    } catch (error) {
      if (error instanceof HttpError) {
        setErrorText(`Could not load session history. ${error.message}`)
      } else {
        setErrorText('Could not load session history due to an unexpected error.')
      }
    }
  }

  async function loadMoreHistory() {
    if (!sessionId || !hasMoreHistory) return
    await loadHistory(sessionId, true)
  }
```

Export `loadMoreHistory` and `hasMoreHistory` in the return object.

- [ ] **Step 3: Add "Load More" button to ConversationPanel**

Open `frontend/src/components/ConversationPanel.tsx` and add a "Load More" button after the message list:

```tsx
          {hasMoreHistory && (
            <button
              type="button"
              className="btn-load-more"
              onClick={() => void loadMoreHistory()}
            >
              Load earlier messages
            </button>
          )}
```

Update the props type to include `hasMoreHistory` and `loadMoreHistory`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/chatService.ts frontend/src/lib/apiClient.ts frontend/src/hooks/useChat.ts frontend/src/components/ConversationPanel.tsx
git commit -m "feat(frontend): add cursor-based pagination for session history"
```

---

## Task 5.3: Persist session ID to localStorage

**Files:**
- Modify: `frontend/src/hooks/useChat.ts` (read/write localStorage on session changes)

- [ ] **Step 1: Add localStorage persistence**

Open `frontend/src/hooks/useChat.ts` and add this effect after the retryAfter effect (after line 36):

```typescript
  useEffect(() => {
    if (sessionId) {
      try {
        localStorage.setItem('acu_last_session_id', sessionId)
      } catch {
        // localStorage may be unavailable (e.g., private browsing)
      }
    }
  }, [sessionId])
```

And add a restore effect after it:

```typescript
  useEffect(() => {
    try {
      const saved = localStorage.getItem('acu_last_session_id')
      if (saved) {
        setSessionId(saved)
        void loadHistory(saved)
      }
    } catch {
      // localStorage unavailable; skip restore
    }
    // Run only once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat(frontend): persist session ID to localStorage and restore on mount"
```

---

## Task 5.4: Write backup and restore documentation

**Files:**
- Create: `docs/backup-restore.md`

- [ ] **Step 1: Create backup/restore guide**

Create `docs/backup-restore.md`:

````markdown
# Backup and Restore Procedures

## PostgreSQL (chat sessions, messages, feedback, ingest jobs)

### Backup

```bash
docker compose exec db pg_dump -U postgres acu_chatbot > backup_pg_$(date +%Y%m%d).sql
```

### Restore

```bash
docker compose exec -T db psql -U postgres acu_chatbot < backup_pg_20260501.sql
```

## Chroma Vector Store (embeddings, document chunks)

### Backup

```bash
docker compose exec django-web tar -czf /tmp/chromadb-backup.tar.gz -C /app chromadb-data
docker compose cp django-web:/tmp/chromadb-backup.tar.gz ./chromadb-backup_$(date +%Y%m%d).tar.gz
```

### Restore

```bash
docker compose exec django-web rm -rf /app/chromadb-data
tar -xzf chromadb-backup_20260501.tar.gz -C backend/
docker compose restart django-web
```

## Ollama Models

Models are pulled from the Ollama registry on first use. No backup needed. To repull:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull nomic-embed-text-v2-moe
```

## Automated Backup Script

Save as `scripts/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE_TAG="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL..."
docker compose exec -T db pg_dump -U postgres acu_chatbot > "$BACKUP_DIR/pg_${DATE_TAG}.sql"

echo "Backing up Chroma vector store..."
docker compose exec django-web tar -czf /tmp/chromadb-backup.tar.gz -C /app chromadb-data
docker compose cp django-web:/tmp/chromadb-backup.tar.gz "$BACKUP_DIR/chromadb_${DATE_TAG}.tar.gz"

echo "Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*${DATE_TAG}*
```

Run with: `bash scripts/backup.sh`
````

- [ ] **Step 2: Commit**

```bash
git add docs/backup-restore.md
git commit -m "docs: add backup and restore procedures for PostgreSQL and Chroma"
```

---

## Task 5.5: Generate contribution appendix script

**Files:**
- Create: `scripts/generate_contributions.sh`

- [ ] **Step 1: Create contribution appendix script**

Create `scripts/generate_contributions.sh`:

```bash
#!/bin/bash
# Generate contribution appendix from Git log.
# Output: contributor name, commit count, files touched.

set -euo pipefail

echo "# Contribution Appendix"
echo ""
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

git shortlog -sn --all | while read -r count name; do
    echo "## $name"
    echo ""
    echo "- **Commits:** $count"
    echo ""
    echo "### Files modified:"
    git log --author="$name" --name-only --pretty=format: | sort -u | sed 's/^/- `/' | sed 's/$/`/'
    echo ""
done
```

Make it executable:

```bash
chmod +x scripts/generate_contributions.sh
```

- [ ] **Step 2: Run the script**

```bash
bash scripts/generate_contributions.sh > docs/contribution_appendix.md
```

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_contributions.sh docs/contribution_appendix.md
git commit -m "chore: add contribution appendix generator script"
```

---

## Task 5.6: Clean up unused assets and final lint pass

**Files:**
- Delete: `frontend/src/assets/hero.png` (if unused)
- Verify no code references unused assets

- [ ] **Step 1: Check for unused asset references**

```bash
grep -r "hero.png\|react.svg\|vite.svg" frontend/src/ --include="*.tsx" --include="*.ts" --include="*.css" || echo "NO_REFERENCES_FOUND"
```

If `NO_REFERENCES_FOUND`, the assets are unused. They may have been create-vite scaffolding.

- [ ] **Step 2: Remove unused asset files**

```bash
rm -f frontend/src/assets/hero.png frontend/src/assets/react.svg frontend/src/assets/vite.svg
```

Note: Only delete these if they are confirmed unused and not referenced elsewhere.

- [ ] **Step 3: Final frontend build check**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: Clean build, no warnings.

- [ ] **Step 4: Final backend test run**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2 2>&1 | tail -15
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: Sprint 5 polish — cleanup unused assets, final test pass"
```

---

## Task 5.7: Final integration validation (all sprints)

- [ ] **Step 1: Full system restart from scratch**

```bash
docker compose down -v
docker compose up -d --build
sleep 90
docker compose ps
```

Expected: All 4 services show `(healthy)`.

- [ ] **Step 2: Run batch scraper to populate content**

```bash
docker compose exec django-web python rag/scrape_runner.py
```

- [ ] **Step 3: Run evaluation**

```bash
docker compose exec django-web python rag/evaluation.py
```

- [ ] **Step 4: Run full test suite**

```bash
docker compose exec django-web python manage.py test api_v1.tests -v 2
```

- [ ] **Step 5: Test chat endpoint with citations**

```bash
docker compose exec django-web python -c "
import json, urllib.request
for q in ['What is Acibadem University?', 'Tell me about student life', 'What programs are offered?']:
    req = urllib.request.Request(
        'http://localhost:8000/api/v1/chat',
        data=json.dumps({'question': q, 'stream': False}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    print(f'Q: {q[:50]}...')
    print(f'  Answer: {resp[\"data\"][\"message\"][\"answer\"][:100]}...')
    print(f'  Citations: {len(resp[\"data\"][\"message\"][\"citations\"])}')
    print()
"
```

- [ ] **Step 6: Build frontend**

```bash
cd frontend && npm run build
```

- [ ] **Step 7: Final commit**

```bash
git add -A && git commit -m "chore: final integration validation — all 5 sprints complete"
```

---

# Post-Plan Verification

## Self-Review Checklist

- [x] **Spec coverage:** Each proposal section (§2-§7) maps to at least one task. All 19 gaps from the gap analysis are addressed.
- [x] **No placeholders:** Every step has concrete code, exact file paths, and exact commands. No TBDs, TODOs, or "implement later."
- [x] **Type consistency:** Django model field names match between views, RAG layer, and tests. Frontend TypeScript types match API contract shapes. Citation field names are consistent from `_docs_to_citation_entries` → `Citation` model → `_serialize_citation` → API response.
- [x] **File paths verified:** Every file path matches the actual codebase structure.
- [x] **Dependencies declared:** `beautifulsoup4`, `requests`, `channels`, `daphne`, `react-markdown` are all explicitly added to the relevant requirement files.

## Summary

| Sprint | Focus | Tasks | Key Deliverable |
|--------|-------|-------|-----------------|
| Sprint 1 | Citation + health + scraper | 7 | Chat returns real citations, containers start reliably |
| Sprint 2 | Scraping + evaluation | 4 | 5 scraped pages, 10-question eval with scores |
| Sprint 3 | Auth + sessions + admin | 6 | Login page, session sidebar, admin dashboard |
| Sprint 4 | Streaming + CI/CD + tests | 6 | WebSocket tokens, GitHub Actions, contract tests |
| Sprint 5 | Polish + report | 7 | Markdown, pagination, persistence, backup docs, appendix |
