"""
Catalog import services.

These functions bridge the Open Library client and the local database,
creating Author and Book records from OL data on first encounter and
returning the existing records on subsequent calls.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from .models import Author, Book
from .openlibrary import (
    OLAuthor,
    OLBook,
    OpenLibraryClient,
)

logger = logging.getLogger(__name__)

_client: OpenLibraryClient | None = None


def _get_client() -> OpenLibraryClient:
    global _client
    if _client is None:
        _client = OpenLibraryClient()
    return _client


def _parse_ol_date(raw: str) -> date | None:
    """Try to parse an Open Library date string; return None if not parseable."""
    if not raw:
        return None
    for fmt in ('%Y', '%Y-%m-%d', '%B %Y', '%B %d, %Y', '%d %B %Y'):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _get_or_create_author(ol_author: OLAuthor) -> Author:
    """Get or create a local Author record from an OL author dataclass."""
    name = ol_author.name or 'Unknown Author'
    if ol_author.olid:
        author, _ = Author.objects.get_or_create(
            external_id=ol_author.olid,
            defaults={
                'name': name,
                'bio': ol_author.bio or '',
                'birth_date': _parse_ol_date(ol_author.birth_date),
                'death_date': _parse_ol_date(ol_author.death_date),
            },
        )
        return author
    # No OLID — match by name as a best-effort dedup.
    author, _ = Author.objects.get_or_create(
        name=name,
        defaults={'bio': ol_author.bio or ''},
    )
    return author


def _create_book_from_ol(ol_book: OLBook) -> Book:
    """Persist a new Book (and its Authors) from OL data."""
    authors = [
        _get_or_create_author(a)
        for a in ol_book.authors
        if a.name
    ]
    book = Book.objects.create(
        title=ol_book.title,
        isbn_10=ol_book.isbn_10,
        isbn_13=ol_book.isbn_13,
        description=ol_book.description,
        page_count=ol_book.page_count,
        publisher=ol_book.publisher,
        published_date=_parse_ol_date(ol_book.published_date),
        language=ol_book.language or 'en',
        cover_image_url=ol_book.cover_url,
        external_id=ol_book.work_id,
    )
    if authors:
        book.authors.set(authors)
    return book


def get_or_import_book(isbn: str) -> tuple[Book, bool]:
    """
    Return a Book for the given ISBN, importing from Open Library if necessary.

    Returns a ``(book, imported)`` tuple where ``imported`` is ``True`` when
    the book was fetched from OL and ``False`` when it already existed.

    Raises:
        ``OpenLibraryNotFoundError`` – ISBN not found on OL.
        ``OpenLibraryError``         – Network or API failure.
    """
    clean = isbn.replace('-', '').replace(' ', '')

    # Check local DB first (isbn_13 is the more reliable key).
    existing = (
        Book.objects.filter(isbn_13=clean).first()
        or Book.objects.filter(isbn_10=clean).first()
    )
    if existing:
        return existing, False

    # Fetch from Open Library — may raise OpenLibraryNotFoundError / OpenLibraryError.
    ol_book = _get_client().get_book_by_isbn(clean)

    # Double-check DB with the OL-normalised ISBNs to handle aliased inputs.
    if ol_book.isbn_13:
        existing = Book.objects.filter(isbn_13=ol_book.isbn_13).first()
        if existing:
            return existing, False
    if ol_book.isbn_10:
        existing = Book.objects.filter(isbn_10=ol_book.isbn_10).first()
        if existing:
            return existing, False

    return _create_book_from_ol(ol_book), True
