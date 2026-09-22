"""
search_sourcing.py

Queries DuckDuckGo's HTML endpoint (no API key needed) to find candidate
store URLs for a list of search queries, and writes them to a file for
detector.py to process.

Usage:
    python search_sourcing.py --queries queries.txt --out candidates.txt
    python search_sourcing.py --query '"powered by wix" jewelry' --out candidates.txt
"""

import re
import time
import argparse
import os
import requests
from urllib.parse import urlparse, parse_qs, unquote

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
SEARCH_URL = "https://html.duckduckgo.com/html/"
BING_SEARCH_URL = "https://www.bing.com/search"
TIMEOUT = 10

# Skip results from these — not candidate stores, just noise.
DOMAIN_BLOCKLIST = (
    "duckduckgo.com", "wix.com", "wixsite.com/support", "youtube.com",
    "facebook.com", "instagram.com", "pinterest.com", "wikipedia.org",
    "reddit.com", "linkedin.com", "twitter.com", "x.com", "builtwith.com",
)


def extract_real_url(href: str) -> str:
    """DuckDuckGo HTML results wrap links in a redirect; unwrap them."""
    if href.startswith("//duckduckgo.com/l/"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and "uddg" in parse_qs(parsed.query):
        return unquote(parse_qs(parsed.query)["uddg"][0])
    return href


def is_blocked(url: str) -> bool:
    netloc = urlparse(url).netloc.lower()
    return any(b in netloc for b in DOMAIN_BLOCKLIST)


def search_bing(query: str, max_results: int = 30):
    """Fallback search engine — tried when DuckDuckGo returns nothing."""
    urls = []
    try:
        resp = requests.get(
            BING_SEARCH_URL,
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        print(f"  [bing error] query failed: {e}")
        return urls

    # Bing result links appear as <a href="..."> inside <h2> tags in organic results.
    hrefs = re.findall(r'<h2><a[^>]+href="([^"]+)"', resp.text)
    if not hrefs:
        print(f"  [bing diag] status={resp.status_code} body_len={len(resp.text)}")

    for href in hrefs:
        if href.startswith("http") and not is_blocked(href) and "bing.com" not in href:
            urls.append(href)
        if len(urls) >= max_results:
            break

    return urls


def search_duckduckgo(query: str, max_results: int = 30):
    """Returns a list of candidate URLs for one query."""
    urls = []
    try:
        resp = requests.post(
            SEARCH_URL,
            data={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        print(f"  [error] query failed: {e}")
        return urls

    # Result links carry class="result__a"
    hrefs = re.findall(r'class="result__a"[^>]*href="([^"]+)"', resp.text)

    if not hrefs:
        # Nothing matched — likely blocked/rate-limited rather than "no results".
        # Print diagnostics so it's obvious which case we're in.
        print(f"  [diag] status={resp.status_code} body_len={len(resp.text)}")
        lowered = resp.text.lower()
        if "anomaly" in lowered or "unusual traffic" in lowered or resp.status_code in (403, 429, 202):
            print("  [diag] response looks like a block/rate-limit page, not a real 'no results' page")
        elif len(resp.text) < 2000:
            print(f"  [diag] short response body, first 300 chars: {resp.text[:300]!r}")

    for href in hrefs:
        real_url = extract_real_url(href)
        if real_url and not is_blocked(real_url):
            urls.append(real_url)
        if len(urls) >= max_results:
            break

    return urls


def dedupe(urls):
    seen = set()
    out = []
    for u in urls:
        netloc = urlparse(u).netloc.lower().replace("www.", "")
        if netloc not in seen:
            seen.add(netloc)
            out.append(u)
    return out


def run(queries, out_path, delay=2.0, max_per_query=30):
    all_urls = []
    for i, q in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] searching: {q}")
        results = search_duckduckgo(q, max_per_query)
        if not results:
            print("  -> 0 results from DuckDuckGo, trying Bing...")
            time.sleep(1)
            results = search_bing(q, max_per_query)
        print(f"  -> {len(results)} results")
        all_urls.extend(results)
        time.sleep(delay)

    all_urls = dedupe(all_urls)

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for u in all_urls:
            f.write(u + "\n")

    print(f"\nDone. {len(all_urls)} unique candidate URLs written to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Source candidate store URLs via DuckDuckGo search.")
    parser.add_argument("--query", help="A single search query")
    parser.add_argument("--queries", help="Path to a text file of queries, one per line")
    parser.add_argument("--out", default="candidates.txt", help="Output file for candidate URLs")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between search requests")
    parser.add_argument("--max-per-query", type=int, default=30, help="Max results to keep per query")
    args = parser.parse_args()

    if args.queries:
        with open(args.queries, encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]
    elif args.query:
        queries = [args.query]
    else:
        parser.print_help()
        return

    run(queries, args.out, args.delay, args.max_per_query)


if __name__ == "__main__":
    main()
