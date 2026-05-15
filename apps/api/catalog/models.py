from django.db import models


class Author(models.Model):
    """
    Represents a book author.

    ``external_id`` stores the identifier from the external book API
    (e.g. Open Library ``/authors/OL...A``) so records can be enriched
    or de-duplicated against the upstream source.
    """

    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Identifier from the upstream book API (e.g. Open Library author key).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    """
    Represents a published book.

    Authors are stored as a many-to-many relationship so a book with
    multiple authors (or an author with multiple books) is handled
    naturally.  ``external_id`` stores the canonical identifier from
    the upstream book API so the record can be refreshed later.
    """

    title = models.CharField(max_length=512)
    authors = models.ManyToManyField(
        Author,
        related_name='books',
        blank=True,
    )
    isbn_10 = models.CharField(max_length=10, blank=True, db_index=True)
    isbn_13 = models.CharField(max_length=13, blank=True, db_index=True)
    description = models.TextField(blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.DateField(
        null=True,
        blank=True,
        help_text="Publication date; day/month may be approximate for older titles.",
    )
    language = models.CharField(
        max_length=10,
        blank=True,
        default='en',
        help_text="IETF language tag, e.g. 'en', 'es'.",
    )
    cover_image_url = models.URLField(blank=True)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Identifier from the upstream book API (e.g. Open Library work key).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title
