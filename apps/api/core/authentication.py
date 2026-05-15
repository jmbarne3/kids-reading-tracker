from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError


class CookieOrBearerJWTAuthentication(JWTAuthentication):
    """
    Extends JWTAuthentication to accept the access token from either:
      1. An Authorization: Bearer <token> header  (native apps / API clients)
      2. An HttpOnly cookie named AUTH_COOKIE_ACCESS               (web browsers)

    The Authorization header always takes precedence over the cookie so that
    programmatic API consumers are unaffected.
    """

    def authenticate(self, request):
        # 1. Try the standard Authorization header path first.
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # 2. Fall back to the HttpOnly cookie.
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError:
            # Invalid / expired cookie — don't raise, just treat as anonymous.
            return None

        return self.get_user(validated_token), validated_token
