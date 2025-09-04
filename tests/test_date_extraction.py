#!/usr/bin/env python3
"""Test the new date extraction system."""

import asyncio
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.utils.date_extractor import filter_and_extract_dates


async def test_date_extraction():
    """Test date extraction with sample data."""
    # Sample search results
    sample_results = [
        {
            "title": "Python asyncio Tutorial 2024",
            "url": "https://realpython.com/async-io-python/",
            "source": "brave_search",
            "timestamp": "2025-08-04T14:00:00",
        },
        {
            "title": "Old Python Tutorial from 2020",
            "url": "https://example.com/2020/01/15/old-tutorial/",
            "source": "brave_search",
            "timestamp": "2025-08-04T14:00:00",
        },
        {
            "title": "Recent Async Guide",
            "url": "https://medium.com/recent-guide",
            "source": "brave_search",
            "timestamp": "2025-08-04T14:00:00",
        },
    ]

    print("Testing date extraction system...")
    print(f"Original results: {len(sample_results)}")

    # Test the filtering
    filtered_results = await filter_and_extract_dates(sample_results, max_age_months=2)

    print(f"Filtered results: {len(filtered_results)}")

    for i, result in enumerate(filtered_results):
        print(f"Result {i+1}:")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  Date: {result['timestamp']}")
        print(f"  Source: {result.get('_date_source', 'unknown')}")
        print()


if __name__ == "__main__":
    asyncio.run(test_date_extraction())
