from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    register_user,
    register_courier,
    user_profile,
    change_password,
    update_phone_number,
    update_profile,
    logout
)
from .password_reset.views import password_reset_request, password_reset_confirm

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout, name='logout'),
    path('register/user/', register_user, name='register_user'),
    path('register/courier/', register_courier, name='register_courier'),
    path('profile/', user_profile, name='user_profile'),
    path('profile/update/', update_profile, name='update_profile'),
    path('phone/update/', update_phone_number, name='update_phone_number'),
    path('password/change/', change_password, name='change_password'),
    path('password/reset/request/', password_reset_request, name='password_reset_request'),
    path('password/reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
]

