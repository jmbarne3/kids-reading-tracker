from django.test import TestCase

from .models import Author, Book


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
