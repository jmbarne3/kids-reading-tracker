"""
Thin wrapper around the Open Library REST API.

Only the read-only, unauthenticated endpoints are used here; no Open Library
account credentials are required.

Reference:
  https://openlibrary.org/developers/api
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://openlibrary.org"
_COVERS_URL = "https://covers.openlibrary.org"

# Providing a descriptive User-Agent unlocks a 3x rate-limit allowance from OL
# and lets them contact us if our traffic spikes.  Replace the email before
# deploying to production.
_DEFAULT_USER_AGENT = "KidsReadingTracker/1.0 (change-me@example.com)"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OLAuthor:
    """Author data returned from Open Library."""

    olid: str  # e.g. "OL26320A"
    name: str
    bio: str = ""
    birth_date: str = ""  # Raw OL string, e.g. "3 January 1892"
    death_date: str = ""


@dataclass
class OLBook:
    """
    Book data returned from Open Library.

    ``work_id`` is the canonical Open Library work key (e.g. "OL27448W").
    ``edition_id`` is the specific edition key (e.g. "OL25952968M"); it is
    empty when the result came from a work-level or search endpoint.
    """

    work_id: str
    edition_id: str
    title: str
    authors: list[OLAuthor] = field(default_factory=list)
    isbn_10: str = ""
    isbn_13: str = ""
    description: str = ""
    page_count: Optional[int] = None
    publisher: str = ""
    published_date: str = ""  # Raw OL string, e.g. "2003" or "March 2003"
    language: str = ""  # IETF two-letter tag after normalisation
    cover_url: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OpenLibraryError(Exception):
    """Raised when the Open Library API returns an unexpected response."""


class OpenLibraryNotFoundError(OpenLibraryError):
    """Raised when the requested resource does not exist on Open Library."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class OpenLibraryClient:
    """
    Read-only client for the Open Library REST API.

    A single ``requests.Session`` is reused across calls so that TCP
    connections are pooled.

    Usage::

        client = OpenLibraryClient()
        book   = client.get_book_by_isbn("9780747532699")
        books  = client.search_books(title="Harry Potter", limit=5)
        author = client.get_author("OL26320A")
    """

    def __init__(
        self,
        user_agent: str = _DEFAULT_USER_AGENT,
        base_url: str = _BASE_URL,
        timeout: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_book_by_isbn(self, isbn: str) -> OLBook:
        """
        Fetch a book by ISBN-10 or ISBN-13.

        Resolves to the canonical Open Library edition, then fetches the
        parent work to obtain the description and full author details.

        Raises ``OpenLibraryNotFoundError`` if no edition exists for that ISBN.
        """
        clean = isbn.replace("-", "").replace(" ", "")
        data = self._get(f"/isbn/{clean}.json")
        return self._edition_data_to_book(data)

    def get_work(self, work_id: str) -> OLBook:
        """
        Fetch a work by its Open Library ID (e.g. ``"OL27448W"``).

        Work-level results don't carry edition-specific fields (ISBNs, page
        count, publisher).  Use ``get_book_by_isbn`` when you have an ISBN.
        """
        key = work_id if work_id.startswith("/works/") else f"/works/{work_id}"
        data = self._get(f"{key}.json")
        return self._work_data_to_book(data)

    def get_author(self, author_id: str) -> OLAuthor:
        """
        Fetch an author by their Open Library ID (e.g. ``"OL26320A"``).
        """
        key = author_id if author_id.startswith("/authors/") else f"/authors/{author_id}"
        data = self._get(f"{key}.json")
        return self._author_data_to_ol_author(data)

    def search_books(
        self,
        *,
        query: str = "",
        title: str = "",
        author: str = "",
        isbn: str = "",
        limit: int = 10,
    ) -> list[OLBook]:
        """
        Search for books using the Open Library Search API.

        Provide at least one of ``query``, ``title``, ``author``, or ``isbn``.
        Results are work-level; use ``get_book_by_isbn`` to get full edition
        detail for a specific result.

        ``limit`` is capped at 100 per Open Library guidelines.
        """
        has_search_term = any([query, title, author, isbn])
        if not has_search_term:
            raise ValueError("At least one search parameter must be provided.")

        params: dict = {
            "limit": min(limit, 100),
            # Request only the fields we need to keep the payload small.
            "fields": (
                "key,title,author_name,author_key,isbn,cover_i,"
                "first_publish_year,publisher,language,number_of_pages_median"
            ),
        }
        if query:
            params["q"] = query
        if title:
            params["title"] = title
        if author:
            params["author"] = author
        if isbn:
            params["isbn"] = isbn.replace("-", "").replace(" ", "")

        data = self._get("/search.json", params=params)
        return [self._search_doc_to_book(doc) for doc in data.get("docs", [])]

    # ------------------------------------------------------------------
    # HTTP layer
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise OpenLibraryNotFoundError(f"Not found: {url}") from exc
            raise OpenLibraryError(f"HTTP error from Open Library: {exc}") from exc
        except requests.RequestException as exc:
            raise OpenLibraryError(f"Network error reaching Open Library: {exc}") from exc

    # ------------------------------------------------------------------
    # Response → dataclass mapping
    # ------------------------------------------------------------------

    def _parse_olid(self, key: str) -> str:
        """Extract the bare OLID from a full path, e.g. '/works/OL27448W' → 'OL27448W'."""
        return key.split("/")[-1]

    def _cover_url(self, cover_id: int | None, size: str = "M") -> str:
        if not cover_id:
            return ""
        return f"{_COVERS_URL}/b/id/{cover_id}-{size}.jpg"

    def _author_data_to_ol_author(self, data: dict) -> OLAuthor:
        bio_raw = data.get("bio", "")
        bio = bio_raw.get("value", "") if isinstance(bio_raw, dict) else bio_raw
        return OLAuthor(
            olid=self._parse_olid(data.get("key", "")),
            name=data.get("name", ""),
            bio=bio,
            birth_date=data.get("birth_date", ""),
            death_date=data.get("death_date", ""),
        )

    def _fetch_author_by_ref(self, author_ref: dict) -> OLAuthor:
        """Fetch a single author given a ``{"key": "/authors/OL..."}`` reference dict."""
        key = author_ref.get("key", "")
        try:
            return self.get_author(key)
        except OpenLibraryError:
            logger.warning("Could not fetch author %s from Open Library", key)
            return OLAuthor(olid=self._parse_olid(key), name="")

    def _edition_data_to_book(self, data: dict) -> OLBook:
        edition_id = self._parse_olid(data.get("key", ""))

        # Resolve the parent work for description and author details.
        works = data.get("works", [])
        work_id = self._parse_olid(works[0]["key"]) if works else ""
        description = ""
        authors: list[OLAuthor] = []

        if work_id:
            try:
                work_data = self._get(f"/works/{work_id}.json")
                desc_raw = work_data.get("description", "")
                description = desc_raw.get("value", "") if isinstance(desc_raw, dict) else desc_raw
                authors = [
                    self._fetch_author_by_ref(entry["author"])
                    for entry in work_data.get("authors", [])
                    if "author" in entry
                ]
            except OpenLibraryError:
                logger.warning(
                    "Could not fetch work %s for edition %s", work_id, edition_id
                )

        isbn_10_list = data.get("isbn_10", [])
        isbn_13_list = data.get("isbn_13", [])
        publishers = data.get("publishers", [])
        languages = data.get("languages", [])
        language = _ol_language_to_iso(self._parse_olid(languages[0]["key"])) if languages else ""
        first_cover = data.get("covers", [None])[0] if data.get("covers") else None

        return OLBook(
            work_id=work_id,
            edition_id=edition_id,
            title=data.get("title", ""),
            authors=authors,
            isbn_10=isbn_10_list[0] if isbn_10_list else "",
            isbn_13=isbn_13_list[0] if isbn_13_list else "",
            description=description,
            page_count=data.get("number_of_pages"),
            publisher=publishers[0] if publishers else "",
            published_date=data.get("publish_date", ""),
            language=language,
            cover_url=self._cover_url(first_cover),
        )

    def _work_data_to_book(self, data: dict) -> OLBook:
        work_id = self._parse_olid(data.get("key", ""))
        desc_raw = data.get("description", "")
        description = desc_raw.get("value", "") if isinstance(desc_raw, dict) else desc_raw
        authors = [
            self._fetch_author_by_ref(entry["author"])
            for entry in data.get("authors", [])
            if "author" in entry
        ]
        first_cover = data.get("covers", [None])[0] if data.get("covers") else None
        return OLBook(
            work_id=work_id,
            edition_id="",
            title=data.get("title", ""),
            authors=authors,
            description=description,
            cover_url=self._cover_url(first_cover),
        )

    def _search_doc_to_book(self, doc: dict) -> OLBook:
        work_id = self._parse_olid(doc.get("key", ""))
        author_names: list[str] = doc.get("author_name", [])
        author_keys: list[str] = doc.get("author_key", [])
        authors = [
            OLAuthor(olid=key, name=name)
            for key, name in zip(author_keys, author_names)
        ]
        isbns: list[str] = doc.get("isbn", [])
        isbn_13 = next((i for i in isbns if len(i) == 13), "")
        isbn_10 = next((i for i in isbns if len(i) == 10), "")
        publishers: list[str] = doc.get("publisher", [])
        languages: list[str] = doc.get("language", [])
        language = _ol_language_to_iso(languages[0]) if languages else ""
        return OLBook(
            work_id=work_id,
            edition_id="",
            title=doc.get("title", ""),
            authors=authors,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            page_count=doc.get("number_of_pages_median"),
            publisher=publishers[0] if publishers else "",
            published_date=str(doc.get("first_publish_year", "")),
            language=language,
            cover_url=self._cover_url(doc.get("cover_i")),
        )


# ---------------------------------------------------------------------------
# Language code normalisation
# ---------------------------------------------------------------------------

# Open Library uses ISO 639-2/B three-letter codes; map common ones to the
# IETF two-letter tags stored in the Book.language field.
_OL_LANGUAGE_MAP: dict[str, str] = {
    "eng": "en", "fre": "fr", "ger": "de", "spa": "es",
    "ita": "it", "por": "pt", "rus": "ru", "jpn": "ja",
    "zho": "zh", "ara": "ar", "hin": "hi", "kor": "ko",
    "nld": "nl", "pol": "pl", "swe": "sv", "nor": "no",
    "dan": "da", "fin": "fi", "tur": "tr", "vie": "vi",
}


def _ol_language_to_iso(ol_code: str) -> str:
    """Convert an Open Library 3-letter language code to an IETF 2-letter tag."""
    return _OL_LANGUAGE_MAP.get(ol_code.lower(), ol_code)
