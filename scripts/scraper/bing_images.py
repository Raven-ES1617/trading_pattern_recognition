from __future__ import annotations

import html
import http.client
import re
import time
import urllib.parse
import urllib.error
import urllib.request


SEARCH_URL = "https://www.bing.com/images/search"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/132.0.0.0 Safari/537.36"
)
MURL_PATTERN = re.compile(r"murl&quot;:&quot;(.*?)&quot;")


def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def fetch_search_page(query: str, first: int = 1, retries: int = 3) -> str:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "first": first,
            "form": "HDRSC3",
        }
    )
    request = _build_request(f"{SEARCH_URL}?{params}")
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="ignore")
        except (
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            http.client.RemoteDisconnected,
            OSError,
        ) as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))

    if last_error is not None:
        return ""
    return ""


def extract_image_urls(page_html: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for match in MURL_PATTERN.finditer(page_html):
        candidate = html.unescape(match.group(1)).replace("\\/", "/").strip()
        if not candidate.startswith(("http://", "https://")):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)

    return urls


def search_image_urls(query: str, limit: int, pages: int = 5) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    for page_index in range(pages):
        first = 1 + page_index * 35
        page_html = fetch_search_page(query=query, first=first)
        page_urls = extract_image_urls(page_html)
        if not page_urls:
            break

        for url in page_urls:
            if url in seen:
                continue
            seen.add(url)
            collected.append(url)
            if len(collected) >= limit:
                return collected

    return collected
