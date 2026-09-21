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
import requests
from urllib.parse import urlparse, parse_qs, unquote

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
SEARCH_URL = "https://html.duckduckgo.com/html/"
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
        print(f"  -> {len(results)} results")
        all_urls.extend(results)
        time.sleep(delay)

    all_urls = dedupe(all_urls)

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
