import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    EmailTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    StandardResponseSerializer,
    UserAuthLoginSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserRegisterSerializer,
    build_password_reset_url,
    generate_password_reset_token,
)
from .models import User
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)

from core.api_responses import success_response

logger = logging.getLogger(__name__)


class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserRegisterSerializer,
        responses={201: StandardResponseSerializer, 400: StandardResponseSerializer, 401: StandardResponseSerializer},
        parameters=[
            OpenApiParameter(
                name='x-api-key',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description='API key requerida por el gateway.',
            ),
            OpenApiParameter(
                name='x-origin',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description='Origen requerido por el gateway.',
            ),
        ],
    )
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_data = UserRegisterSerializer(user).data
        return success_response(
            'Usuario registrado exitosamente.',
            data=response_data,
            status_code=status.HTTP_201_CREATED,
        )


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserAuthLoginSerializer,
        responses={
            200: OpenApiResponse(response=StandardResponseSerializer, description='Login exitoso'),
            400: OpenApiResponse(response=StandardResponseSerializer, description='Datos de entrada invalidos'),
            401: OpenApiResponse(response=StandardResponseSerializer, description='Credenciales invalidas'),
        },
        examples=[
            OpenApiExample(
                'Request con username',
                value={'username': 'luismorales', 'password': 'mi_password_seguro'},
                request_only=True,
            ),
            OpenApiExample(
                'Request con email',
                value={'email': 'luis@luis.com', 'password': 'mi_password_seguro'},
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta 200',
                value={
                    'success': True,
                    'message': 'Login exitoso.',
                    'data': {
                        'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                        'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    },
                    'status': 200,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Respuesta 401',
                value={
                    'success': False,
                    'message': 'Credenciales invalidas.',
                    'data': {'detail': 'Credenciales invalidas.'},
                    'status': 401,
                },
                response_only=True,
                status_codes=['401'],
            ),
        ],
    )
    def post(self, request):
        serializer = UserAuthLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Usar el serializador personalizado para generar tokens con claims adicionales
        refresh = EmailTokenObtainPairSerializer.get_token(user)
        
        return success_response(
            'Login exitoso.',
            data={
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status_code=status.HTTP_200_OK,
        )


class UserProfileUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UserProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(response=StandardResponseSerializer, description='Perfil actualizado exitosamente'),
            401: OpenApiResponse(response=StandardResponseSerializer, description='Token invalido o ausente'),
        },
        examples=[
            OpenApiExample(
                'Request de actualizacion parcial',
                value={
                    'first_name': 'Luis',
                    'last_name': 'Morales',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta 200',
                value={
                    'success': True,
                    'message': 'Perfil actualizado exitosamente.',
                    'data': {
                        'username': 'luismorales',
                        'email': 'luis@luis.com',
                        'first_name': 'Luis',
                        'last_name': 'Morales',
                        'phone': '+50255555555',
                        'role': 'b2c',
                    },
                    'status': 200,
                },
                response_only=True,
                status_codes=['200'],
            ),
        ],
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            'Perfil actualizado exitosamente.',
            data=UserProfileSerializer(request.user).data,
            status_code=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(response=StandardResponseSerializer, description='Solicitud procesada'),
        },
        examples=[
            OpenApiExample(
                'Request password reset',
                value={'email': 'juan@example.com'},
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta 200',
                value={
                    'success': True,
                    'message': 'Se ha enviado un correo con las instrucciones.',
                    'data': [],
                    'status': 200,
                },
                response_only=True,
                status_codes=['200'],
            ),
        ],
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            token = generate_password_reset_token(user)
            reset_url = build_password_reset_url(token)
            logger.info(
                'PASSWORD_RESET_DEBUG email=%s token=%s reset_url=%s',
                user.email,
                token,
                reset_url,
            )
            send_mail(
                subject='Recuperacion de contrasena',
                message=(
                    'Recibimos una solicitud para restablecer tu contrasena.\n\n'
                    f'Token: {token}\n'
                    f'Usa este enlace para continuar: {reset_url}\n\n'
                    'Si no realizaste esta solicitud, puedes ignorar este correo.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return success_response(
            'Se ha enviado un correo con las instrucciones.',
            status_code=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(response=StandardResponseSerializer, description='Password actualizada'),
            400: OpenApiResponse(response=StandardResponseSerializer, description='Token invalido o expirado'),
        },
        examples=[
            OpenApiExample(
                'Confirmar reset',
                value={
                    'token': 'eyJ1aWQiOiIxIiwidG9rZW4iOiJiNGExYzg...token_firmado',
                    'new_password': 'NuevoPassword123!',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta 200',
                value={
                    'success': True,
                    'message': 'La contrasena ha sido actualizada exitosamente.',
                    'data': [],
                    'status': 200,
                },
                response_only=True,
                status_codes=['200'],
            ),
        ],
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            'La contrasena ha sido actualizada exitosamente.',
            status_code=status.HTTP_200_OK,
        )


class UserListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Solo admins pueden listar usuarios
        if request.user.role != User.Role.ADMIN:
            return success_response(
                'No tienes permisos para ver esta información.',
                data=[],
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        users = User.objects.all().order_by('-date_joined')
        serializer = UserProfileSerializer(users, many=True)
        return success_response(
            'Usuarios obtenidos exitosamente.',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class UserDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        # Solo admins pueden actualizar otros usuarios
        if request.user.role != User.Role.ADMIN:
            return success_response(
                'No tienes permisos para realizar esta acción.',
                data={},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return success_response(
                'Usuario no encontrado.',
                data={},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Permitir actualizar role
        if 'role' in request.data:
            if request.data['role'] not in [User.Role.ADMIN, User.Role.B2B, User.Role.B2C]:
                return success_response(
                    'Rol inválido.',
                    data={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            user.role = request.data['role']
            user.is_staff = request.data['role'] == User.Role.ADMIN
            user.save()
        
        return success_response(
            'Usuario actualizado exitosamente.',
            data=UserProfileSerializer(user).data,
            status_code=status.HTTP_200_OK,
        )
