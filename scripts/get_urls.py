#!/usr/bin/env python3
import argparse
import sys
import fnmatch
import requests
from datetime import datetime, timedelta, timezone
from lxml import etree


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sitemap-url", required=True)
    p.add_argument("--since", type=int, required=True)
    p.add_argument("--since-unit", choices=["minutes", "hours", "days"], required=True)
    p.add_argument("--exclude-urls", default="", help="Newline separated glob patterns")
    p.add_argument("--filter-urls", default="", help="Newline separated substrings")
    return p.parse_args()


def parse_since(since: int, unit: str) -> datetime:
    now = datetime.now(timezone.utc)
    delta_map = {"minutes": "minutes", "hours": "hours", "days": "days"}
    return now - timedelta(**{delta_map[unit]: since})


def fetch_sitemap(url: str):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def extract_urls(xml_bytes: bytes, since_ago: datetime):
    ns = {"x": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    tree = etree.fromstring(xml_bytes)
    for url_el in tree.xpath("//x:url", namespaces=ns):
        loc = url_el.find("x:loc", ns)
        lastmod = url_el.find("x:lastmod", ns)
        if loc is None or lastmod is None:
            continue
        url = loc.text.strip()
        try:
            lm = datetime.fromisoformat(lastmod.text.strip().replace("Z", "+00:00"))
        except Exception:
            continue
        if lm > since_ago:
            yield url


def should_exclude(url: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(url, pat):
            return True
    return False


def should_filter(url: str, filters: list[str]) -> bool:
    if not filters:
        return True
    return any(f in url for f in filters)


def main():
    args = parse_args()
    since_ago = parse_since(args.since, args.since - unit)
    xml = fetch_sitemap(args.sitemap_url)
    candidates = set(extract_urls(xml, since_ago))

    exclude_patterns = [p.strip() for p in args.exclude_urls.splitlines() if p.strip()]
    filter_patterns = [p.strip() for p in args.filter_urls.splitlines() if p.strip()]

    processed = []
    for url in sorted(candidates):
        if should_exclude(url, exclude_patterns):
            print(f"Excluding URL: {url}", file=sys.stderr)
            continue
        if not should_filter(url, filter_patterns):
            print(f"Skipping (no filter match): {url}", file=sys.stderr)
            continue
        print(f"Processing URL: {url}", file=sys.stderr)
        processed.append(url)

    # Output both lists for GitHub Actions
    print("latest-urls<<EOF")
    print("\n".join(sorted(candidates)))
    print("EOF")

    print("processed-urls<<EOF")
    print("\n".join(processed))
    print("EOF")


if __name__ == "__main__":
    main()
