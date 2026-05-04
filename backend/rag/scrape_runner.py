"""Batch scraper orchestrator.

Two-phase scrape:
  Phase 1 — Drupal site (acibadem.edu.tr): fetch all pre-configured pages
  Phase 2 — Bologna site (obs.acibadem.edu.tr):
    a) Fetch all static dynConPage pages (institution info, student info, etc.)
    b) Fetch all degree-level program listings (unitSelection.aspx)
    c) For each discovered program, fetch all detail sub-pages

All content is chunked and added to the vector store.

Usage:
  docker compose exec backend python rag/scrape_runner.py
  docker compose exec backend python rag/scrape_runner.py --dry-run   # show what would be scraped
  docker compose exec backend python rag/scrape_runner.py --bologna-only
  docker compose exec backend python rag/scrape_runner.py --drupal-only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running this script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.vector_store import init_vector_store_manager
from rag.web_scrape_processor import WebScrapeProcessor
from rag.scrape_targets import (
    build_drupal_full_urls,
    build_bologna_static_urls,
    build_bologna_unit_selection_urls,
    build_program_detail_url,
    BOLOGNA_PROGRAM_SUBPAGES,
)

#from printmeup import printmeup as pm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Summary / reporting
# ---------------------------------------------------------------------------

class BatchStats:
    """Track scraping and ingestion statistics."""

    def __init__(self) -> None:
        self.drupal = {"total": 0, "ingested": 0, "failed": 0, "chunks": 0, "details": []}
        self.bologna_static = {"total": 0, "ingested": 0, "failed": 0, "chunks": 0, "details": []}
        self.bologna_programs = {"total": 0, "ingested": 0, "failed": 0, "chunks": 0,
                                 "program_count": 0, "details": []}
        self.start_time = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return {
            "drupal": self.drupal,
            "bologna_static": self.bologna_static,
            "bologna_programs": self.bologna_programs,
            "totals": {
                "ingested": (
                    self.drupal["ingested"]
                    + self.bologna_static["ingested"]
                    + self.bologna_programs["ingested"]
                ),
                "failed": (
                    self.drupal["failed"]
                    + self.bologna_static["failed"]
                    + self.bologna_programs["failed"]
                ),
                "total_chunks": (
                    self.drupal["chunks"]
                    + self.bologna_static["chunks"]
                    + self.bologna_programs["chunks"]
                ),
            },
            "elapsed_seconds": elapsed,
            "timestamp": self.start_time.isoformat().replace("+00:00", "Z"),
        }


# ---------------------------------------------------------------------------
# Phase 1 — Drupal site
# ---------------------------------------------------------------------------

def scrape_drupal_pages(processor: WebScrapeProcessor, stats: BatchStats,
                        vector_store_manager, dry_run: bool = False) -> None:
    """Scrape all pre-configured Drupal pages."""
    targets = build_drupal_full_urls()
    stats.drupal["total"] = len(targets)

    logger.info(f"Phase 1: Scraping {len(targets)} Drupal pages...")

    for target in targets:
        url = target["url"]
        title = target["title"]
        tag = target["source_tag"]
        category = target.get("category", "")

        logger.info(f"  [{category}] {title}")

        if dry_run:
            stats.drupal["details"].append({
                "url": url, "title": title, "status": "dry_run",
            })
            continue
        
        # Fetch the Drupal page
        doc = processor.fetch_drupal_page(url, title=title, source_tag=tag)
        if doc is None:
            stats.drupal["failed"] += 1
            stats.drupal["details"].append({
                "url": url, "title": title, "status": "failed",
            })
            continue
        
        # Split into chunks and add to vector store
        chunks = processor.split_documents_into_chunks([doc])
        if not chunks:
            stats.drupal["failed"] += 1
            stats.drupal["details"].append({
                "url": url, "title": title, "status": "no_chunks",
            })
            continue

        ok = vector_store_manager.add_chunks(chunks)
        if ok:
            stats.drupal["ingested"] += 1
            stats.drupal["chunks"] += len(chunks)
            stats.drupal["details"].append({
                "url": url, "title": title, "status": "ingested",
                "chunk_count": len(chunks),
            })
            logger.info(f"    ✓ {len(chunks)} chunks ingested")
        else:
            stats.drupal["failed"] += 1
            stats.drupal["details"].append({
                "url": url, "title": title, "status": "vector_add_failed",
            })

    logger.info(
        f"Drupal phase complete: {stats.drupal['ingested']}/{stats.drupal['total']} "
        f"ingested, {stats.drupal['chunks']} chunks"
    )


# ---------------------------------------------------------------------------
# Phase 2 — Bologna site
# ---------------------------------------------------------------------------

def scrape_bologna_static(processor: WebScrapeProcessor, stats: BatchStats,
                          vector_store_manager, dry_run: bool = False) -> None:
    """Scrape all Bologna static dynConPage pages."""
    targets = build_bologna_static_urls()
    stats.bologna_static["total"] = len(targets)

    logger.info(f"Phase 2a: Scraping {len(targets)} Bologna static pages...")

    for target in targets:
        url = target["url"]
        title = target["title"]
        category = target.get("category", "")

        logger.info(f"  [{category}] {title}")

        if dry_run:
            stats.bologna_static["details"].append({
                "url": url, "title": title, "status": "dry_run",
            })
            continue

        doc = processor.fetch_bologna_static_page(url, title=title, source_tag=url)
        if doc is None:
            stats.bologna_static["failed"] += 1
            stats.bologna_static["details"].append({
                "url": url, "title": title, "status": "failed",
            })
            continue

        chunks = processor.split_documents_into_chunks([doc])
        if not chunks:
            stats.bologna_static["failed"] += 1
            stats.bologna_static["details"].append({
                "url": url, "title": title, "status": "no_chunks",
            })
            continue

        ok = vector_store_manager.add_chunks(chunks)
        if ok:
            stats.bologna_static["ingested"] += 1
            stats.bologna_static["chunks"] += len(chunks)
            stats.bologna_static["details"].append({
                "url": url, "title": title, "status": "ingested",
                "chunk_count": len(chunks),
            })
            logger.info(f"    ✓ {len(chunks)} chunks ingested")
        else:
            stats.bologna_static["failed"] += 1
            stats.bologna_static["details"].append({
                "url": url, "title": title, "status": "vector_add_failed",
            })

    logger.info(
        f"Bologna static phase complete: "
        f"{stats.bologna_static['ingested']}/{stats.bologna_static['total']} "
        f"ingested, {stats.bologna_static['chunks']} chunks"
    )


def scrape_bologna_programs(processor: WebScrapeProcessor, stats: BatchStats,
                            vector_store_manager, dry_run: bool = False,
                            max_programs_per_level: int = 0) -> None:
    """Scrape Bologna program listings and detail pages.

    For each degree level, discover all programs, then scrape every
    sub-page (admission reqs, learning outcomes, courses, etc.).
    """
    logger.info("Phase 2b: Scraping Bologna program listings and detail pages...")

    degree_urls = build_bologna_unit_selection_urls()
    all_programs: list[dict] = []

    # --- Step 1: Discover all programs across all degree levels ---
    for level in degree_urls:
        logger.info(f"  Discovering {level['level']} programs...")
        programs = processor.fetch_bologna_program_listing(
            level["url"], level["level"]
        )
        if programs:
            all_programs.extend(programs)
            logger.info(f"    Found {len(programs)} programs")
        else:
            logger.warning(f"    No programs found for {level['level']}")

    stats.bologna_programs["program_count"] = len(all_programs)
    logger.info(f"Total programs discovered: {len(all_programs)}")

    if max_programs_per_level > 0:
        logger.info(f"  Limiting to {max_programs_per_level} programs (testing mode)")
        # Keep programs from different levels proportionally
        from itertools import groupby
        all_programs.sort(key=lambda p: p["degree_level"])
        limited: list[dict] = []
        for _level, group in groupby(all_programs, key=lambda p: p["degree_level"]):
            group_list = list(group)
            limited.extend(group_list[:max_programs_per_level])
        all_programs = limited
        logger.info(f"  After limiting: {len(all_programs)} programs")

    # --- Step 2: For each program, scrape all detail sub-pages ---
    for prog in all_programs:
        cur_sunit = prog["cur_sunit"]
        prog_name = prog["program_name"]
        degree = prog["degree_level"]

        logger.info(f"  [{degree}] {prog_name} (curSunit={cur_sunit})")

        prog_chunks_total = 0
        prog_pages_ingested = 0
        prog_pages_failed = 0

        for subpage in BOLOGNA_PROGRAM_SUBPAGES:
            func = subpage["func"]
            label = subpage["label"]
            detail_url = build_program_detail_url(cur_sunit, func)

            doc_title = f"{prog_name} — {label}"

            if dry_run:
                prog_pages_ingested += 1
                continue

            doc = processor.fetch_bologna_program_detail(detail_url, title=doc_title)
            if doc is None:
                prog_pages_failed += 1
                continue

            chunks = processor.split_documents_into_chunks([doc])
            if not chunks:
                prog_pages_failed += 1
                continue

            ok = vector_store_manager.add_chunks(chunks)
            if ok:
                prog_pages_ingested += 1
                prog_chunks_total += len(chunks)
                logger.info(f"      [{func}] ✓ {len(chunks)} chunks")
            else:
                prog_pages_failed += 1
                logger.warning(f"      [{func}] ✗ add_chunks failed ({len(chunks)} chunks)")

        stats.bologna_programs["ingested"] += prog_pages_ingested
        stats.bologna_programs["failed"] += prog_pages_failed
        stats.bologna_programs["chunks"] += prog_chunks_total
        stats.bologna_programs["total"] += (prog_pages_ingested + prog_pages_failed)

        if prog_pages_ingested > 0:
            logger.info(
                f"    ✓ {prog_pages_ingested} detail pages ingested "
                f"({prog_chunks_total} chunks)"
            )

    logger.info(
        f"Bologna programs phase complete: "
        f"{stats.bologna_programs['ingested']} detail pages ingested, "
        f"{stats.bologna_programs['chunks']} chunks, "
        f"{stats.bologna_programs['program_count']} programs"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_batch_scrape(dry_run: bool = False,
                     drupal_only: bool = False,
                     bologna_only: bool = False,
                     max_programs_per_level: int = 0) -> dict:
    """Run the full batch scrape across both sites."""
    vsm, _ = init_vector_store_manager()
    processor = WebScrapeProcessor()
    stats = BatchStats()

    do_drupal = not bologna_only
    do_bologna = not drupal_only

    if do_drupal:
        scrape_drupal_pages(processor, stats, vsm, dry_run=dry_run)

    if do_bologna:
        scrape_bologna_static(processor, stats, vsm, dry_run=dry_run)
        scrape_bologna_programs(
            processor, stats, vsm,
            dry_run=dry_run,
            max_programs_per_level=max_programs_per_level,
        )

    result = stats.to_dict()

    # Print summary
    totals = result["totals"]
    logger.info("=" * 50)
    logger.info("BATCH SCRAPE COMPLETE")
    logger.info(f"  Ingested: {totals['ingested']} pages")
    logger.info(f"  Failed:   {totals['failed']} pages")
    logger.info(f"  Chunks:   {totals['total_chunks']}")
    logger.info(f"  Time:     {result['elapsed_seconds']:.1f}s")
    logger.info(f"  Drupal:       {stats.drupal['ingested']}/{stats.drupal['total']} ingested")
    logger.info(f"  Bologna:      {stats.bologna_static['ingested']}/{stats.bologna_static['total']} ingested")
    logger.info(f"  Programs:     {stats.bologna_programs['program_count']} programs, "
                f"{stats.bologna_programs['ingested']} detail pages")
    logger.info("=" * 50)

    # Save report
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    report_path = logs_dir / "scrape_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info(f"Report saved to {report_path}")

    return result


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ACU Batch Web Scraper")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be scraped without fetching")
    parser.add_argument("--drupal-only", action="store_true",
                        help="Only scrape Drupal (main site)")
    parser.add_argument("--bologna-only", action="store_true",
                        help="Only scrape Bologna (info package)")
    parser.add_argument("--max-programs", type=int, default=0,
                        help="Max programs per degree level (0=all, use 1-2 for testing)")
    parser.add_argument("--report", type=str, default="",
                        help="Path to save JSON report (default: logs/scrape_report.json)")

    args = parser.parse_args()

    result = run_batch_scrape(
        dry_run=args.dry_run,
        drupal_only=args.drupal_only,
        bologna_only=args.bologna_only,
        max_programs_per_level=args.max_programs,
    )

    # Optionally save report to custom path
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"Report also saved to {args.report}")
