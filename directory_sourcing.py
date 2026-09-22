"""
directory_sourcing.py

Some platforms have real, free, no-login pages that list actual live store
domains — separate from search engines and separate from BuiltWith:
  - Shopify theme sellers publish "shops using our theme" showcase pages
  - Third-party sites publish theme-example lists with real domains

This is a curated list of known-good directory URLs per platform. Add more
URLs to PLATFORM_DIRECTORIES as you find them — the extraction logic is
generic (same domain-matching approach as builtwith_sourcing.py).

Usage:
    python directory_sourcing.py --platform Shopify --out candidates_dir.txt
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

# Known free, no-login pages listing real store domains, per platform.
# Shopify has the most of these because its theme-seller ecosystem publishes
# customer showcases; other platforms don't have an equivalent yet found —
# add URLs here as you discover more (WooCommerce/PrestaShop theme sellers
# sometimes publish similar showcase pages).
PLATFORM_DIRECTORIES = {
    "Shopify": [
        "https://zikanalytics.com/store-list/shopify-dawn-theme-examples",
        "https://zikanalytics.com/store-list/shopify-debut-theme-examples",
        "https://zikanalytics.com/store-list/shopify-brooklyn-theme-examples",
        "https://zikanalytics.com/store-list/shopify-minimal-theme-examples",
        "https://zikanalytics.com/store-list/shopify-venture-theme-examples",
        "https://zikanalytics.com/store-list/shopify-narrative-theme-examples",
        "https://help.outofthesandbox.com/hc/en-us/articles/115006909187",  # Responsive theme
        "https://help.outofthesandbox.com/hc/en-us/articles/115007100808",  # Parallax theme
    ],
    "Wix": [
        "https://winningwp.com/examples-of-websites-using-wix/",
        "https://htmlburger.com/blog/wix-website-examples/",
    ],
    "WooCommerce": [
        "https://nestify.io/blog/10-inspiring-woocommerce-websites/",
        "https://www.hostinger.com/tutorials/woocommerce-website-examples",
        "https://htmlburger.com/blog/woocommerce-stores/",
        "https://reallygooddesigns.com/stunning-woocommerce-stores/",
        "https://ecommerceguide.com/best-woocommerce-store-examples/",
    ],
    "WordPress": [
        "https://reallygooddesigns.com/best-small-business-ecommerce-website-examples/",
    ],
    "PrestaShop": [
        "https://belvg.com/blog/11-best-prestashop-websites-by-industry.html",
    ],
    "BigCommerce": [
        "https://colorlib.com/wp/bigcommerce-websites/",
        "https://www.howtostartanllc.com/how-to-build-a-website/bigcommerce-website-examples",
    ],
}

DOMAIN_RE = re.compile(
    r"\b((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24})\b",
    re.IGNORECASE,
)

JUNK_DOMAINS = (
    "shopify.com", "zikanalytics.com", "outofthesandbox.com", "wix.com",
    "woocommerce.com", "wordpress.com", "wordpress.org", "prestashop.com",
    "bigcommerce.com", "google.com", "facebook.com", "twitter.com",
    "instagram.com", "youtube.com", "amazonaws.com", "zendesk.com",
    "winningwp.com", "htmlburger.com", "nestify.io", "hostinger.com",
    "reallygooddesigns.com", "ecommerceguide.com", "belvg.com",
    "colorlib.com", "howtostartanllc.com", "linkedin.com", "pinterest.com",
    "tiktok.com", "wp.com", "gravatar.com", "w.org",
)


def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text
        print(f"  [diag] {url} -> status={resp.status_code}")
    except requests.RequestException as e:
        print(f"  [error] {url} -> {e}")
    return None


def extract_domains(html: str):
    domains = set()
    for match in DOMAIN_RE.finditer(html):
        domain = match.group(1).lower()
        if any(j in domain for j in JUNK_DOMAINS):
            continue
        if domain.count(".") == 0:
            continue
        domains.add(domain)
    return domains


def source_platform(platform: str, max_results: int = 100):
    urls_to_check = PLATFORM_DIRECTORIES.get(platform, [])
    if not urls_to_check:
        print(f"No known directory pages for {platform} yet.")
        return []

    all_domains = set()
    for page_url in urls_to_check:
        print(f"Fetching {page_url} ...")
        html = fetch(page_url)
        if html:
            found = extract_domains(html)
            print(f"  -> {len(found)} domains found")
            all_domains |= found

    urls = [f"https://{d}" for d in sorted(all_domains)][:max_results]
    return urls


def run(platform: str, out_path: str, max_results: int = 100):
    urls = source_platform(platform, max_results)
    with open(out_path, "w", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")
    print(f"\nDone. {len(urls)} unique candidate URLs written to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Source candidate URLs from known platform showcase directories.")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--out", default="candidates_directory.txt")
    parser.add_argument("--max-results", type=int, default=100)
    args = parser.parse_args()
    run(args.platform, args.out, args.max_results)


if __name__ == "__main__":
    main()
