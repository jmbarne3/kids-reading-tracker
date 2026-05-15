from django.conf import settings
from django.db import models


class ShelfEntry(models.Model):
    """
    Represents a book on one of the user's shelves.

    A user can have a book on only one shelf at a time (enforced by the
    unique_together constraint).  To move a book between shelves, update
    the ``shelf`` field on the existing entry rather than creating a new one.
    """

    CURRENTLY_READING = 'currently_reading'
    WANT_TO_READ = 'want_to_read'
    READ = 'read'
    DID_NOT_FINISH = 'did_not_finish'

    SHELF_CHOICES = [
        (CURRENTLY_READING, 'Currently Reading'),
        (WANT_TO_READ, 'Want to Read'),
        (READ, 'Read'),
        (DID_NOT_FINISH, 'Did Not Finish'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shelf_entries',
    )
    book = models.ForeignKey(
        'catalog.Book',
        on_delete=models.CASCADE,
        related_name='shelf_entries',
    )
    shelf = models.CharField(max_length=20, choices=SHELF_CHOICES)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('user', 'book')]

    def __str__(self) -> str:
        return f'{self.user} — {self.book.title!r} ({self.shelf})'


class ReadingSession(models.Model):
    """
    A single read-through of a book.

    Multiple sessions per (user, book) are allowed so that re-reads are
    tracked separately.  ``finished_at`` is null for an active/in-progress
    read and set when the user considers it done (whether they finished the
    book or just closed out the session).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_sessions',
    )
    book = models.ForeignKey(
        'catalog.Book',
        on_delete=models.CASCADE,
        related_name='reading_sessions',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self) -> str:
        return f'{self.user} — {self.book.title!r} (started {self.started_at:%Y-%m-%d})'

    @property
    def current_page(self) -> int | None:
        """The most recently recorded page number, or None if no progress yet."""
        latest = self.progress_entries.order_by('-recorded_at').first()
        return latest.page if latest else None

    @property
    def percent_complete(self) -> float | None:
        """
        Percentage of the book read based on the latest progress entry.
        Returns None if no progress has been logged or the book lacks a page count.
        """
        page = self.current_page
        if page is None or not self.book.page_count:
            return None
        return round((page / self.book.page_count) * 100, 1)


class ReadingProgress(models.Model):
    """
    A single page-position snapshot within a ReadingSession.

    Each time the user taps "Update Progress", a new entry is created with
    their current page.  The history of entries gives a timeline of how
    quickly they progressed through the book.
    """

    session = models.ForeignKey(
        ReadingSession,
        on_delete=models.CASCADE,
        related_name='progress_entries',
    )
    page = models.PositiveIntegerField(
        help_text='The page the reader is currently on.',
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self) -> str:
        return f'Session {self.session_id}: p.{self.page} @ {self.recorded_at:%Y-%m-%d %H:%M}'
