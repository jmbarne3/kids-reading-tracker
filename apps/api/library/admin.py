from django.contrib import admin

from .models import ReadingProgress, ReadingSession, ShelfEntry


@admin.register(ShelfEntry)
class ShelfEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'shelf', 'added_at', 'updated_at')
    list_filter = ('shelf',)
    search_fields = ('user__email', 'user__username', 'book__title')
    raw_id_fields = ('user', 'book')
    readonly_fields = ('added_at', 'updated_at')


@admin.register(ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'started_at', 'finished_at')
    list_filter = ('finished_at',)
    search_fields = ('user__email', 'user__username', 'book__title')
    raw_id_fields = ('user', 'book')
    readonly_fields = ('started_at',)


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ('session', 'page', 'recorded_at')
    search_fields = ('session__book__title', 'session__user__email')
    raw_id_fields = ('session',)
    readonly_fields = ('recorded_at',)
