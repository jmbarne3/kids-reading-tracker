from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ChildProfile, SocialAccount, User

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

STRONG_PASSWORD = 'Tr0ub4dor&3!'


def make_parent(username='parent', email='parent@example.com', password=STRONG_PASSWORD):
    return User.objects.create_user(
        username=username, email=email, password=password, role=User.ROLE_PARENT,
    )


def make_child(parent, username='child', email='child@example.com', password=STRONG_PASSWORD):
    return User.objects.create_user(
        username=username, email=email, password=password,
        role=User.ROLE_CHILD, parent=parent,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class UserModelTest(TestCase):
    def test_parent_created_with_correct_role(self):
        user = make_parent()
        self.assertEqual(user.role, User.ROLE_PARENT)
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_child_linked_to_parent(self):
        parent = make_parent()
        child = make_child(parent)
        self.assertEqual(child.role, User.ROLE_CHILD)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.child_accounts.all())

    def test_str_contains_email_and_role(self):
        user = make_parent()
        result = str(user)
        self.assertIn(user.email, result)
        self.assertIn(user.role, result)


class ChildProfileModelTest(TestCase):
    def setUp(self):
        self.parent = make_parent()

    def test_create_profile(self):
        profile = ChildProfile.objects.create(parent=self.parent, name='Alice')
        self.assertEqual(profile.name, 'Alice')
        self.assertIn(profile, self.parent.child_profiles.all())

    def test_set_and_check_pin(self):
        profile = ChildProfile.objects.create(parent=self.parent, name='Bob')
        profile.set_pin('1234')
        profile.save()
        self.assertTrue(profile.check_pin('1234'))
        self.assertFalse(profile.check_pin('9999'))

    def test_blank_pin_means_no_pin_required(self):
        profile = ChildProfile.objects.create(parent=self.parent, name='Charlie')
        self.assertEqual(profile.pin, '')

    def test_str_contains_name_and_parent_email(self):
        profile = ChildProfile.objects.create(parent=self.parent, name='Dana')
        self.assertIn('Dana', str(profile))
        self.assertIn(self.parent.email, str(profile))


class SocialAccountModelTest(TestCase):
    def setUp(self):
        self.user = make_parent()

    def test_create_google_social_account(self):
        sa = SocialAccount.objects.create(
            user=self.user,
            provider=SocialAccount.PROVIDER_GOOGLE,
            provider_user_id='google-uid-123',
            email='test@gmail.com',
        )
        self.assertEqual(sa.provider, 'google')
        self.assertIn(sa, self.user.social_accounts.all())

    def test_unique_together_prevents_duplicate_provider_uid(self):
        SocialAccount.objects.create(
            user=self.user,
            provider=SocialAccount.PROVIDER_GOOGLE,
            provider_user_id='google-uid-dup',
        )
        with self.assertRaises(IntegrityError):
            SocialAccount.objects.create(
                user=self.user,
                provider=SocialAccount.PROVIDER_GOOGLE,
                provider_user_id='google-uid-dup',
            )

    def test_same_provider_uid_for_different_providers_allowed(self):
        SocialAccount.objects.create(
            user=self.user, provider=SocialAccount.PROVIDER_GOOGLE, provider_user_id='uid-1'
        )
        # Same uid, different provider — should succeed
        SocialAccount.objects.create(
            user=self.user, provider=SocialAccount.PROVIDER_APPLE, provider_user_id='uid-1'
        )
        self.assertEqual(self.user.social_accounts.count(), 2)


# ---------------------------------------------------------------------------
# Auth API tests
# ---------------------------------------------------------------------------

