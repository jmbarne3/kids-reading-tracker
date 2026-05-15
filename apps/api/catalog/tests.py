from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from .models import Author, Book
from .openlibrary import OLAuthor, OLBook, OpenLibraryError, OpenLibraryNotFoundError
from .services import (
    _create_book_from_ol,
    _get_or_create_author,
    _parse_ol_date,
    get_or_import_book,
)


class AuthorModelTest(TestCase):
    def test_create_author(self):
        author = Author.objects.create(name='J.K. Rowling')
        self.assertEqual(author.name, 'J.K. Rowling')
        self.assertEqual(str(author), 'J.K. Rowling')

    def test_external_id_stored_and_indexed(self):
        author = Author.objects.create(name='Tolkien', external_id='OL26320A')
        fetched = Author.objects.get(external_id='OL26320A')
        self.assertEqual(fetched.name, 'Tolkien')

    def test_optional_fields_default_blank(self):
        author = Author.objects.create(name='Anonymous')
        self.assertEqual(author.bio, '')
        self.assertIsNone(author.birth_date)
        self.assertIsNone(author.death_date)

    def test_ordering_by_name(self):
        Author.objects.create(name='Zara Stein')
        Author.objects.create(name='Aaron Beck')
        names = list(Author.objects.values_list('name', flat=True))
        self.assertEqual(names[0], 'Aaron Beck')
        self.assertEqual(names[1], 'Zara Stein')


class BookModelTest(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name='J.K. Rowling')

    def test_create_book(self):
        book = Book.objects.create(title="Harry Potter and the Philosopher's Stone", page_count=309)
        self.assertEqual(str(book), "Harry Potter and the Philosopher's Stone")
        self.assertEqual(book.page_count, 309)

    def test_add_author_many_to_many(self):
        book = Book.objects.create(title='Harry Potter')
        book.authors.add(self.author)
        self.assertIn(self.author, book.authors.all())
        self.assertIn(book, self.author.books.all())

    def test_multiple_authors(self):
        co_author = Author.objects.create(name='Co Author')
        book = Book.objects.create(title='Co-written Book')
        book.authors.add(self.author, co_author)
        self.assertEqual(book.authors.count(), 2)

    def test_isbn_fields(self):
        book = Book.objects.create(
            title='Test Book',
            isbn_10='0439708184',
            isbn_13='9780439708180',
        )
        self.assertEqual(book.isbn_10, '0439708184')
        self.assertEqual(book.isbn_13, '9780439708180')

    def test_page_count_optional(self):
        book = Book.objects.create(title='Unknown Length')
        self.assertIsNone(book.page_count)

    def test_default_language_is_english(self):
        book = Book.objects.create(title='English Book')
        self.assertEqual(book.language, 'en')

    def test_ordering_by_title(self):
        Book.objects.create(title='Zebra')
        Book.objects.create(title='Aardvark')
        titles = list(Book.objects.values_list('title', flat=True))
        self.assertEqual(titles[0], 'Aardvark')
        self.assertEqual(titles[1], 'Zebra')


# ---------------------------------------------------------------------------
# _parse_ol_date
# ---------------------------------------------------------------------------

class ParseOLDateTest(TestCase):
    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_ol_date(''))

    def test_year_only(self):
        self.assertEqual(_parse_ol_date('2003'), date(2003, 1, 1))

    def test_iso_date(self):
        self.assertEqual(_parse_ol_date('2003-06-15'), date(2003, 6, 15))

    def test_month_year(self):
        self.assertEqual(_parse_ol_date('March 2003'), date(2003, 3, 1))

    def test_month_day_year(self):
        self.assertEqual(_parse_ol_date('June 1, 2003'), date(2003, 6, 1))

    def test_day_month_year(self):
        self.assertEqual(_parse_ol_date('1 January 1892'), date(1892, 1, 1))

    def test_unparseable_returns_none(self):
        self.assertIsNone(_parse_ol_date('sometime in the 90s'))

    def test_strips_leading_trailing_whitespace(self):
        self.assertEqual(_parse_ol_date('  2010  '), date(2010, 1, 1))


