from django.urls import path

from . import views
from .auth_views import (
    AppleAuthView,
    ChildAccountListCreateView,
    ChildProfileDetailView,
    ChildProfileListCreateView,
    GoogleAuthView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    TokenRefreshView,
)

urlpatterns = [
    path('', views.root, name='root'),

    # Authentication
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/me/', MeView.as_view(), name='auth-me'),

    # Social sign-in
    path('auth/google/', GoogleAuthView.as_view(), name='auth-google'),
    path('auth/apple/', AppleAuthView.as_view(), name='auth-apple'),

    # Child profile management (no-login profiles, parent only)
    path('auth/child-profiles/', ChildProfileListCreateView.as_view(), name='child-profile-list'),
    path('auth/child-profiles/<int:pk>/', ChildProfileDetailView.as_view(), name='child-profile-detail'),

    # Child account management (full login accounts for children 13+, parent only)
    path('auth/child-accounts/', ChildAccountListCreateView.as_view(), name='child-account-list'),
]