class RootViewTest(APITestCase):
    def test_returns_ok(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')


class RegisterViewTest(APITestCase):
    url = '/api/auth/register/'

    def _payload(self, **overrides):
        return {
            'email': 'new@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': STRONG_PASSWORD,
            'password2': STRONG_PASSWORD,
            **overrides,
        }

    def test_successful_registration_returns_201_with_tokens(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['email'], 'new@example.com')
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_new_account_has_parent_role(self):
        self.client.post(self.url, self._payload(), format='json')
        user = User.objects.get(email='new@example.com')
        self.assertEqual(user.role, User.ROLE_PARENT)

    def test_password_mismatch_rejected(self):
        response = self.client.post(self.url, self._payload(password2='wrong'), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_rejected(self):
        make_parent(email='new@example.com', username='existing')
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_rejected(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(APITestCase):
    url = '/api/auth/login/'

    def setUp(self):
        self.user = make_parent(email='login@example.com')

    def test_correct_credentials_return_tokens(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': STRONG_PASSWORD}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['email'], 'login@example.com')

    def test_wrong_password_rejected(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'wrongpass'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_email_rejected(self):
        response = self.client.post(
            self.url, {'email': 'nobody@example.com', 'password': STRONG_PASSWORD}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': STRONG_PASSWORD}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutViewTest(APITestCase):
    url = '/api/auth/logout/'

    def setUp(self):
        self.user = make_parent()

    def test_authenticated_logout_succeeds(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {'refresh': str(refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_logout_rejected(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshViewTest(APITestCase):
    url = '/api/auth/token/refresh/'

    def setUp(self):
        self.user = make_parent()

    def test_valid_refresh_token_returns_new_access(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {'refresh': str(refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_missing_refresh_token_rejected(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTest(APITestCase):
    url = '/api/auth/me/'

    def setUp(self):
        self.user = make_parent()

    def test_authenticated_returns_user_data(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['role'], User.ROLE_PARENT)

    def test_unauthenticated_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChildProfileAPITest(APITestCase):
    list_url = '/api/auth/child-profiles/'

    def setUp(self):
        self.parent = make_parent()
        self.client.force_authenticate(self.parent)

    def test_list_empty_for_new_parent(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_parent_can_create_profile(self):
        response = self.client.post(self.list_url, {'name': 'Alice'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Alice')
        self.assertEqual(ChildProfile.objects.filter(parent=self.parent).count(), 1)

    def test_list_shows_only_own_profiles(self):
        ChildProfile.objects.create(parent=self.parent, name='Mine')
        other = make_parent(username='other', email='other@example.com')
        ChildProfile.objects.create(parent=other, name='Theirs')
        response = self.client.get(self.list_url)
        names = [p['name'] for p in response.data]
        self.assertIn('Mine', names)
        self.assertNotIn('Theirs', names)

    def test_child_user_cannot_create_profile(self):
        child = make_child(self.parent, username='kid', email='kid@example.com')
        self.client.force_authenticate(child)
        response = self.client.post(self.list_url, {'name': 'NotAllowed'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_parent_can_update_profile(self):
        profile = ChildProfile.objects.create(parent=self.parent, name='Old')
        response = self.client.patch(
            f'{self.list_url}{profile.pk}/', {'name': 'New'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New')

    def test_parent_can_delete_profile(self):
        profile = ChildProfile.objects.create(parent=self.parent, name='ToDelete')
        response = self.client.delete(f'{self.list_url}{profile.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChildProfile.objects.filter(pk=profile.pk).exists())

    def test_unauthenticated_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChildAccountAPITest(APITestCase):
    url = '/api/auth/child-accounts/'

    def setUp(self):
        self.parent = make_parent()
        self.client.force_authenticate(self.parent)

    def test_parent_can_create_child_account(self):
        response = self.client.post(self.url, {
            'email': 'teen@example.com',
            'username': 'teenager',
            'first_name': 'Teen',
            'last_name': 'Ager',
            'password': STRONG_PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        child = User.objects.get(email='teen@example.com')
        self.assertEqual(child.role, User.ROLE_CHILD)
        self.assertEqual(child.parent, self.parent)

    def test_child_account_created_without_password_gets_unusable_password(self):
        self.client.post(self.url, {
            'email': 'nopw@example.com',
            'username': 'nopw',
        }, format='json')
        child = User.objects.get(email='nopw@example.com')
        self.assertFalse(child.has_usable_password())

    def test_child_user_cannot_create_child_account(self):
        child = make_child(self.parent, username='c', email='c@example.com')
        self.client.force_authenticate(child)
        response = self.client.post(self.url, {
            'email': 'forbidden@example.com', 'username': 'forbidden',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_own_child_accounts_only(self):
        make_child(self.parent, username='kid1', email='kid1@example.com')
        other_parent = make_parent(username='op', email='op@example.com')
        make_child(other_parent, username='kid2', email='kid2@example.com')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'kid1@example.com')


class SocialAuthUnconfiguredTest(APITestCase):
    """When GOOGLE_CLIENT_ID / APPLE_APP_ID are not set, endpoints return 503."""

    def test_google_returns_503(self):
        response = self.client.post(
            '/api/auth/google/', {'id_token': 'fake-token'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_apple_returns_503(self):
        response = self.client.post(
            '/api/auth/apple/', {'identity_token': 'fake-token'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
