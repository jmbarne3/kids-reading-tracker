from django.urls import path

from . import views

urlpatterns = [
    # Shelf
    path('shelf/', views.ShelfEntryListCreateView.as_view(), name='shelf-list'),
    path('shelf/<int:pk>/', views.ShelfEntryDetailView.as_view(), name='shelf-detail'),

    # Reading sessions
    path('sessions/', views.ReadingSessionListCreateView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', views.ReadingSessionDetailView.as_view(), name='session-detail'),

    # Progress entries (nested under a session)
    path(
        'sessions/<int:session_pk>/progress/',
        views.ReadingProgressListCreateView.as_view(),
        name='progress-list',
    ),

    # Progress entry detail (delete only — for corrections)
    path('progress/<int:pk>/', views.ReadingProgressDetailView.as_view(), name='progress-detail'),
]
