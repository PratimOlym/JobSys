"""Web scraper for extracting job listings from configured URLs.

Supports generic HTML scraping with configurable selectors.
Each job source URL can have an associated scraping configuration
stored in the config table; otherwise, a best-effort generic approach is used.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Default request headers to avoid blocks
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REQUEST_TIMEOUT = 30  # seconds


@dataclass
class ScrapedJob:
    """Raw job data extracted from a web page."""
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    date_posted: str = ""
    description: str = ""
    source_page: str = ""


def scrape_job_listings(source_url: str, scrape_config: Optional[dict] = None) -> List[ScrapedJob]:
    """Scrape job listings from a single source URL.

    Args:
        source_url: The URL to scrape.
        scrape_config: Optional dict with CSS selectors for parsing, e.g.:
            {
                "listing_selector": ".job-card",
                "title_selector": ".job-title",
                "company_selector": ".company-name",
                "location_selector": ".job-location",
                "date_selector": ".post-date",
                "link_selector": "a.job-link",
                "is_detail_page": false
            }

    Returns:
        List of ScrapedJob instances.
    """
    try:
        html = _fetch_page(source_url)
        if not html:
            return []

        if scrape_config and scrape_config.get("is_detail_page", False):
            # This URL is a single job detail page — extract it directly
            return [_scrape_single_job(source_url, html, scrape_config)]

        if scrape_config:
            return _scrape_with_config(source_url, html, scrape_config)

        return _scrape_generic(source_url, html)

    except Exception as e:
        logger.error(f"Failed to scrape {source_url}: {e}")
        return []


def scrape_single_job_page(job_url: str) -> ScrapedJob:
    """Scrape details from a single job detail page.

    Used when we have a direct link to a job posting.
    """
    try:
        html = _fetch_page(job_url)
        if not html:
            return ScrapedJob(url=job_url)

        soup = BeautifulSoup(html, "html.parser")

        # Try to extract the full page text as the description
        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = ""
        # Try common title patterns
        title_tag = soup.find("h1")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Get the main content area
        main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"job|posting|content|description", re.I))
        description = main.get_text(separator="\n", strip=True) if main else soup.body.get_text(separator="\n", strip=True) if soup.body else ""

        # Try to extract company, location from meta tags or structured data
        company = _extract_meta(soup, ["company", "employer", "og:site_name"])
        location = _extract_meta(soup, ["location", "geo.placename"])

        return ScrapedJob(
            url=job_url,
            title=title,
            company=company,
            location=location,
            description=description[:10000],  # Cap description length
            source_page=job_url,
        )
    except Exception as e:
        logger.error(f"Failed to scrape job page {job_url}: {e}")
        return ScrapedJob(url=job_url)


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _fetch_page(url: str) -> Optional[str]:
    """Fetch HTML content from a URL."""
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"HTTP request failed for {url}: {e}")
        return None


def _scrape_with_config(source_url: str, html: str, cfg: dict) -> List[ScrapedJob]:
    """Scrape using explicit CSS selectors from configuration."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    listing_sel = cfg.get("listing_selector", ".job-card")
    cards = soup.select(listing_sel)

    for card in cards:
        title = _select_text(card, cfg.get("title_selector", "h2"))
        company = _select_text(card, cfg.get("company_selector", ".company"))
        location = _select_text(card, cfg.get("location_selector", ".location"))
        date_posted = _select_text(card, cfg.get("date_selector", ".date"))

        # Extract link
        link_sel = cfg.get("link_selector", "a")
        link_tag = card.select_one(link_sel)
        job_url = ""
        if link_tag and link_tag.get("href"):
            job_url = _resolve_url(source_url, link_tag["href"])

        if job_url or title:
            jobs.append(ScrapedJob(
                url=job_url or source_url,
                title=title,
                company=company,
                location=location,
                date_posted=date_posted,
                source_page=source_url,
            ))

    logger.info(f"Scraped {len(jobs)} jobs from {source_url} (with config)")
    return jobs


def _scrape_generic(source_url: str, html: str) -> List[ScrapedJob]:
    """Best-effort generic scraping when no config is provided.

    Looks for common job listing patterns in the HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # Try common job card selectors
    selectors = [
        "[class*='job']", "[class*='posting']", "[class*='vacancy']",
        "[class*='position']", "[class*='opening']", "[data-job]",
        "article", ".card", "li",
    ]

    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if len(cards) >= 2:  # Found multiple items — likely a listing
            break

    if not cards:
        # Fallback: treat the entire page as a single job
        return [_scrape_single_job(source_url, html, {})]

    for card in cards[:50]:  # Cap at 50 jobs per page
        # Find the first link as the job URL
        link = card.find("a", href=True)
        job_url = _resolve_url(source_url, link["href"]) if link else ""

        # Find title (first heading or link text)
        heading = card.find(["h1", "h2", "h3", "h4"])
        title = heading.get_text(strip=True) if heading else (link.get_text(strip=True) if link else "")

        if not title or len(title) < 3:
            continue

        # Try to find company and location
        text_parts = card.get_text(separator=" | ", strip=True).split(" | ")
        company = text_parts[1] if len(text_parts) > 1 else ""
        location = text_parts[2] if len(text_parts) > 2 else ""

        jobs.append(ScrapedJob(
            url=job_url or source_url,
            title=title[:200],
            company=company[:200],
            location=location[:200],
            source_page=source_url,
        ))

    logger.info(f"Scraped {len(jobs)} jobs from {source_url} (generic)")
    return jobs


def _scrape_single_job(url: str, html: str, cfg: dict) -> ScrapedJob:
    """Extract a single job from an HTML page (detail page)."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    title_sel = cfg.get("title_selector") if cfg else None
    if title_sel:
        title = _select_text(soup, title_sel)
    else:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

    main = soup.find("main") or soup.find("article") or soup.body
    description = main.get_text(separator="\n", strip=True) if main else ""

    return ScrapedJob(
        url=url,
        title=title,
        description=description[:10000],
        source_page=url,
    )


def _select_text(element, selector: str) -> str:
    """Select an element and return its text, or empty string."""
    try:
        tag = element.select_one(selector)
        return tag.get_text(strip=True) if tag else ""
    except Exception:
        return ""


def _resolve_url(base_url: str, href: str) -> str:
    """Resolve a relative URL against a base URL."""
    if href.startswith("http"):
        return href
    parsed = urlparse(base_url)
    if href.startswith("/"):
        return f"{parsed.scheme}://{parsed.netloc}{href}"
    return f"{base_url.rstrip('/')}/{href.lstrip('/')}"


def _extract_meta(soup: BeautifulSoup, names: list) -> str:
    """Try to extract content from meta tags by name patterns."""
    for name in names:
        tag = soup.find("meta", attrs={"name": re.compile(name, re.I)})
        if tag and tag.get("content"):
            return tag["content"]
        tag = soup.find("meta", attrs={"property": re.compile(name, re.I)})
        if tag and tag.get("content"):
            return tag["content"]
    return ""
