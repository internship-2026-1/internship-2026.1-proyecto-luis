from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import serializers
from .serializers import (
    UserAuthLoginSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserRegisterSerializer,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)


class TokenPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class ErrorDetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()

class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserRegisterSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
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
        if serializer.is_valid():
            user = serializer.save()
            response_data = UserRegisterSerializer(user).data
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserAuthLoginSerializer,
        responses={
            200: OpenApiResponse(response=TokenPairResponseSerializer, description='Login exitoso'),
            400: OpenApiResponse(response=ErrorDetailResponseSerializer, description='Datos de entrada invalidos'),
            401: OpenApiResponse(response=ErrorDetailResponseSerializer, description='Credenciales invalidas'),
        },
        examples=[
            OpenApiExample(
                'Request con username',
                value={'username': 'juan_perez', 'password': 'mi_password_seguro'},
                request_only=True,
            ),
            OpenApiExample(
                'Request con email',
                value={'email': 'juan@empresa.com', 'password': 'mi_password_seguro'},
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta 200',
                value={
                    'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Respuesta 401',
                value={'detail': 'Credenciales invalidas.'},
                response_only=True,
                status_codes=['401'],
            ),
        ],
    )
    def post(self, request):
        serializer = UserAuthLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class UserProfileUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UserProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UserProfileSerializer, description='Perfil actualizado exitosamente'),
            401: OpenApiResponse(response=ErrorDetailResponseSerializer, description='Token invalido o ausente'),
        },
        examples=[
            OpenApiExample(
                'Request de actualizacion parcial',
                value={
                    'first_name': 'Juan',
                    'last_name': 'Perez Actualizado',
                    'bio': 'Desarrollador backend apasionado por APIs.',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Respuesta 200',
                value={
                    'username': 'juan_perez',
                    'email': 'juan@example.com',
                    'first_name': 'Juan',
                    'last_name': 'Perez Actualizado',
                    'bio': 'Desarrollador backend apasionado por APIs.',
                    'phone': '+50255555555',
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
        return Response(UserProfileSerializer(request.user).data, status=status.HTTP_200_OK)
