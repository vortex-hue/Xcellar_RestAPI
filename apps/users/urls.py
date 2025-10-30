from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.core.permissions import IsUser


@extend_schema(
    tags=['Users'],
    summary='User Dashboard',
    description='Get user dashboard information. Available only for regular customers (USER type).',
    responses={
        200: {
            'description': 'User dashboard data',
            'examples': {
                'application/json': {
                    'message': 'User dashboard',
                    'user': 'user@example.com',
                }
            }
        },
        401: {'description': 'Authentication required'},
        403: {'description': 'Forbidden - Only USER type allowed'},
        429: {'description': 'Rate limit exceeded (100 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'User Dashboard Response',
            value={
                'message': 'User dashboard',
                'user': 'user@example.com',
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([IsUser])
@ratelimit(key='user', rate='100/h', method='GET')
def user_dashboard(request):
    """
    User dashboard endpoint.
    GET /api/v1/users/dashboard/
    """
    return Response({
        'message': 'User dashboard',
        'user': request.user.email
    }, status=status.HTTP_200_OK)


app_name = 'users'

urlpatterns = [
    path('dashboard/', user_dashboard, name='user_dashboard'),
]