# ---------------------------------------------------------------------------
# _get_or_create_author
# ---------------------------------------------------------------------------

class GetOrCreateAuthorTest(TestCase):
    def test_creates_author_with_olid(self):
        ol = OLAuthor(olid='OL26320A', name='J.K. Rowling', bio='British author', birth_date='31 July 1965')
        author = _get_or_create_author(ol)
        self.assertEqual(author.name, 'J.K. Rowling')
        self.assertEqual(author.external_id, 'OL26320A')
        self.assertEqual(author.bio, 'British author')
        self.assertEqual(author.birth_date, date(1965, 7, 31))

    def test_idempotent_with_same_olid(self):
        ol = OLAuthor(olid='OL26320A', name='J.K. Rowling')
        a1 = _get_or_create_author(ol)
        a2 = _get_or_create_author(ol)
        self.assertEqual(a1.pk, a2.pk)
        self.assertEqual(Author.objects.filter(external_id='OL26320A').count(), 1)

    def test_creates_author_without_olid_by_name(self):
        ol = OLAuthor(olid='', name='Anonymous Writer')
        author = _get_or_create_author(ol)
        self.assertEqual(author.name, 'Anonymous Writer')
        self.assertEqual(author.external_id, '')

    def test_idempotent_by_name_when_no_olid(self):
        ol = OLAuthor(olid='', name='Anonymous Writer')
        a1 = _get_or_create_author(ol)
        a2 = _get_or_create_author(ol)
        self.assertEqual(a1.pk, a2.pk)
        self.assertEqual(Author.objects.filter(name='Anonymous Writer').count(), 1)

    def test_empty_name_defaults_to_unknown_author(self):
        ol = OLAuthor(olid='OL999Z', name='')
        author = _get_or_create_author(ol)
        self.assertEqual(author.name, 'Unknown Author')


# ---------------------------------------------------------------------------
# _create_book_from_ol
# ---------------------------------------------------------------------------

class CreateBookFromOLTest(TestCase):
    def _make_ol_book(self, **overrides):
        defaults = dict(
            work_id='OL12345W',
            edition_id='OL67890M',
            title='Test Book',
            authors=[OLAuthor(olid='OL1A', name='Test Author')],
            isbn_10='0123456789',
            isbn_13='9780123456786',
            description='A test book.',
            page_count=200,
            publisher='Test Publisher',
            published_date='2020',
            language='en',
            cover_url='https://covers.openlibrary.org/b/id/123-M.jpg',
        )
        defaults.update(overrides)
        return OLBook(**defaults)

    def test_creates_book_with_all_fields(self):
        book = _create_book_from_ol(self._make_ol_book())
        self.assertEqual(book.title, 'Test Book')
        self.assertEqual(book.isbn_10, '0123456789')
        self.assertEqual(book.isbn_13, '9780123456786')
        self.assertEqual(book.page_count, 200)
        self.assertEqual(book.publisher, 'Test Publisher')
        self.assertEqual(book.language, 'en')
        self.assertEqual(book.external_id, 'OL12345W')
        self.assertEqual(book.published_date, date(2020, 1, 1))
        self.assertTrue(book.cover_image_url.startswith('https://'))

    def test_authors_linked(self):
        ol_book = self._make_ol_book(
            authors=[
                OLAuthor(olid='OL1A', name='Author One'),
                OLAuthor(olid='OL2A', name='Author Two'),
            ]
        )
        book = _create_book_from_ol(ol_book)
        self.assertEqual(book.authors.count(), 2)
        names = set(book.authors.values_list('name', flat=True))
        self.assertIn('Author One', names)
        self.assertIn('Author Two', names)

    def test_authors_with_empty_name_are_skipped(self):
        ol_book = self._make_ol_book(
            authors=[
                OLAuthor(olid='OL1A', name=''),
                OLAuthor(olid='OL2A', name='Real Author'),
            ]
        )
        book = _create_book_from_ol(ol_book)
        self.assertEqual(book.authors.count(), 1)

    def test_no_authors_creates_book_without_authors(self):
        book = _create_book_from_ol(self._make_ol_book(authors=[]))
        self.assertEqual(book.authors.count(), 0)

    def test_unparseable_published_date_stored_as_none(self):
        book = _create_book_from_ol(self._make_ol_book(published_date='sometime long ago'))
        self.assertIsNone(book.published_date)

    def test_missing_language_defaults_to_en(self):
        book = _create_book_from_ol(self._make_ol_book(language=''))
        self.assertEqual(book.language, 'en')


