from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import ReadingProgress, ReadingSession, ShelfEntry
from .serializers import (
    ReadingProgressSerializer,
    ReadingSessionSerializer,
    ShelfEntrySerializer,
)


# ---------------------------------------------------------------------------
# Shelf
# ---------------------------------------------------------------------------

class ShelfEntryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/library/shelf/           — list the authenticated user's shelf entries.
    POST /api/library/shelf/           — add a book to a shelf.

    Filter by shelf type: GET /api/library/shelf/?shelf=currently_reading
    """

    serializer_class = ShelfEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            ShelfEntry.objects
            .filter(user=self.request.user)
            .select_related('book')
            .prefetch_related('book__authors')
        )
        shelf = self.request.query_params.get('shelf')
        if shelf:
            qs = qs.filter(shelf=shelf)
        return qs


class ShelfEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/library/shelf/{id}/    — retrieve a shelf entry.
    PATCH  /api/library/shelf/{id}/    — update (e.g. move to a different shelf).
    DELETE /api/library/shelf/{id}/    — remove a book from the shelf.
    """

    serializer_class = ShelfEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return (
            ShelfEntry.objects
            .filter(user=self.request.user)
            .select_related('book')
            .prefetch_related('book__authors')
        )


# ---------------------------------------------------------------------------
# Reading sessions
# ---------------------------------------------------------------------------

class ReadingSessionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/library/sessions/        — list the user's reading sessions.
    POST /api/library/sessions/        — start a new reading session for a book.

    Filter by book: GET /api/library/sessions/?book=42
    """

    serializer_class = ReadingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            ReadingSession.objects
            .filter(user=self.request.user)
            .select_related('book')
            .prefetch_related('book__authors', 'progress_entries')
        )
        book_id = self.request.query_params.get('book')
        if book_id:
            qs = qs.filter(book_id=book_id)
        return qs


class ReadingSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/library/sessions/{id}/ — retrieve a reading session.
    PATCH  /api/library/sessions/{id}/ — update (e.g. set finished_at or notes).
    DELETE /api/library/sessions/{id}/ — delete a session and all its progress.
    """

    serializer_class = ReadingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return (
            ReadingSession.objects
            .filter(user=self.request.user)
            .select_related('book')
            .prefetch_related('book__authors', 'progress_entries')
        )


# ---------------------------------------------------------------------------
# Reading progress
# ---------------------------------------------------------------------------

def _get_session_for_user(session_pk: int, user) -> ReadingSession:
    """Return the ReadingSession owned by ``user``, or raise a suitable error."""
    try:
        return ReadingSession.objects.select_related('book').get(pk=session_pk, user=user)
    except ReadingSession.DoesNotExist:
        raise NotFound('Reading session not found.')


class ReadingProgressListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/library/sessions/{session_id}/progress/
         — list all progress entries for a session, most recent first.

    POST /api/library/sessions/{session_id}/progress/
         — log the user's current page in this session.
    """

    serializer_class = ReadingProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session = _get_session_for_user(self.kwargs['session_pk'], self.request.user)
        return ReadingProgress.objects.filter(session=session)

    def perform_create(self, serializer: ReadingProgressSerializer) -> None:
        session = _get_session_for_user(self.kwargs['session_pk'], self.request.user)

        # Validate page number doesn't exceed the book's known page count.
        page: int = serializer.validated_data['page']
        page_count = session.book.page_count
        if page_count and page > page_count:
            raise ValidationError(
                {'page': f'Page {page} exceeds this book\'s page count ({page_count}).'}
            )

        serializer.save(session=session)


class ReadingProgressDetailView(generics.DestroyAPIView):
    """
    DELETE /api/library/progress/{id}/
           — remove an incorrect or duplicate progress entry.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ensure users can only delete their own progress entries.
        return ReadingProgress.objects.filter(session__user=self.request.user)
