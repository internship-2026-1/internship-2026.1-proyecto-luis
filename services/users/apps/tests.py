from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User
from .serializers import generate_password_reset_token


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PASSWORD_RESET_CONFIRM_URL='http://frontend.test/reset-password',
)
class UserApiTests(APITestCase):
    def test_register_assigns_default_b2c_role(self):
        response = self.client.post(
            reverse('user-register'),
            data={
                'username': 'maria_b2c',
                'email': 'maria@example.com',
                'password': 'Password123!',
                'first_name': 'Maria',
                'last_name': 'Lopez',
                'phone': '+50255556666',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['role'], User.Role.B2C)
        self.assertEqual(User.objects.get(email='maria@example.com').role, User.Role.B2C)

    def test_register_persists_assigned_role(self):
        response = self.client.post(
            reverse('user-register'),
            data={
                'username': 'empresa_b2b',
                'email': 'empresa@example.com',
                'password': 'Password123!',
                'first_name': 'Empresa',
                'last_name': 'Cliente',
                'phone': '+50255557777',
                'role': User.Role.B2B,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['role'], User.Role.B2B)
        self.assertEqual(User.objects.get(email='empresa@example.com').role, User.Role.B2B)

    def test_password_reset_request_and_confirm(self):
        user = User.objects.create_user(
            email='juan@example.com',
            password='Password123!',
            username='juan_reset',
            first_name='Juan',
            last_name='Perez',
            phone_number='+50255558888',
        )

        request_response = self.client.post(
            reverse('auth-password-reset'),
            data={'email': user.email},
            format='json',
        )

        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        self.assertEqual(request_response.data['message'], 'Se ha enviado un correo con las instrucciones.')
        self.assertEqual(len(mail.outbox), 1)

        token = generate_password_reset_token(user)
        confirm_response = self.client.post(
            reverse('auth-password-reset-confirm'),
            data={
                'token': token,
                'new_password': 'NuevoPassword123!',
            },
            format='json',
        )

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertTrue(confirm_response.data['success'])
        self.assertIn(f'Token: {token}', mail.outbox[0].body)
        self.assertNotIn('UID:', mail.outbox[0].body)
        self.assertIn(f'?token={token}', mail.outbox[0].body)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NuevoPassword123!'))
