"""
pipeline.py

Runs the full lead-gen flow end to end:
    1. search_sourcing.py  -> candidate URLs from DuckDuckGo queries
    2. detector.py logic    -> keep only confirmed Wix stores
    3. age_scorer.py logic  -> tag NEW vs ESTABLISHED
    4. writes final leads CSV, NEW leads first

Usage:
    python pipeline.py --queries queries.txt --out output/leads.csv
"""

import csv
import argparse
import os
from urllib.parse import urlparse

from search_sourcing import run as run_search
from builtwith_sourcing import source_platform as source_builtwith
from directory_sourcing import source_platform as source_directory
from detector import detect_platform
from age_scorer import score_domain
from contact_extractor import get_contacts
from platform_config import get_config


def load_lines(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Full multi-platform lead-gen pipeline.")
    parser.add_argument("--queries", help="Path to seed queries file (auto-picked from --platform if omitted)")
    parser.add_argument("--candidates-out", default="output/candidates.txt")
    parser.add_argument("--out", help="Output CSV path (defaults to output/leads_<platform>.csv)")
    parser.add_argument("--platform", default="Wix",
                         help="Platform to filter for (Wix, Shopify, WooCommerce, WordPress, PrestaShop, BigCommerce)")
    parser.add_argument("--no-builtwith", action="store_true",
                         help="Skip BuiltWith's free list as an extra candidate source")
    args = parser.parse_args()

    # Platform config is the single source of truth — this guarantees Shopify
    # never touches Wix's queries file or Wix's BuiltWith list, and vice versa.
    config = get_config(args.platform)
    queries_path = args.queries or config["queries_file"]
    out_path = args.out or f"output/leads_{args.platform}.csv"

    # Step 1: source candidate URLs — search engines + BuiltWith's free sample list
    queries = load_lines(queries_path)
    print(f"Sourcing candidates from {len(queries)} queries ({queries_path})...")
    run_search(queries, args.candidates_out)

    candidates = load_lines(args.candidates_out)

    if not args.no_builtwith:
        print(f"\nSourcing additional candidates from BuiltWith for {args.platform}...")
        bw_urls = source_builtwith(args.platform)
        candidates.extend(bw_urls)

    print(f"\nSourcing additional candidates from known directories for {args.platform}...")
    dir_urls = source_directory(args.platform)
    candidates.extend(dir_urls)

    # dedupe by netloc across all three sources
    seen = set()
    deduped = []
    for u in candidates:
        netloc = urlparse(u).netloc.lower().replace("www.", "")
        if netloc not in seen:
            seen.add(netloc)
            deduped.append(u)
    candidates = deduped
    # Step 2: detect platform, keep only matches
    print(f"\nDetecting platform for {len(candidates)} candidates (filtering for {args.platform})...")
    matched = []
    for i, url in enumerate(candidates, 1):
        res = detect_platform(url)
        print(f"[{i}/{len(candidates)}] {res['url']} -> {res['platform']}")
        if res["platform"] == args.platform:
            matched.append(res["url"])

    print(f"\n{len(matched)} confirmed {args.platform} stores.")

    # Step 3: score new vs established
    print("\nScoring domain age...")
    scored = []
    for i, url in enumerate(matched, 1):
        res = score_domain(url)
        print(f"[{i}/{len(matched)}] {res['url']} -> {res['classification']}")
        scored.append(res)

    # Step 4: extract contact details for each lead
    print("\nExtracting contact details...")
    for i, res in enumerate(scored, 1):
        contact = get_contacts(res["url"])
        res["emails"] = contact["emails"]
        res["phones"] = contact["phones"]
        res["instagram"] = contact["instagram"]
        res["facebook"] = contact["facebook"]
        res["tiktok"] = contact["tiktok"]
        print(f"[{i}/{len(scored)}] {res['url']} -> emails: {contact['emails'] or 'none'}")

    # Step 5: write final leads, NEW first
    scored.sort(key=lambda r: r["new_score"], reverse=True)
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fieldnames = [
        "url", "domain_age_days", "wayback_age_days", "ssl_age_days",
        "wix_badge", "new_score", "classification",
        "emails", "phones", "instagram", "facebook", "tiktok",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored)

    new_count = sum(1 for r in scored if r["classification"] == "NEW")
    print(f"\nDone. {len(scored)} leads written to {out_path} ({new_count} NEW, {len(scored) - new_count} ESTABLISHED)")


if __name__ == "__main__":
    main()
