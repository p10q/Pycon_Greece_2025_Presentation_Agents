"""Clean date extraction and filtering utilities for web search results."""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any

import httpx
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse

from . import get_logger

logger = get_logger(__name__)


class DateExtractor:
    """Clean, efficient date extraction from web pages and URLs."""

    # Common meta tag selectors for publication dates
    META_DATE_SELECTORS = [
        'meta[property="article:published_time"]',
        'meta[property="article:modified_time"]',
        'meta[name="date"]',
        'meta[name="publish-date"]',
        'meta[name="publication-date"]',
        'meta[name="pubdate"]',
        'meta[name="DC.date"]',
        'meta[name="DC.Date"]',
        'meta[name="dcterms.created"]',
        'meta[name="dcterms.modified"]',
        'meta[property="og:updated_time"]',
        'meta[name="last-modified"]',
        "time[datetime]",
        "time[pubdate]",
    ]

    # URL date patterns (YYYY/MM/DD, YYYY-MM-DD, etc.)
    URL_DATE_PATTERNS = [
        r"/(\d{4})/(\d{1,2})/(\d{1,2})/",
        r"/(\d{4})-(\d{1,2})-(\d{1,2})/",
        r"/(\d{4})(\d{2})(\d{2})/",
        r"_(\d{4})(\d{2})(\d{2})_",
        r"-(\d{4})(\d{2})(\d{2})-",
    ]

    def __init__(self, max_age_months: int = 2, timeout_seconds: int = 5):
        """Initialize date extractor.

        Args:
            max_age_months: Maximum age in months for content (default: 2)
            timeout_seconds: HTTP request timeout (default: 5)

        """
        self.max_age_months = max_age_months
        self.timeout = timeout_seconds
        self.cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)

        # HTTP client for fetching pages
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TechTracker/1.0; +https://github.com/your-repo)",
            },
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    def extract_date_from_url(self, url: str) -> datetime | None:
        """Extract date from URL patterns.

        Args:
            url: The URL to extract date from

        Returns:
            Extracted datetime or None

        """
        if not url:
            return None

        for pattern in self.URL_DATE_PATTERNS:
            match = re.search(pattern, url)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                        date = datetime(int(year), int(month), int(day))

                        # Validate date is reasonable (not too far in future/past)
                        now = datetime.now()
                        if (
                            (now - timedelta(days=365 * 3))
                            <= date
                            <= (now + timedelta(days=365))
                        ):
                            return date
                except (ValueError, TypeError):
                    continue

        return None

    async def extract_date_from_meta_tags(self, url: str) -> datetime | None:
        """Extract publication date from page meta tags.

        Args:
            url: URL to fetch and parse

        Returns:
            Extracted datetime or None

        """
        if not url or not url.startswith(("http://", "https://")):
            return None

        try:
            # Fetch page content
            response = await self.client.get(url)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, "lxml")

            # Try each meta tag selector
            for selector in self.META_DATE_SELECTORS:
                elements = soup.select(selector)
                for element in elements:
                    date_str = None

                    # Extract date string from different attributes
                    if element.get("content"):
                        date_str = element.get("content")
                    elif element.get("datetime"):
                        date_str = element.get("datetime")
                    elif element.text:
                        date_str = element.text.strip()

                    if date_str:
                        parsed_date = self._parse_date_string(date_str)
                        if parsed_date:
                            return parsed_date

            return None

        except Exception as e:
            logger.debug(f"Failed to extract meta date from {url}: {e}")
            return None

    def _parse_date_string(self, date_str: str) -> datetime | None:
        """Parse various date string formats.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime or None

        """
        if not date_str:
            return None

        # Clean the date string
        date_str = date_str.strip().replace("T", " ").replace("Z", "")

        try:
            # Use dateutil parser for flexible parsing
            parsed_date = date_parse(date_str, fuzzy=True)

            # Validate date is reasonable
            now = datetime.now()
            if (
                (now - timedelta(days=365 * 5))
                <= parsed_date
                <= (now + timedelta(days=365))
            ):
                return parsed_date

        except (ValueError, TypeError, OverflowError):
            pass

        return None

    async def extract_and_validate_date(
        self,
        item: dict[str, Any],
    ) -> datetime | None:
        """Extract and validate publication date from search result item.

        Args:
            item: Search result item with url, title, etc.

        Returns:
            Valid datetime within age limit or None

        """
        url = item.get("url", "")

        # 1. Try API-provided dates first
        for field in ["published", "age", "publication_date"]:
            if item.get(field):
                parsed_date = self._parse_date_string(item[field])
                if parsed_date and self._is_date_valid(parsed_date):
                    return parsed_date

        # 2. Try URL pattern extraction
        url_date = self.extract_date_from_url(url)
        if url_date and self._is_date_valid(url_date):
            return url_date

        # 3. Try meta tags (more expensive, so last)
        meta_date = await self.extract_date_from_meta_tags(url)
        if meta_date and self._is_date_valid(meta_date):
            return meta_date

        return None

    def _is_date_valid(self, date: datetime) -> bool:
        """Check if date is within acceptable age limit.

        Args:
            date: Date to validate

        Returns:
            True if date is recent enough

        """
        return date >= self.cutoff_date

    async def filter_recent_results(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Filter search results to only include recent content.

        Args:
            results: List of search result items

        Returns:
            Filtered list with only recent results

        """
        if not results:
            return results

        filtered_results = []

        # Process results concurrently for better performance
        tasks = []
        for item in results:
            tasks.append(self._process_result_item(item))

        # Wait for all date extractions to complete
        processed_items = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        for item in processed_items:
            if item is not None and not isinstance(item, Exception):
                filtered_results.append(item)

        logger.info(
            f"Filtered {len(results)} results to {len(filtered_results)} recent items (max age: {self.max_age_months} months)",
        )
        return filtered_results

    async def _process_result_item(
        self,
        item: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Process individual result item for date extraction and validation.

        Args:
            item: Search result item

        Returns:
            Item with updated timestamp if valid, None if too old

        """
        try:
            # Extract publication date
            pub_date = await self.extract_and_validate_date(item)

            if pub_date:
                # Update item with extracted date
                updated_item = item.copy()
                updated_item["timestamp"] = pub_date.isoformat()
                updated_item["_date_source"] = "extracted"  # For debugging
                return updated_item
            # No valid date found or too old
            logger.debug(
                f"Filtered out result (too old or no date): {item.get('title', 'Unknown')[:50]}",
            )
            return None

        except Exception as e:
            logger.warning(f"Error processing result item: {e}")
            return None


# Convenience function for easy usage
async def filter_and_extract_dates(
    results: list[dict[str, Any]],
    max_age_months: int = 2,
) -> list[dict[str, Any]]:
    """Convenience function to filter results by date.

    Args:
        results: Search results to filter
        max_age_months: Maximum age in months

    Returns:
        Filtered results with extracted dates

    """
    print(
        f"DEBUG: filter_and_extract_dates called with {len(results)} results, max_age={max_age_months} months",
    )
    async with DateExtractor(max_age_months=max_age_months) as extractor:
        filtered = await extractor.filter_recent_results(results)
        print(f"DEBUG: filter_and_extract_dates returning {len(filtered)} results")
        return filtered
