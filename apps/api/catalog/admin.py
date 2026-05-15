from django.contrib import admin

from .models import Author, Book


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_date', 'external_id')
    search_fields = ('name', 'external_id')


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'isbn_13', 'published_date', 'page_count', 'external_id')
    list_filter = ('language',)
    search_fields = ('title', 'isbn_10', 'isbn_13', 'external_id')
    filter_horizontal = ('authors',)
