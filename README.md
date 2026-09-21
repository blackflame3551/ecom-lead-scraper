# E-commerce Platform Lead Scraper

Free, no-API-key lead generation. Sources candidate store URLs from search
engines, detects which platform they run on (Wix, Shopify, WooCommerce,
WordPress, PrestaShop, BigCommerce), and scores Wix stores as NEW or
ESTABLISHED so you can prioritize outreach.

## Setup

```bash
pip install -r requirements.txt
```

## Run the full pipeline (recommended)

```bash
python pipeline.py --queries queries.txt --out output/leads.csv
```

This will:
1. Search DuckDuckGo using the queries in `queries.txt`
2. Filter results down to confirmed Wix stores
3. Score each as NEW or ESTABLISHED (domain age, Wayback history, SSL cert age, "Powered by Wix" badge)
4. Write `output/leads.csv`, sorted NEW-first

Edit `queries.txt` to target different niches — one query per line.

## Run steps individually

```bash
# 1. Source candidate URLs
python search_sourcing.py --queries queries.txt --out candidates.txt

# 2. Check what platform any single URL runs
python detector.py https://example.com

# 2b. Or batch-detect platform for a whole file of URLs
python detector.py --file candidates.txt --out output/results.csv

# 3. Score domains as NEW vs ESTABLISHED
python age_scorer.py --file output/results.csv --out output/scored.csv
```

## Targeting a different platform

`pipeline.py --platform Shopify` (or WooCommerce / WordPress / PrestaShop / BigCommerce)
will filter for that platform instead of Wix. Age scoring logic still applies
the same way to any domain.

## Run automatically with GitHub Actions (free, no server needed)

1. Push this project to a GitHub repo.
2. The workflow at `.github/workflows/scrape.yml` is already set up — it runs daily at 06:00 UTC and can also be triggered manually from the **Actions** tab (`Run workflow` button).
3. After each run, go to the run's summary page and download the `leads-<run_id>` artifact — it contains `output/leads.csv`.
4. To change the schedule, edit the `cron` line in `scrape.yml` ([crontab.guru](https://crontab.guru) helps write the expression).
5. To change what it searches for, edit `queries.txt` and commit — the next run picks it up automatically.

GitHub Actions free tier gives 2,000 minutes/month on public repos (unlimited on public repos actually, 2,000 min/month on private) — a daily run of this pipeline uses only a few minutes, so you're nowhere near the limit.


- Respect rate limits — default delays are built in (`--delay` flag on each script). Don't strip them out; DuckDuckGo and target sites will block you.
- WHOIS lookups can be slow or rate-limited by registries — `age_scorer.py` handles failures gracefully (returns `None` for that signal rather than crashing).
- This detects Wix's presence via HTML fingerprints. Actually scraping *product data* from a Wix store (not just detecting it) requires a JS-rendering step (Playwright) since Wix loads products client-side — that's the next module to build.
