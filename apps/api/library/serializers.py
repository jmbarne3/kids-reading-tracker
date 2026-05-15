from rest_framework import serializers

from catalog.models import Book

from .models import ReadingProgress, ReadingSession, ShelfEntry


class BookBriefSerializer(serializers.ModelSerializer):
    """Lightweight read-only book representation for embedding in other serializers."""

    author_names = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ('id', 'title', 'author_names', 'isbn_13', 'cover_image_url', 'page_count')

    def get_author_names(self, obj: Book) -> list[str]:
        return [a.name for a in obj.authors.all()]


class ShelfEntrySerializer(serializers.ModelSerializer):
    book = BookBriefSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source='book',
        write_only=True,
        help_text='ID of the Book to place on this shelf.',
    )

    class Meta:
        model = ShelfEntry
        fields = ('id', 'book', 'book_id', 'shelf', 'added_at', 'updated_at')
        read_only_fields = ('id', 'added_at', 'updated_at')

    def validate(self, attrs: dict) -> dict:
        # Prevent duplicate shelf entries on creation.
        if not self.instance:
            user = self.context['request'].user
            book = attrs.get('book')
            if book and ShelfEntry.objects.filter(user=user, book=book).exists():
                raise serializers.ValidationError(
                    'This book is already on one of your shelves. '
                    'PATCH the existing entry to move it to a different shelf.'
                )
        return attrs

    def create(self, validated_data: dict) -> ShelfEntry:
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = ('id', 'page', 'recorded_at', 'notes')
        read_only_fields = ('id', 'recorded_at')


class ReadingSessionSerializer(serializers.ModelSerializer):
    book = BookBriefSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source='book',
        write_only=True,
        help_text='ID of the Book being read.',
    )
    current_page = serializers.SerializerMethodField(
        help_text='The most recently recorded page number, or null.',
    )
    percent_complete = serializers.SerializerMethodField(
        help_text='Percentage of the book read (0–100), or null if unknown.',
    )

    class Meta:
        model = ReadingSession
        fields = (
            'id', 'book', 'book_id',
            'started_at', 'finished_at', 'notes',
            'current_page', 'percent_complete',
        )
        read_only_fields = ('id', 'started_at', 'current_page', 'percent_complete')

    def get_current_page(self, obj: ReadingSession) -> int | None:
        return obj.current_page

    def get_percent_complete(self, obj: ReadingSession) -> float | None:
        return obj.percent_complete

    def create(self, validated_data: dict) -> ReadingSession:
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddByISBNRequestSerializer(serializers.Serializer):
    isbn = serializers.CharField(help_text='ISBN-10 or ISBN-13.')
    shelf = serializers.ChoiceField(choices=ShelfEntry.SHELF_CHOICES)


class AddByISBNResponseSerializer(serializers.Serializer):
    shelf_entry = ShelfEntrySerializer()
    imported = serializers.BooleanField(
        help_text='True if the book was newly imported from Open Library.',
    )
