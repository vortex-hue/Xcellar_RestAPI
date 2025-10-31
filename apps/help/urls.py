from django.urls import path
from .views import submit_help_request, my_help_requests

app_name = 'help'

urlpatterns = [
    path('request/', submit_help_request, name='submit_help_request'),
    path('my-requests/', my_help_requests, name='my_help_requests'),
]

