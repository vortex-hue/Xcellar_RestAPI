from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_ratelimit.decorators import ratelimit
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import logging

from .models import WorkflowLog, AutomationTask

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Automation'],
    summary='n8n Webhook',
    description='Webhook endpoint for n8n workflows to call Django APIs. This endpoint receives POST requests from n8n automation workflows.',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'description': 'Action to perform',
                    'example': 'test',
                },
                'data': {
                    'type': 'object',
                    'description': 'Data payload',
                    'example': {},
                },
            },
            'required': ['action'],
        }
    },
    responses={
        200: {
            'description': 'Webhook processed successfully',
            'examples': {
                'application/json': {
                    'status': 'success',
                    'message': 'Webhook received successfully',
                    'data': {},
                }
            }
        },
        400: {'description': 'Bad request - invalid payload'},
        429: {'description': 'Rate limit exceeded (100 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'Webhook Request',
            value={
                'action': 'test',
                'data': {
                    'key': 'value',
                },
            },
            request_only=True,
        ),
        OpenApiExample(
            'Webhook Response',
            value={
                'status': 'success',
                'message': 'Webhook received successfully',
                'data': {},
            },
            response_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='100/h', method='POST')
def n8n_webhook(request):
    """
    Webhook endpoint for n8n to call Django APIs.
    This endpoint receives requests from n8n workflows.
    
    POST /api/v1/automation/webhook/
    
    Expected payload:
    {
        "action": "create_order",
        "data": {...}
    }
    """
    try:
        action = request.data.get('action')
        data = request.data.get('data', {})
        
        # Log the webhook call
        logger.info(f"Received n8n webhook: {action}")
        
        # Handle different actions from n8n
        if action == 'test':
            return Response({
                'status': 'success',
                'message': 'Webhook received successfully',
                'data': data
            }, status=status.HTTP_200_OK)
        
        # Add more action handlers here as needed
        # Example:
        # elif action == 'create_order':
        #     # Process order creation from n8n
        #     pass
        
        return Response({
            'status': 'success',
            'message': f'Action {action} received',
            'data': data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing n8n webhook: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Automation'],
    summary='Get Workflow Logs',
    description='Retrieve the last 50 workflow execution logs from n8n automation.',
    responses={
        200: {
            'description': 'List of workflow logs',
            'examples': {
                'application/json': {
                    'logs': [
                        {
                            'id': 1,
                            'workflow_id': 'workflow_123',
                            'workflow_name': 'Order Processing',
                            'status': 'SUCCESS',
                            'executed_at': '2025-10-30T18:00:00Z',
                        }
                    ]
                }
            }
        },
        429: {'description': 'Rate limit exceeded (100 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'Workflow Logs Response',
            value={
                'logs': [
                    {
                        'id': 1,
                        'workflow_id': 'workflow_123',
                        'workflow_name': 'Order Processing',
                        'status': 'SUCCESS',
                        'executed_at': '2025-10-30T18:00:00Z',
                    }
                ]
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='100/h', method='GET')
def workflow_logs(request):
    """
    Get workflow execution logs.
    GET /api/v1/automation/workflows/
    """
    logs = WorkflowLog.objects.all()[:50]  # Limit to last 50 logs
    return Response({
        'logs': [
            {
                'id': log.id,
                'workflow_id': log.workflow_id,
                'workflow_name': log.workflow_name,
                'status': log.status,
                'executed_at': log.executed_at
            }
            for log in logs
        ]
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Automation'],
    summary='Get Automation Tasks',
    description='Retrieve the last 50 automation tasks triggered from Django.',
    responses={
        200: {
            'description': 'List of automation tasks',
            'examples': {
                'application/json': {
                    'tasks': [
                        {
                            'id': 1,
                            'task_type': 'ORDER_CREATED',
                            'workflow_id': 'workflow_123',
                            'status': 'SUCCESS',
                            'created_at': '2025-10-30T18:00:00Z',
                        }
                    ]
                }
            }
        },
        429: {'description': 'Rate limit exceeded (100 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'Automation Tasks Response',
            value={
                'tasks': [
                    {
                        'id': 1,
                        'task_type': 'ORDER_CREATED',
                        'workflow_id': 'workflow_123',
                        'status': 'SUCCESS',
                        'created_at': '2025-10-30T18:00:00Z',
                    }
                ]
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='100/h', method='GET')
def automation_tasks(request):
    """
    Get automation tasks.
    GET /api/v1/automation/tasks/
    """
    tasks = AutomationTask.objects.all()[:50]  # Limit to last 50 tasks
    return Response({
        'tasks': [
            {
                'id': task.id,
                'task_type': task.task_type,
                'workflow_id': task.workflow_id,
                'status': task.status,
                'created_at': task.created_at
            }
            for task in tasks
        ]
    }, status=status.HTTP_200_OK)

