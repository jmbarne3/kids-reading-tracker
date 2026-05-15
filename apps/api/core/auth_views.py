import logging

import requests as http_requests
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ChildProfile, SocialAccount, User
from .serializers import (
    AppleAuthSerializer,
    AuthTokenResponseSerializer,
    ChildProfileSerializer,
    CreateChildAccountSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    RegisterSerializer,
    TokenRefreshResponseSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_tokens(user: User) -> tuple[str, str]:
    """Return (access_token_str, refresh_token_str) for the given user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def _set_auth_cookies(response: Response, access: str, refresh: str | None = None) -> None:
    """Attach HttpOnly JWT cookies to a response for browser clients."""
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        access,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    if refresh:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            httponly=settings.AUTH_COOKIE_HTTP_ONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )


def _find_or_create_social_user(
    provider: str,
    provider_user_id: str,
    email: str,
    **kwargs,
) -> User:
    """
    Return the User linked to the given social identity.
    If no SocialAccount exists yet, try to link to an existing User by email;
    otherwise create a new parent-role User, then create the SocialAccount link.
    """
    try:
        social = SocialAccount.objects.select_related('user').get(
            provider=provider,
            provider_user_id=provider_user_id,
        )
        user = social.user
        # Update avatar if we now have one and the user doesn't yet
        avatar_url = kwargs.get('avatar_url', '')
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            user.save(update_fields=['avatar_url'])
        return user
    except SocialAccount.DoesNotExist:
        pass

    # Try to link to an existing account by email (e.g. user already registered
    # with email/password and is now adding a social login).
    user = User.objects.filter(email=email).first() if email else None

    if user is None:
        base = email.split('@')[0] if email else provider_user_id[:30]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1
        user = User.objects.create_user(
            username=username,
            email=email or '',
            first_name=kwargs.get('first_name', ''),
            last_name=kwargs.get('last_name', ''),
            avatar_url=kwargs.get('avatar_url', ''),
            role=User.ROLE_PARENT,
        )

    SocialAccount.objects.create(
        user=user,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email or '',
    )
    return user


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

@extend_schema(request=RegisterSerializer, responses={201: AuthTokenResponseSerializer})
class RegisterView(APIView):
    """POST /api/auth/register/ — create a parent account with email+password."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        access, refresh = _issue_tokens(user)
        response = Response(
            {'user': UserSerializer(user).data, 'access': access, 'refresh': refresh},
            status=status.HTTP_201_CREATED,
        )
        _set_auth_cookies(response, access, refresh)
        return response


@extend_schema(request=LoginSerializer, responses={200: AuthTokenResponseSerializer})
class LoginView(APIView):
    """POST /api/auth/login/ — authenticate with email+password, receive JWT."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        access, refresh = _issue_tokens(user)
        response = Response(
            {'user': UserSerializer(user).data, 'access': access, 'refresh': refresh},
        )
        _set_auth_cookies(response, access, refresh)
        return response


@extend_schema(responses={200: None})
class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklist the refresh token and clear cookies."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = (
            request.data.get('refresh')
            or request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        )
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass  # Already invalid or blacklisted — acceptable.

        response = Response({'detail': 'Logged out.'})
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH)
        return response


@extend_schema(
    request=TokenRefreshResponseSerializer,
    responses={200: TokenRefreshResponseSerializer},
)
class TokenRefreshView(APIView):
    """
    POST /api/auth/token/refresh/
    Accept the refresh token from the request body (native apps) or from the
    HttpOnly cookie (browsers).  Returns a new access token (and rotated refresh
    token when ROTATE_REFRESH_TOKENS=True).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_raw = (
            request.data.get('refresh')
            or request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        )
        if not refresh_raw:
            return Response(
                {'detail': 'Refresh token required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TokenRefreshSerializer(data={'refresh': refresh_raw})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        data = serializer.validated_data  # has 'access' and optionally 'refresh'
        response = Response(data)
        _set_auth_cookies(response, data['access'], data.get('refresh'))
        return response


@extend_schema(request=GoogleAuthSerializer, responses={200: AuthTokenResponseSerializer})
class GoogleAuthView(APIView):
    """
    POST /api/auth/google/
    Verify a Google ID token issued by the Google Sign-In SDK (web or native).
    Body: { "id_token": "<token from Google>" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GOOGLE_CLIENT_ID:
            return Response(
                {'detail': 'Google authentication is not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            idinfo = google_id_token.verify_oauth2_token(
                serializer.validated_data['id_token'],
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as exc:
            logger.warning('Google token verification failed: %s', exc)
            return Response(
                {'detail': 'Invalid Google token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _find_or_create_social_user(
            provider=SocialAccount.PROVIDER_GOOGLE,
            provider_user_id=idinfo['sub'],
            email=idinfo.get('email', ''),
            first_name=idinfo.get('given_name', ''),
            last_name=idinfo.get('family_name', ''),
            avatar_url=idinfo.get('picture', ''),
        )

        access, refresh = _issue_tokens(user)
        response = Response(
            {'user': UserSerializer(user).data, 'access': access, 'refresh': refresh},
        )
        _set_auth_cookies(response, access, refresh)
        return response


@extend_schema(request=AppleAuthSerializer, responses={200: AuthTokenResponseSerializer})
class AppleAuthView(APIView):
    """
    POST /api/auth/apple/
    Verify an Apple identity token issued by Sign in with Apple (web JS SDK or
    native iOS/macOS SDK).

    Body:
      {
        "identity_token": "<JWT from Apple>",
        "first_name": "...",   // optional — Apple only sends this on first auth
        "last_name":  "..."    // optional
      }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AppleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.APPLE_APP_ID:
            return Response(
                {'detail': 'Apple authentication is not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        identity_token = serializer.validated_data['identity_token']

        try:
            import jwt as pyjwt
            from jwt.algorithms import RSAAlgorithm

            # Fetch Apple's current public keys
            resp = http_requests.get('https://appleid.apple.com/auth/keys', timeout=10)
            resp.raise_for_status()
            apple_keys = resp.json().get('keys', [])

            header = pyjwt.get_unverified_header(identity_token)
            matching_key_data = next(
                (k for k in apple_keys if k.get('kid') == header.get('kid')),
                None,
            )
            if matching_key_data is None:
                return Response(
                    {'detail': 'Apple public key not found.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            public_key = RSAAlgorithm.from_jwk(matching_key_data)
            payload = pyjwt.decode(
                identity_token,
                public_key,
                algorithms=['RS256'],
                audience=settings.APPLE_APP_ID,
                issuer='https://appleid.apple.com',
            )
        except Exception as exc:
            logger.warning('Apple token verification failed: %s', exc)
            return Response(
                {'detail': 'Invalid Apple token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = _find_or_create_social_user(
            provider=SocialAccount.PROVIDER_APPLE,
            provider_user_id=payload['sub'],
            email=payload.get('email', ''),
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
        )

        access, refresh = _issue_tokens(user)
        response = Response(
            {'user': UserSerializer(user).data, 'access': access, 'refresh': refresh},
        )
        _set_auth_cookies(response, access, refresh)
        return response


@extend_schema(responses={200: UserSerializer})
class MeView(APIView):
    """GET /api/auth/me/ — return the authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Child profile management (parent only)
# ---------------------------------------------------------------------------

class ChildProfileListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/auth/child-profiles/  — list this parent's child profiles
    POST /api/auth/child-profiles/  — create a new child profile
    """
    serializer_class = ChildProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChildProfile.objects.filter(parent=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != User.ROLE_PARENT:
            raise PermissionDenied('Only parent accounts can create child profiles.')
        serializer.save(parent=self.request.user)


class ChildProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/auth/child-profiles/<pk>/
    """
    serializer_class = ChildProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChildProfile.objects.filter(parent=self.request.user)


# ---------------------------------------------------------------------------
# Child account management (parent creates full login account for child 13+)
# ---------------------------------------------------------------------------

class ChildAccountListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/auth/child-accounts/  — list child user accounts under this parent
    POST /api/auth/child-accounts/  — parent creates a full account for a child (13+)
    """
    serializer_class = CreateChildAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(parent=self.request.user, role=User.ROLE_CHILD)

    def perform_create(self, serializer):
        if self.request.user.role != User.ROLE_PARENT:
            raise PermissionDenied('Only parent accounts can create child accounts.')
        serializer.save()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return Response(UserSerializer(qs, many=True).data)
