from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Book
from catalog.openlibrary import OLAuthor, OLBook, OpenLibraryError, OpenLibraryNotFoundError
from core.models import User

from .models import ReadingProgress, ReadingSession, ShelfEntry

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

STRONG_PASSWORD = 'Tr0ub4dor&3!'


def make_user(username='user', email='user@example.com', password=STRONG_PASSWORD):
    return User.objects.create_user(username=username, email=email, password=password)


def make_book(title='Test Book', page_count=300):
    return Book.objects.create(title=title, page_count=page_count)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class ShelfEntryModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book()

    def test_create_shelf_entry(self):
        entry = ShelfEntry.objects.create(
            user=self.user, book=self.book, shelf=ShelfEntry.CURRENTLY_READING
        )
        self.assertEqual(entry.shelf, ShelfEntry.CURRENTLY_READING)
        self.assertIn(self.book.title, str(entry))

    def test_unique_together_prevents_same_book_on_two_shelves(self):
        ShelfEntry.objects.create(
            user=self.user, book=self.book, shelf=ShelfEntry.CURRENTLY_READING
        )
        with self.assertRaises(IntegrityError):
            ShelfEntry.objects.create(
                user=self.user, book=self.book, shelf=ShelfEntry.WANT_TO_READ
            )

    def test_different_users_can_shelf_same_book(self):
        other = make_user(username='other', email='other@example.com')
        ShelfEntry.objects.create(user=self.user, book=self.book, shelf=ShelfEntry.READ)
        ShelfEntry.objects.create(user=other, book=self.book, shelf=ShelfEntry.WANT_TO_READ)
        self.assertEqual(ShelfEntry.objects.filter(book=self.book).count(), 2)

    def test_all_shelf_choices_are_valid(self):
        choices = [
            ShelfEntry.CURRENTLY_READING,
            ShelfEntry.WANT_TO_READ,
            ShelfEntry.READ,
            ShelfEntry.DID_NOT_FINISH,
        ]
        for i, shelf in enumerate(choices):
            u = make_user(username=f'u{i}', email=f'u{i}@test.com')
            entry = ShelfEntry.objects.create(user=u, book=self.book, shelf=shelf)
            self.assertEqual(entry.shelf, shelf)


class ReadingSessionModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(page_count=200)

    def test_create_session(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        self.assertIsNone(session.finished_at)
        self.assertIn(self.book.title, str(session))

    def test_current_page_is_none_without_progress(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        self.assertIsNone(session.current_page)

    def test_current_page_returns_most_recent_entry(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        earlier = ReadingProgress.objects.create(session=session, page=50)
        # Push the first entry into the past so ordering is deterministic.
        ReadingProgress.objects.filter(pk=earlier.pk).update(
            recorded_at=timezone.now() - timedelta(hours=1)
        )
        ReadingProgress.objects.create(session=session, page=80)
        self.assertEqual(session.current_page, 80)

    def test_percent_complete(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        ReadingProgress.objects.create(session=session, page=100)
        self.assertEqual(session.percent_complete, 50.0)

    def test_percent_complete_is_none_without_progress(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        self.assertIsNone(session.percent_complete)

    def test_percent_complete_is_none_when_book_has_no_page_count(self):
        book = Book.objects.create(title='No Page Count')  # page_count=None
        session = ReadingSession.objects.create(user=self.user, book=book)
        ReadingProgress.objects.create(session=session, page=50)
        self.assertIsNone(session.percent_complete)

    def test_multiple_sessions_allowed_for_same_book(self):
        ReadingSession.objects.create(user=self.user, book=self.book)
        ReadingSession.objects.create(user=self.user, book=self.book)
        count = ReadingSession.objects.filter(user=self.user, book=self.book).count()
        self.assertEqual(count, 2)


class ReadingProgressModelTest(TestCase):
    def setUp(self):
        user = make_user()
        book = make_book()
        self.session = ReadingSession.objects.create(user=user, book=book)

    def test_create_progress_entry(self):
        progress = ReadingProgress.objects.create(session=self.session, page=42)
        self.assertEqual(progress.page, 42)
        self.assertIn('42', str(progress))

    def test_progress_linked_to_session(self):
        ReadingProgress.objects.create(session=self.session, page=10)
        ReadingProgress.objects.create(session=self.session, page=20)
        self.assertEqual(self.session.progress_entries.count(), 2)

    def test_notes_optional(self):
        progress = ReadingProgress.objects.create(session=self.session, page=5)
        self.assertEqual(progress.notes, '')


# ---------------------------------------------------------------------------
# Shelf API tests
# ---------------------------------------------------------------------------

class ShelfAPITest(APITestCase):
    url = '/api/library/shelf/'

    def setUp(self):
        self.user = make_user()
        self.book = make_book()
        self.client.force_authenticate(self.user)

    def test_list_returns_empty_for_new_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_shelf_entry(self):
        response = self.client.post(
            self.url, {'book_id': self.book.pk, 'shelf': 'currently_reading'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['shelf'], 'currently_reading')
        self.assertEqual(response.data['book']['title'], self.book.title)
        self.assertEqual(response.data['book']['page_count'], self.book.page_count)

    def test_filter_by_shelf(self):
        book2 = make_book(title='Book Two')
        ShelfEntry.objects.create(user=self.user, book=self.book, shelf='currently_reading')
        ShelfEntry.objects.create(user=self.user, book=book2, shelf='want_to_read')
        response = self.client.get(f'{self.url}?shelf=currently_reading')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['shelf'], 'currently_reading')

    def test_move_book_to_different_shelf(self):
        entry = ShelfEntry.objects.create(
            user=self.user, book=self.book, shelf='currently_reading'
        )
        response = self.client.patch(
            f'{self.url}{entry.pk}/', {'shelf': 'read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['shelf'], 'read')

    def test_delete_shelf_entry(self):
        entry = ShelfEntry.objects.create(user=self.user, book=self.book, shelf='want_to_read')
        response = self.client.delete(f'{self.url}{entry.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShelfEntry.objects.filter(pk=entry.pk).exists())

    def test_duplicate_book_on_shelf_rejected(self):
        ShelfEntry.objects.create(user=self.user, book=self.book, shelf='currently_reading')
        response = self.client.post(
            self.url, {'book_id': self.book.pk, 'shelf': 'want_to_read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_not_allowed(self):
        entry = ShelfEntry.objects.create(user=self.user, book=self.book, shelf='read')
        response = self.client.put(f'{self.url}{entry.pk}/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_users_entries_not_visible(self):
        other = make_user(username='other', email='other@example.com')
        ShelfEntry.objects.create(user=other, book=self.book, shelf='read')
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 0)

    def test_cannot_modify_other_users_entry(self):
        other = make_user(username='other2', email='other2@example.com')
        entry = ShelfEntry.objects.create(user=other, book=self.book, shelf='read')
        response = self.client.patch(
            f'{self.url}{entry.pk}/', {'shelf': 'want_to_read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Reading session API tests
# ---------------------------------------------------------------------------

class ReadingSessionAPITest(APITestCase):
    url = '/api/library/sessions/'

    def setUp(self):
        self.user = make_user()
        self.book = make_book()
        self.client.force_authenticate(self.user)

    def test_list_returns_empty_for_new_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_session(self):
        response = self.client.post(self.url, {'book_id': self.book.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['book']['title'], self.book.title)
        self.assertIsNone(response.data['current_page'])
        self.assertIsNone(response.data['percent_complete'])
        self.assertIsNone(response.data['finished_at'])

    def test_filter_by_book(self):
        book2 = make_book(title='Other Book')
        ReadingSession.objects.create(user=self.user, book=self.book)
        ReadingSession.objects.create(user=self.user, book=book2)
        response = self.client.get(f'{self.url}?book={self.book.pk}')
        self.assertEqual(len(response.data), 1)

    def test_update_notes(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        response = self.client.patch(
            f'{self.url}{session.pk}/', {'notes': 'Great read so far!'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'Great read so far!')

    def test_set_finished_at(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        finished = '2026-05-10T12:00:00Z'
        response = self.client.patch(
            f'{self.url}{session.pk}/', {'finished_at': finished}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['finished_at'])

    def test_delete_session(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        response = self.client.delete(f'{self.url}{session.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ReadingSession.objects.filter(pk=session.pk).exists())

    def test_delete_session_cascades_progress(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        progress = ReadingProgress.objects.create(session=session, page=50)
        self.client.delete(f'{self.url}{session.pk}/')
        self.assertFalse(ReadingProgress.objects.filter(pk=progress.pk).exists())

    def test_put_not_allowed(self):
        session = ReadingSession.objects.create(user=self.user, book=self.book)
        response = self.client.put(f'{self.url}{session.pk}/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_other_users_sessions_not_visible(self):
        other = make_user(username='other', email='other@example.com')
        ReadingSession.objects.create(user=other, book=self.book)
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 0)

    def test_cannot_modify_other_users_session(self):
        other = make_user(username='other2', email='other2@example.com')
        session = ReadingSession.objects.create(user=other, book=self.book)
        response = self.client.patch(
            f'{self.url}{session.pk}/', {'notes': 'Hack'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Reading progress API tests
# ---------------------------------------------------------------------------

class ReadingProgressAPITest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(page_count=200)
        self.session = ReadingSession.objects.create(user=self.user, book=self.book)
        self.progress_url = f'/api/library/sessions/{self.session.pk}/progress/'
        self.client.force_authenticate(self.user)

    def test_list_returns_empty_initially(self):
        response = self.client.get(self.progress_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_log_progress_entry(self):
        response = self.client.post(self.progress_url, {'page': 50}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['page'], 50)

    def test_multiple_entries_build_history(self):
        self.client.post(self.progress_url, {'page': 30}, format='json')
        self.client.post(self.progress_url, {'page': 60}, format='json')
        response = self.client.get(self.progress_url)
        self.assertEqual(len(response.data), 2)

    def test_page_exceeding_book_page_count_rejected(self):
        response = self.client.post(self.progress_url, {'page': 999}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_page_equal_to_page_count_allowed(self):
        response = self.client.post(self.progress_url, {'page': 200}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_progress_updates_current_page_on_session(self):
        self.client.post(self.progress_url, {'page': 100}, format='json')
        session_response = self.client.get(f'/api/library/sessions/{self.session.pk}/')
        self.assertEqual(session_response.data['current_page'], 100)
        self.assertEqual(session_response.data['percent_complete'], 50.0)

    def test_delete_progress_entry(self):
        progress = ReadingProgress.objects.create(session=self.session, page=25)
        response = self.client.delete(f'/api/library/progress/{progress.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ReadingProgress.objects.filter(pk=progress.pk).exists())

    def test_cannot_add_progress_to_other_users_session(self):
        other = make_user(username='other', email='other@example.com')
        self.client.force_authenticate(other)
        response = self.client.post(self.progress_url, {'page': 10}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_other_users_progress(self):
        other = make_user(username='other2', email='other2@example.com')
        other_session = ReadingSession.objects.create(user=other, book=self.book)
        progress = ReadingProgress.objects.create(session=other_session, page=10)
        # self.user (authenticated) tries to delete other's progress
        response = self.client.delete(f'/api/library/progress/{progress.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.progress_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Add book by ISBN API tests
# ---------------------------------------------------------------------------

class AddBookByISBNAPITest(APITestCase):
    url = '/api/library/shelf/by-isbn/'

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)

    # -- Validation ----------------------------------------------------------

    def test_missing_isbn_returns_400(self):
        response = self.client.post(self.url, {'shelf': 'want_to_read'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('isbn', response.data)

    def test_missing_shelf_returns_400(self):
        response = self.client.post(self.url, {'isbn': '9780000000000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('shelf', response.data)

    def test_empty_body_returns_400_for_both_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('isbn', response.data)
        self.assertIn('shelf', response.data)

    def test_invalid_shelf_value_returns_400(self):
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'nonsense'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('shelf', response.data)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'want_to_read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- OL error handling ---------------------------------------------------

    @patch('library.views.get_or_import_book')
    def test_ol_not_found_returns_404(self, mock_import):
        mock_import.side_effect = OpenLibraryNotFoundError('Not found')
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'want_to_read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('library.views.get_or_import_book')
    def test_ol_network_error_returns_502(self, mock_import):
        mock_import.side_effect = OpenLibraryError('Timeout')
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'want_to_read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    # -- Happy path ----------------------------------------------------------

    @patch('library.views.get_or_import_book')
    def test_new_book_imported_and_shelved_returns_201(self, mock_import):
        book = make_book(title='Imported Book')
        mock_import.return_value = (book, True)
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'want_to_read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['imported'])
        self.assertEqual(response.data['shelf_entry']['shelf'], 'want_to_read')
        self.assertEqual(response.data['shelf_entry']['book']['title'], 'Imported Book')
        self.assertTrue(ShelfEntry.objects.filter(user=self.user, book=book).exists())

    @patch('library.views.get_or_import_book')
    def test_existing_book_not_yet_shelved_returns_201(self, mock_import):
        book = make_book(title='Existing Book')
        mock_import.return_value = (book, False)
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['imported'])
        self.assertEqual(response.data['shelf_entry']['shelf'], 'read')

    @patch('library.views.get_or_import_book')
    def test_book_already_on_same_shelf_returns_200(self, mock_import):
        book = make_book(title='Already Shelved')
        ShelfEntry.objects.create(user=self.user, book=book, shelf='currently_reading')
        mock_import.return_value = (book, False)
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'currently_reading'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['shelf_entry']['shelf'], 'currently_reading')
        # Still only one ShelfEntry
        self.assertEqual(ShelfEntry.objects.filter(user=self.user, book=book).count(), 1)

    @patch('library.views.get_or_import_book')
    def test_book_on_different_shelf_is_moved(self, mock_import):
        book = make_book(title='Moveable Book')
        ShelfEntry.objects.create(user=self.user, book=book, shelf='want_to_read')
        mock_import.return_value = (book, False)
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'currently_reading'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['shelf_entry']['shelf'], 'currently_reading')
        entry = ShelfEntry.objects.get(user=self.user, book=book)
        self.assertEqual(entry.shelf, 'currently_reading')

    @patch('library.views.get_or_import_book')
    def test_isbn_with_dashes_passed_through_to_service(self, mock_import):
        book = make_book(title='Dashed ISBN Book')
        mock_import.return_value = (book, True)
        response = self.client.post(
            self.url, {'isbn': '978-0-000-00000-0', 'shelf': 'read'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # The view strips whitespace but leaves dashes for the service to normalise.
        mock_import.assert_called_once_with('978-0-000-00000-0')

    @patch('library.views.get_or_import_book')
    def test_response_includes_book_details(self, mock_import):
        book = make_book(title='Detail Book', page_count=150)
        mock_import.return_value = (book, True)
        response = self.client.post(
            self.url, {'isbn': '9780000000000', 'shelf': 'read'}, format='json'
        )
        entry_data = response.data['shelf_entry']
        self.assertIn('book', entry_data)
        self.assertEqual(entry_data['book']['title'], 'Detail Book')
        self.assertEqual(entry_data['book']['page_count'], 150)
