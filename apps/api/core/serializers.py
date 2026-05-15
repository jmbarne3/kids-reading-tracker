from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ChildProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'date_of_birth', 'avatar_url',
        )
        read_only_fields = ('id',)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password', 'password2', 'date_of_birth')

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        # Public self-registration always creates a parent account.
        # Child accounts (13+) are created by a parent via a separate endpoint.
        return User.objects.create_user(
            username=validated_data.get('username') or validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            date_of_birth=validated_data.get('date_of_birth'),
            role=User.ROLE_PARENT,
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            user_obj = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials.')

        user = authenticate(username=user_obj.username, password=attrs['password'])
        if user is None:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')

        attrs['user'] = user
        return attrs


class ChildProfileSerializer(serializers.ModelSerializer):
    # PIN is write-only; it is stored hashed and never returned.
    pin = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ChildProfile
        fields = ('id', 'name', 'avatar_url', 'date_of_birth', 'pin', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        raw_pin = validated_data.pop('pin', None)
        profile = ChildProfile(**validated_data)
        if raw_pin:
            profile.set_pin(raw_pin)
        profile.save()
        return profile

    def update(self, instance, validated_data):
        raw_pin = validated_data.pop('pin', None)
        if raw_pin:
            instance.set_pin(raw_pin)
        return super().update(instance, validated_data)


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class AppleAuthSerializer(serializers.Serializer):
    identity_token = serializers.CharField()
    # Apple only sends name data on the very first authorization; it is optional.
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')


class CreateChildAccountSerializer(serializers.ModelSerializer):
    """Used by a parent to create a full child user account (age 13+)."""

    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password', 'date_of_birth')

    def create(self, validated_data):
        parent = self.context['request'].user
        password = validated_data.pop('password', None)
        user = User(
            username=validated_data.get('username') or validated_data.get('email', ''),
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            date_of_birth=validated_data.get('date_of_birth'),
            role=User.ROLE_CHILD,
            parent=parent,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user
