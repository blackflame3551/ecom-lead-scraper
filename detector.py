"""
detector.py

Given a URL, identifies which e-commerce/CMS platform it's running on:
Wix, Shopify, WooCommerce, WordPress, PrestaShop, BigCommerce.

Usage:
    python detector.py https://example.com
    python detector.py --file urls.txt --out results.csv
"""

import re
import csv
import sys
import time
import argparse
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 10


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def fetch(url: str):
    """Fetch a URL, return (response, error). Never raises."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return resp, None
    except requests.RequestException as e:
        return None, str(e)


def check_shopify(html: str, headers: dict, url: str) -> bool:
    if "cdn.shopify.com" in html or "Shopify.shop" in html:
        return True
    # confirm via products.json endpoint
    resp, err = fetch(url + "/products.json")
    if resp is not None and resp.status_code == 200:
        try:
            data = resp.json()
            if isinstance(data, dict) and "products" in data:
                return True
        except ValueError:
            pass
    return False


def check_woocommerce(html: str, url: str) -> bool:
    if re.search(r"woocommerce", html, re.IGNORECASE):
        return True
    resp, err = fetch(url + "/wp-json/wc/store/products")
    if resp is not None and resp.status_code == 200:
        return True
    return False


def check_wordpress(html: str, url: str) -> bool:
    if "wp-content" in html or "wp-json" in html:
        return True
    resp, err = fetch(url + "/wp-json/")
    if resp is not None and resp.status_code == 200 and "wp/v2" in resp.text:
        return True
    return False


def check_wix(html: str, headers: dict) -> bool:
    if "static.parastorage.com" in html or "wixBiSession" in html:
        return True
    if "Wix.com" in html and "generator" in html.lower():
        return True
    if headers and any("wix" in k.lower() or "wix" in str(v).lower() for k, v in headers.items()):
        return True
    return False


def check_prestashop(html: str) -> bool:
    if re.search(r"PrestaShop", html, re.IGNORECASE):
        return True
    if "prestashop" in html.lower():
        return True
    return False


def check_bigcommerce(html: str) -> bool:
    if "cdn11.bigcommerce.com" in html or "bigcommerce.com" in html.lower():
        return True
    return False


def detect_platform(url: str) -> dict:
    """
    Returns a dict: {url, platform, status, error}
    platform is one of: Shopify, WooCommerce, WordPress, Wix, PrestaShop,
    BigCommerce, Unknown
    """
    url = normalize_url(url)
    result = {"url": url, "platform": "Unknown", "status": None, "error": None}

    resp, err = fetch(url)
    if resp is None:
        result["error"] = err
        return result

    result["status"] = resp.status_code
    html = resp.text
    headers = dict(resp.headers)

    # Order matters: check most identifiable / cheapest signals first.
    if check_shopify(html, headers, url):
        result["platform"] = "Shopify"
    elif check_wix(html, headers):
        result["platform"] = "Wix"
    elif check_bigcommerce(html):
        result["platform"] = "BigCommerce"
    elif check_prestashop(html):
        result["platform"] = "PrestaShop"
    elif check_woocommerce(html, url):
        result["platform"] = "WooCommerce"
    elif check_wordpress(html, url):
        result["platform"] = "WordPress"

    return result


def run_batch(urls, out_path, delay=1.0):
    fieldnames = ["url", "platform", "status", "error"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, u in enumerate(urls, 1):
            res = detect_platform(u)
            writer.writerow(res)
            f.flush()
            print(f"[{i}/{len(urls)}] {res['url']} -> {res['platform']}")
            time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Detect e-commerce platform for a URL or list of URLs.")
    parser.add_argument("url", nargs="?", help="Single URL to check")
    parser.add_argument("--file", help="Path to a text file of URLs, one per line")
    parser.add_argument("--out", default="output/results.csv", help="CSV output path for batch mode")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        run_batch(urls, args.out, args.delay)
        print(f"\nDone. Results written to {args.out}")
    elif args.url:
        res = detect_platform(args.url)
        print(res)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
