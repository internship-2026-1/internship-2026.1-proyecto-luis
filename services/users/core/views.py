from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegisterSerializer
from rest_framework.permissions import AllowAny

# Este archivo ha sido movido a apps/views.py

class HelloWorldView(APIView):
    def get(self, request):
        return Response({"message": "Hello, world!"}, status=status.HTTP_200_OK)

class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'message': 'Usuario registrado exitosamente.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)