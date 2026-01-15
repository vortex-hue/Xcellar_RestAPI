from django.urls import path
from .views import verify_account, list_banks, list_states

app_name = 'core'

urlpatterns = [
    path('verify-account/', verify_account, name='verify_account'),
    path('banks/', list_banks, name='list_banks'),
    path('states/', list_states, name='list_states'),
]

