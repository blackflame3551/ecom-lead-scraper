"""
builtwith_sourcing.py

BuiltWith publishes free, no-login sample pages listing real domains using
a given technology, e.g.:
    https://trends.builtwith.com/websitelist/Shopify/United-States
    https://trends.builtwith.com/websitelist/Wix/United-States

These pages show a genuine sample of live domains for free, then cut off
further entries (shown truncated with "...") to push you toward a paid
account. This script pulls only the fully-visible, untruncated domains.

It's a small, free, no-key source of leads — a supplement to search engine
sourcing, not a replacement (the free sample is capped at roughly 20-40
domains per platform per country).

Usage:
    python builtwith_sourcing.py --platform Shopify --out candidates_bw.txt
    python builtwith_sourcing.py --platform Wix --country United-States --out candidates_bw.txt
"""

import re
import argparse
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 15

# BuiltWith's slug for each platform on trends.builtwith.com/websitelist/<slug>
PLATFORM_SLUGS = {
    "Wix": "Wix",
    "Shopify": "Shopify",
    "WooCommerce": "WooCommerce",
    "WordPress": "WordPress",
    "PrestaShop": "PrestaShop",
    "BigCommerce": "BigCommerce",
}

# Domain-looking token: letters/digits/hyphens, dot, a real-ish TLD (2-24 chars, no digits in TLD)
DOMAIN_RE = re.compile(
    r"\b((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24})\b",
    re.IGNORECASE,
)

# Skip these — BuiltWith's own domains, common junk, not real leads
JUNK_DOMAINS = (
    "builtwith.com", "wix.com", "shopify.com", "woocommerce.com",
    "wordpress.com", "wordpress.org", "prestashop.com", "bigcommerce.com",
    "example.com", "google.com", "facebook.com",
)


def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text
        print(f"  [diag] status={resp.status_code}")
    except requests.RequestException as e:
        print(f"  [error] {e}")
    return None


def extract_domains(html: str):
    """Pull full (non-truncated) domain names from the page text."""
    domains = set()
    for match in DOMAIN_RE.finditer(html):
        domain = match.group(1).lower()
        # Skip anything immediately followed by "..." in the source (truncated preview rows)
        end = match.end()
        if html[end:end + 3] == "...":
            continue
        if any(j in domain for j in JUNK_DOMAINS):
            continue
        if domain.count(".") == 0:
            continue
        domains.add(domain)
    return domains


def source_platform(platform: str, country: str = "United-States", max_results: int = 50):
    slug = PLATFORM_SLUGS.get(platform)
    if not slug:
        print(f"Unknown platform '{platform}'. Choose from: {list(PLATFORM_SLUGS)}")
        return []

    url = f"https://trends.builtwith.com/websitelist/{slug}/{country}"
    print(f"Fetching {url} ...")
    html = fetch(url)
    if not html:
        return []

    domains = extract_domains(html)
    urls = [f"https://{d}" for d in sorted(domains)][:max_results]
    print(f"  -> {len(urls)} usable (non-truncated) domains found")
    return urls


def run(platforms, out_path, country="United-States", max_results=50):
    all_urls = []
    for platform in platforms:
        urls = source_platform(platform, country, max_results)
        all_urls.extend(urls)

    seen = set()
    deduped = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    with open(out_path, "w", encoding="utf-8") as f:
        for u in deduped:
            f.write(u + "\n")

    print(f"\nDone. {len(deduped)} unique candidate URLs written to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Source candidate store URLs from BuiltWith's free lists.")
    parser.add_argument("--platform", help="Single platform: Wix, Shopify, WooCommerce, WordPress, PrestaShop, BigCommerce")
    parser.add_argument("--all-platforms", action="store_true", help="Fetch all supported platforms")
    parser.add_argument("--country", default="United-States", help="Country slug as BuiltWith uses it, e.g. United-States")
    parser.add_argument("--out", default="candidates_builtwith.txt")
    parser.add_argument("--max-results", type=int, default=50)
    args = parser.parse_args()

    if args.all_platforms:
        platforms = list(PLATFORM_SLUGS.keys())
    elif args.platform:
        platforms = [args.platform]
    else:
        parser.print_help()
        return

    run(platforms, args.out, args.country, args.max_results)


if __name__ == "__main__":
    main()
