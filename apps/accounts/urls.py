from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    register_user,
    register_courier,
    user_profile
)

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('register/user/', register_user, name='register_user'),
    path('register/courier/', register_courier, name='register_courier'),
    path('profile/', user_profile, name='user_profile'),
]

