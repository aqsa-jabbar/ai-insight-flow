"""
tools.py
--------
Defines the two "hands" of the agent:
  1. search_web      -> uses Serper (Google Search API) to find URLs when the
                         user gives a website NAME instead of a direct link.
  2. scrape_website   -> fetches and cleans the text content of a given URL.

Both are wrapped with LangChain's @tool decorator, which is what lets
langgraph's create_react_agent call them automatically during its
Thought -> Action -> Observation loop.
"""

import logging
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

import config

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool 1: Serper search
# ---------------------------------------------------------------------------

@tool
def search_web(query: str) -> str:
    """
    Search Google (via Serper) for a query and return the top results.

    Use this when the user gives a website NAME or a general topic
    (e.g. "Notion", "best project management tools") rather than a direct
    URL. It returns titles, links, and short snippets so you can decide
    which URL(s) to scrape next.

    Args:
        query: The search query, e.g. "Notion official website" or
               "Stripe pricing documentation".

    Returns:
        A formatted string of the top search results, or an error message
        if the search failed.
    """
    if not config.SERPER_API_KEY:
        return "Error: SERPER_API_KEY is not set. Cannot perform search."

    if not query or not query.strip():
        return "Error: search query was empty."

    headers = {
        "X-API-KEY": config.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query}

    try:
        response = requests.post(
            config.SERPER_URL,
            headers=headers,
            json=payload,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.warning("Serper request timed out for query: %s", query)
        return f"Error: search timed out for query '{query}'."
    except requests.exceptions.RequestException as e:
        logger.error("Serper request failed: %s", e)
        return f"Error: search request failed - {e}"

    organic_results = data.get("organic", [])
    if not organic_results:
        return f"No search results found for '{query}'."

    # Only take the top N - the agent doesn't need 50 links, and more
    # results just eats into the token budget for no benefit.
    formatted = []
    for i, result in enumerate(organic_results[: config.SERPER_MAX_RESULTS], start=1):
        title = result.get("title", "No title")
        link = result.get("link", "No link")
        snippet = result.get("snippet", "")
        formatted.append(f"{i}. {title}\n   URL: {link}\n   {snippet}")

    return "\n\n".join(formatted)


# ---------------------------------------------------------------------------
# Tool 2: Web scraper
# ---------------------------------------------------------------------------

@tool
def scrape_website(url: str) -> str:
    """
    Fetch a webpage and return its main readable text content.

    Use this when you already have a specific URL (either given directly
    by the user, or found via search_web) and need the actual page content
    to answer questions, write documentation, or generate a report.

    Args:
        url: The full URL to scrape, e.g. "https://www.example.com".

    Returns:
        Cleaned text content from the page (truncated if very long),
        or an error message if the page could not be fetched.
    """
    if not url or not url.strip():
        return "Error: no URL was provided."

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        # Some sites block requests with no User-Agent header
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            url, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("Scrape timed out for URL: %s", url)
        return f"Error: request timed out while scraping '{url}'."
    except requests.exceptions.HTTPError as e:
        logger.warning("HTTP error scraping %s: %s", url, e)
        return f"Error: could not access '{url}' (HTTP {response.status_code})."
    except requests.exceptions.RequestException as e:
        logger.error("Scrape failed for %s: %s", url, e)
        return f"Error: failed to fetch '{url}' - {e}"

    soup = BeautifulSoup(response.content, "html.parser")

    # Strip out tags that never contain useful readable content.
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Collapse excessive blank lines left behind after stripping tags.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    if not cleaned_text:
        return f"Error: no readable text content found at '{url}'."

    if len(cleaned_text) > config.MAX_SCRAPE_CHARS:
        cleaned_text = (
            cleaned_text[: config.MAX_SCRAPE_CHARS] + "\n\n[Content truncated...]"
        )

    return cleaned_text