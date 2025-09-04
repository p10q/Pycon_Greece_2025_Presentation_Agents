#!/usr/bin/env python3
"""Simple test of date extraction without app dependencies."""

import asyncio
import re
from datetime import datetime, timedelta


def extract_date_from_url(url: str) -> datetime | None:
    """Simple URL date extraction test."""
    patterns = [
        r"/(\d{4})/(\d{1,2})/(\d{1,2})/",
        r"/(\d{4})-(\d{1,2})-(\d{1,2})/",
        r"/(\d{4})(\d{2})(\d{2})/",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                year, month, day = match.groups()
                date = datetime(int(year), int(month), int(day))

                # Check if within 2 months
                cutoff = datetime.now() - timedelta(days=60)
                if date >= cutoff:
                    return date
            except (ValueError, TypeError):
                continue

    return None


async def test_simple_extraction():
    """Test simple date extraction."""
    test_urls = [
        "https://example.com/2024/12/15/recent-post/",
        "https://example.com/2024/06/01/old-post/",  # Should be filtered out
        "https://example.com/2025/01/15/future-post/",
        "https://medium.com/no-date-in-url",
    ]

    print("Testing URL date extraction:")

    for url in test_urls:
        date = extract_date_from_url(url)
        if date:
            days_ago = (datetime.now() - date).days
            print(f"✅ {url[:50]}: {date.strftime('%Y-%m-%d')} ({days_ago} days ago)")
        else:
            print(f"❌ {url[:50]}: No date found or too old")


if __name__ == "__main__":
    asyncio.run(test_simple_extraction())