# ---------------------------------------------------------------------------
# get_or_import_book
# ---------------------------------------------------------------------------

class GetOrImportBookTest(TestCase):
    def _mock_ol_book(self, isbn_10='0439708184', isbn_13='9780439708180'):
        return OLBook(
            work_id='OL82563W',
            edition_id='OL7353617M',
            title="Harry Potter and the Sorcerer's Stone",
            authors=[OLAuthor(olid='OL23919A', name='J.K. Rowling')],
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            page_count=309,
            language='en',
        )

    def test_returns_existing_book_by_isbn_13(self):
        book = Book.objects.create(title='Existing', isbn_13='9780439708180')
        result, imported = get_or_import_book('9780439708180')
        self.assertEqual(result.pk, book.pk)
        self.assertFalse(imported)

    def test_returns_existing_book_by_isbn_10(self):
        book = Book.objects.create(title='Existing', isbn_10='0439708184')
        result, imported = get_or_import_book('0439708184')
        self.assertEqual(result.pk, book.pk)
        self.assertFalse(imported)

    def test_normalises_isbn_with_dashes(self):
        book = Book.objects.create(title='Existing', isbn_13='9780439708180')
        result, imported = get_or_import_book('978-0-439-70818-0')
        self.assertEqual(result.pk, book.pk)
        self.assertFalse(imported)

    def test_normalises_isbn_with_spaces(self):
        book = Book.objects.create(title='Existing', isbn_13='9780439708180')
        result, imported = get_or_import_book('978 0 439 70818 0')
        self.assertEqual(result.pk, book.pk)
        self.assertFalse(imported)

    @patch('catalog.services._get_client')
    def test_imports_book_from_ol_when_not_in_db(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_book_by_isbn.return_value = self._mock_ol_book()
        mock_get_client.return_value = mock_client

        result, imported = get_or_import_book('9780439708180')

        self.assertTrue(imported)
        self.assertEqual(result.title, "Harry Potter and the Sorcerer's Stone")
        self.assertEqual(result.isbn_13, '9780439708180')
        self.assertTrue(Book.objects.filter(isbn_13='9780439708180').exists())
        mock_client.get_book_by_isbn.assert_called_once_with('9780439708180')

    @patch('catalog.services._get_client')
    def test_no_duplicate_when_ol_returns_known_isbn(self, mock_get_client):
        # Book exists by isbn_13; user queries with isbn_10 which is not in DB yet.
        # OL responds with both ISBNs — the second DB check should catch the match.
        Book.objects.create(title='Already Here', isbn_13='9780439708180', isbn_10='')
        mock_client = MagicMock()
        mock_client.get_book_by_isbn.return_value = self._mock_ol_book()
        mock_get_client.return_value = mock_client

        result, imported = get_or_import_book('0439708184')
        self.assertFalse(imported)
        self.assertEqual(Book.objects.filter(isbn_13='9780439708180').count(), 1)

    @patch('catalog.services._get_client')
    def test_raises_not_found_for_unknown_isbn(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_book_by_isbn.side_effect = OpenLibraryNotFoundError('Not found')
        mock_get_client.return_value = mock_client

        with self.assertRaises(OpenLibraryNotFoundError):
            get_or_import_book('0000000000')

    @patch('catalog.services._get_client')
    def test_propagates_ol_network_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_book_by_isbn.side_effect = OpenLibraryError('Network error')
        mock_get_client.return_value = mock_client

        with self.assertRaises(OpenLibraryError):
            get_or_import_book('9780439708180')
