from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class InvalidCredentialsException(APIException):
    status_code = 401
    default_detail = 'Credenciales invalidas.'
    default_code = 'authentication_failed'

class UserRegisterSerializer(serializers.ModelSerializer):
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
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Este nombre de usuario ya existe.')
        return value

    def validate_password(self, value):
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

    def create(self, validated_data):
        password = validated_data.pop('password')
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
    phone = serializers.CharField(source='phone_number', required=False, allow_blank=True)
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'bio',
            'phone',
        )
        read_only_fields = ('username', 'email')


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
