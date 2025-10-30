from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.core.permissions import IsCourier


@extend_schema(
    tags=['Couriers'],
    summary='Courier Dashboard',
    description='Get courier dashboard information. Available only for couriers (COURIER type).',
    responses={
        200: {
            'description': 'Courier dashboard data',
            'examples': {
                'application/json': {
                    'message': 'Courier dashboard',
                    'courier': 'courier@example.com',
                }
            }
        },
        401: {'description': 'Authentication required'},
        403: {'description': 'Forbidden - Only COURIER type allowed'},
        429: {'description': 'Rate limit exceeded (100 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'Courier Dashboard Response',
            value={
                'message': 'Courier dashboard',
                'courier': 'courier@example.com',
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([IsCourier])
@ratelimit(key='user', rate='100/h', method='GET')
def courier_dashboard(request):
    """
    Courier dashboard endpoint.
    GET /api/v1/couriers/dashboard/
    """
    return Response({
        'message': 'Courier dashboard',
        'courier': request.user.email
    }, status=status.HTTP_200_OK)


app_name = 'couriers'

urlpatterns = [
    path('dashboard/', courier_dashboard, name='courier_dashboard'),
]

