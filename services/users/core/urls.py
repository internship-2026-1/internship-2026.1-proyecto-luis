from django.contrib import admin
from django.urls import path
from apps.views import UserLoginView, UserRegisterView  # Importar desde apps
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('token/', UserLoginView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('gateway-docs/', SpectacularSwaggerView.as_view(url='/user/api/v1/schema/'), name='gateway-swagger-ui'),
]