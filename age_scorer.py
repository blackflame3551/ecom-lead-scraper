"""
age_scorer.py

Scores a domain as NEW or ESTABLISHED using free signals:
  - Domain registration age (WHOIS)
  - Wayback Machine earliest snapshot
  - SSL certificate issue date
  - "Powered by Wix" badge presence (passed in from detector step)

Usage:
    python age_scorer.py --file results.csv --out scored.csv
"""

import ssl
import socket
import argparse
import csv
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

try:
    import whois  # python-whois
except ImportError:
    whois = None

TIMEOUT = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}


def get_domain(url: str) -> str:
    netloc = urlparse(url).netloc
    return netloc.replace("www.", "")


def whois_age_days(domain: str):
    """Returns days since domain registration, or None if unavailable."""
    if whois is None:
        return None
    try:
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if created is None:
            return None
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - created
        return delta.days
    except Exception:
        return None


def wayback_earliest_days(domain: str):
    """Returns days since earliest Wayback Machine snapshot, or None if no snapshot."""
    try:
        resp = requests.get(
            "https://archive.org/wayback/available",
            params={"url": domain},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        data = resp.json()
        snapshot = data.get("archived_snapshots", {}).get("closest")
        if not snapshot:
            return None
        ts = snapshot.get("timestamp")  # format YYYYMMDDhhmmss
        snap_date = datetime.strptime(ts[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - snap_date
        return delta.days
    except Exception:
        return None


def ssl_cert_age_days(domain: str):
    """Returns days since SSL cert issue date, or None if unavailable."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        not_before = cert.get("notBefore")
        if not not_before:
            return None
        issued = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - issued
        return delta.days
    except Exception:
        return None


def has_wix_badge(url: str) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return "Powered by Wix" in resp.text or "wix.com/website/free" in resp.text.lower()
    except Exception:
        return False


def score_domain(url: str) -> dict:
    domain = get_domain(url)
    result = {
        "url": url,
        "domain_age_days": None,
        "wayback_age_days": None,
        "ssl_age_days": None,
        "wix_badge": None,
        "new_score": 0,
        "classification": "UNKNOWN",
    }

    domain_age = whois_age_days(domain)
    wayback_age = wayback_earliest_days(domain)
    ssl_age = ssl_cert_age_days(domain)
    badge = has_wix_badge(url)

    result["domain_age_days"] = domain_age
    result["wayback_age_days"] = wayback_age
    result["ssl_age_days"] = ssl_age
    result["wix_badge"] = badge

    score = 0
    if domain_age is not None and domain_age < 365:
        score += 2
    if wayback_age is None or wayback_age < 180:
        score += 2
    if ssl_age is not None and ssl_age < 180:
        score += 1
    if badge:
        score += 1

    result["new_score"] = score
    result["classification"] = "NEW" if score >= 3 else "ESTABLISHED"
    return result


def run(urls, out_path, delay=1.0):
    fieldnames = [
        "url", "domain_age_days", "wayback_age_days", "ssl_age_days",
        "wix_badge", "new_score", "classification",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, u in enumerate(urls, 1):
            res = score_domain(u)
            writer.writerow(res)
            f.flush()
            print(f"[{i}/{len(urls)}] {res['url']} -> {res['classification']} (score {res['new_score']})")
            time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Score domains as NEW or ESTABLISHED.")
    parser.add_argument("--urls", help="Path to a text file of URLs, one per line")
    parser.add_argument("--file", help="Path to detector.py's output CSV (uses the 'url' column)")
    parser.add_argument("--out", default="output/scored.csv", help="Output CSV path")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between checks")
    args = parser.parse_args()

    urls = []
    if args.urls:
        with open(args.urls, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    elif args.file:
        with open(args.file, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            urls = [row["url"] for row in reader if row.get("url")]
    else:
        parser.print_help()
        return

    run(urls, args.out, args.delay)
    print(f"\nDone. Results written to {args.out}")


if __name__ == "__main__":
    main()
