from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiExample
import logging

from django.conf import settings
from apps.automation.services.n8n_client import N8nClient
from .models import HelpRequest
from .serializers import HelpRequestSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Help'],
    summary='Submit Help Request',
    description='Submit a help/support request. The request will be saved to the database and sent to the support team via n8n workflow. If authenticated, user information will be auto-filled.',
    request=HelpRequestSerializer,
    responses={
        201: {
            'description': 'Help request submitted successfully',
            'examples': {
                'application/json': {
                    'message': 'Help request submitted successfully',
                    'request_id': 1,
                    'status': 'PENDING',
                }
            }
        },
        400: {'description': 'Validation error'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Submit Help Request (Authenticated)',
            value={
                'subject': 'Payment Issue',
                'message': 'I am having trouble processing my payment. The transaction keeps failing.',
                'category': 'PAYMENT',
                'priority': 'HIGH',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Submit Help Request (Anonymous)',
            value={
                'user_email': 'user@example.com',
                'user_name': 'John Doe',
                'phone_number': '+1234567890',
                'subject': 'Account Problem',
                'message': 'I cannot log into my account. Please help.',
                'category': 'ACCOUNT',
                'priority': 'NORMAL',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Help Request Response',
            value={
                'message': 'Help request submitted successfully',
                'request_id': 1,
                'status': 'PENDING',
            },
            response_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow both authenticated and anonymous users
@ratelimit(key='ip', rate='5/h', method='POST')  # Limit to 5 requests per hour per IP
def submit_help_request(request):
    """
    Submit a help/support request.
    POST /api/v1/help/request/
    
    If user is authenticated, user information will be auto-filled.
    """
    serializer = HelpRequestSerializer(data=request.data, context={'request': request})
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # Create help request
            help_request = serializer.save()
            
            # Prepare data for n8n workflow
            n8n_data = {
                'request_id': help_request.id,
                'user_email': help_request.user_email,
                'user_name': help_request.get_user_display_name(),
                'phone_number': help_request.phone_number or '',
                'subject': help_request.subject,
                'message': help_request.message,
                'category': help_request.category,
                'category_display': help_request.get_category_display(),
                'priority': help_request.priority,
                'priority_display': help_request.get_priority_display(),
                'status': help_request.status,
                'created_at': help_request.created_at.isoformat(),
                'is_authenticated_user': help_request.user is not None,
            }
            
            # If user is authenticated, add user info
            if help_request.user:
                n8n_data['user_id'] = help_request.user.id
                n8n_data['user_type'] = help_request.user.user_type
            
            # Trigger n8n workflow
            n8n_client = N8nClient()
            n8n_webhook_url = getattr(settings, 'N8N_HELP_WEBHOOK_URL', None)
            
            if n8n_webhook_url:
                try:
                    response = n8n_client.trigger_workflow_webhook(n8n_webhook_url, n8n_data)
                    
                    if response is not None:
                        help_request.n8n_workflow_triggered = True
                        help_request.n8n_workflow_id = n8n_webhook_url
                        help_request.save(update_fields=['n8n_workflow_triggered', 'n8n_workflow_id'])
                        logger.info(f"Successfully triggered n8n workflow for help request {help_request.id}")
                    else:
                        logger.warning(f"Failed to trigger n8n workflow for help request {help_request.id}")
                except Exception as e:
                    logger.error(f"Error triggering n8n workflow for help request {help_request.id}: {e}")
                    # Don't fail the request if n8n fails - still save the request
            else:
                logger.warning("N8N_HELP_WEBHOOK_URL not configured. Help request saved but n8n workflow not triggered.")
        
        return Response(
            {
                'message': 'Help request submitted successfully',
                'request_id': help_request.id,
                'status': help_request.status,
            },
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        logger.error(f"Error creating help request: {e}")
        return Response(
            {'error': 'Failed to submit help request. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Help'],
    summary='Get My Help Requests',
    description='Retrieve help requests submitted by the authenticated user. Requires authentication.',
    responses={
        200: {
            'description': 'List of user\'s help requests',
            'examples': {
                'application/json': {
                    'requests': [
                        {
                            'id': 1,
                            'subject': 'Payment Issue',
                            'status': 'PENDING',
                            'category': 'PAYMENT',
                            'created_at': '2025-10-30T18:00:00Z',
                        }
                    ]
                }
            }
        },
        401: {'description': 'Authentication required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='100/h', method='GET')
def my_help_requests(request):
    """
    Get help requests submitted by the authenticated user.
    GET /api/v1/help/my-requests/
    """
    help_requests = HelpRequest.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    return Response(
        {
            'requests': [
                {
                    'id': req.id,
                    'subject': req.subject,
                    'message': req.message[:200] + '...' if len(req.message) > 200 else req.message,
                    'category': req.category,
                    'category_display': req.get_category_display(),
                    'priority': req.priority,
                    'priority_display': req.get_priority_display(),
                    'status': req.status,
                    'status_display': req.get_status_display(),
                    'created_at': req.created_at.isoformat(),
                    'updated_at': req.updated_at.isoformat(),
                }
                for req in help_requests
            ],
            'count': help_requests.count(),
        },
        status=status.HTTP_200_OK
    )

