from django.contrib import admin
from django.urls import path
from apps.views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserDetailView,
    UserListView,
    UserLoginView,
    UserProfileUpdateView,
    UserRegisterView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('auth/login/', UserLoginView.as_view(), name='auth-login'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('token/', UserLoginView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('gateway-docs/', SpectacularSwaggerView.as_view(url='/user/api/v1/schema/'), name='gateway-swagger-ui'),
]
