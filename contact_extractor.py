"""
contact_extractor.py

Given a store URL, tries to pull contact details for outreach:
  - email address(es)
  - phone number(s)
  - social links (Instagram, Facebook, TikTok)
  - a likely "contact" or "about" page URL if found

All free — just regex over the homepage + common contact page paths.

Usage:
    python contact_extractor.py https://example.com
    python contact_extractor.py --file leads.csv --out output/leads_with_contacts.csv
"""

import re
import csv
import time
import argparse
import os
import requests
from urllib.parse import urljoin, urlparse

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 10

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")

SOCIAL_PATTERNS = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+"),
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9_.]+"),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+"),
}

# Common contact/about page paths worth checking if homepage has nothing.
CONTACT_PATHS = ["/contact", "/contact-us", "/pages/contact", "/about", "/about-us"]

# Junk matches to strip out (image filenames, tracking pixels, etc. that look like emails)
EMAIL_BLOCKLIST_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def clean_emails(raw_emails):
    cleaned = set()
    for e in raw_emails:
        e_lower = e.lower()
        if e_lower.endswith(EMAIL_BLOCKLIST_SUFFIXES):
            continue
        if "sentry.io" in e_lower or "wix.com" in e_lower or "example.com" in e_lower:
            continue
        cleaned.add(e_lower)
    return cleaned


def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def extract_from_html(html):
    emails = clean_emails(EMAIL_RE.findall(html))
    socials = {}
    for name, pattern in SOCIAL_PATTERNS.items():
        match = pattern.search(html)
        if match:
            socials[name] = match.group(0)
    phones = set(
        m.group(0).strip() for m in PHONE_RE.finditer(html)
        if len(re.sub(r"\D", "", m.group(0))) >= 7
    )
    return emails, phones, socials


def get_contacts(url: str) -> dict:
    result = {
        "url": url,
        "emails": "",
        "phones": "",
        "instagram": "",
        "facebook": "",
        "tiktok": "",
        "contact_page_found": "",
    }

    all_emails = set()
    all_phones = set()
    all_socials = {}
    found_contact_page = ""

    home_html = fetch(url)
    if home_html:
        emails, phones, socials = extract_from_html(home_html)
        all_emails |= emails
        all_phones |= phones
        all_socials.update(socials)

    # If nothing useful yet, try common contact/about paths.
    if not all_emails:
        for path in CONTACT_PATHS:
            page_url = urljoin(url + "/", path.lstrip("/"))
            html = fetch(page_url)
            if html:
                emails, phones, socials = extract_from_html(html)
                if emails or phones or socials:
                    found_contact_page = page_url
                all_emails |= emails
                all_phones |= phones
                all_socials.update(socials)
            if all_emails:
                break

    result["emails"] = "; ".join(sorted(all_emails))
    result["phones"] = "; ".join(sorted(all_phones))
    result["instagram"] = all_socials.get("instagram", "")
    result["facebook"] = all_socials.get("facebook", "")
    result["tiktok"] = all_socials.get("tiktok", "")
    result["contact_page_found"] = found_contact_page
    return result


def run(urls, out_path, delay=1.5):
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fieldnames = ["url", "emails", "phones", "instagram", "facebook", "tiktok", "contact_page_found"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, u in enumerate(urls, 1):
            res = get_contacts(u)
            writer.writerow(res)
            f.flush()
            tag = "OK" if res["emails"] or res["instagram"] or res["facebook"] else "no contact found"
            print(f"[{i}/{len(urls)}] {u} -> {tag}")
            time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Extract contact details from store URLs.")
    parser.add_argument("url", nargs="?", help="Single URL to check")
    parser.add_argument("--file", help="CSV with a 'url' column (e.g. output/leads.csv)")
    parser.add_argument("--out", default="output/leads_with_contacts.csv")
    parser.add_argument("--delay", type=float, default=1.5)
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            urls = [row["url"] for row in reader if row.get("url")]
        run(urls, args.out, args.delay)
        print(f"\nDone. Results written to {args.out}")
    elif args.url:
        print(get_contacts(args.url))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
