from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core import signing
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class InvalidCredentialsException(APIException):
    status_code = 401
    default_detail = 'Credenciales invalidas.'
    default_code = 'authentication_failed'


def validate_user_password(value):
    try:
        validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc

    has_upper = any(char.isupper() for char in value)
    has_lower = any(char.islower() for char in value)
    has_digit = any(char.isdigit() for char in value)
    has_special = any(not char.isalnum() for char in value)
    if not (has_upper and has_lower and has_digit and has_special):
        raise serializers.ValidationError(
            'La password debe incluir mayuscula, minuscula, numero y caracter especial.'
        )
    return value


class UserRegisterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(
        min_length=3,
        max_length=30,
        error_messages={'required': 'El username es obligatorio.', 'blank': 'El username es obligatorio.'},
    )
    email = serializers.EmailField(error_messages={'unique': 'Este correo ya esta registrado.'})
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.RegexField(
        regex=r'^\+?[1-9]\d{7,14}$',
        source='phone_number',
        error_messages={
            'required': 'El telefono es obligatorio.',
            'blank': 'El telefono es obligatorio.',
            'invalid': 'Formato de telefono invalido. Ejemplo: +573001112233',
        },
    )
    role = serializers.ChoiceField(choices=User.Role.choices, required=False, default=User.Role.B2C)
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'phone',
            'role',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Este nombre de usuario ya existe.')
        return value

    def validate_password(self, value):
        return validate_user_password(value)

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.setdefault('role', User.Role.B2C)
        validated_data['is_staff'] = validated_data.get('role') == User.Role.ADMIN
        user = User(**validated_data)
        user.set_password(password)
        try:
            user.save()
        except IntegrityError as exc:
            message = str(exc).lower()
            if 'username' in message:
                raise serializers.ValidationError({'username': ['Este nombre de usuario ya existe.']}) from exc
            raise serializers.ValidationError({'email': ['Este correo ya esta registrado.']}) from exc
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar campos personalizados al token
        token['email'] = user.email
        token['username'] = user.username or ''
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['role'] = user.role
        
        return token

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError({'detail': 'Email y password son requeridos.'})

        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )
        if not user:
            raise serializers.ValidationError({'detail': 'Credenciales invalidas.'})

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class UserAuthLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=True, allow_blank=False, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')

        if not username and not email:
            raise serializers.ValidationError({'detail': 'Debe enviar username o email.'})

        user = None
        if username:
            user = User.objects.filter(username__iexact=username).first()
        elif email:
            user = User.objects.filter(email__iexact=email).first()

        if not user or not user.check_password(password) or not user.is_active:
            raise InvalidCredentialsException()

        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    phone = serializers.CharField(source='phone_number', required=False, allow_blank=True)
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'bio',
            'phone',
            'role',
        )
        read_only_fields = ('id', 'username', 'email', 'role')


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source='phone_number', required=False, allow_blank=True)
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'bio',
            'phone',
        )
        read_only_fields = ('email',)

    def validate(self, attrs):
        attrs.pop('email', None)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_new_password(self, value):
        return validate_user_password(value)

    def validate(self, attrs):
        signed_token = attrs.get('token')

        try:
            token_payload = signing.loads(
                signed_token,
                salt='password-reset-confirm',
                max_age=settings.PASSWORD_RESET_TIMEOUT,
            )
            user_id = token_payload['uid']
            raw_token = token_payload['token']
            user = User.objects.get(pk=user_id)
        except (signing.BadSignature, signing.SignatureExpired, KeyError, User.DoesNotExist) as exc:
            raise serializers.ValidationError({'token': ['El enlace de recuperacion no es valido.']}) from exc

        if not PasswordResetTokenGenerator().check_token(user, raw_token):
            raise serializers.ValidationError({'token': ['El token es invalido o ha expirado.']})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class StandardResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField()
    status = serializers.IntegerField()


class PasswordResetEmailPreviewSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_url = serializers.CharField()


def generate_password_reset_token(user):
    raw_token = PasswordResetTokenGenerator().make_token(user)
    signed_token = signing.dumps(
        {'uid': str(user.pk), 'token': raw_token},
        salt='password-reset-confirm',
    )
    return signed_token


def build_password_reset_url(token):
    base_url = settings.PASSWORD_RESET_CONFIRM_URL.rstrip('/')
    return f'{base_url}?token={token}'
