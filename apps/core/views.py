from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.core.response import success_response, error_response, validation_error_response
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import logging

from apps.core.services.paystack_account_verification import PaystackAccountVerification

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Core'],
    summary='Get Nigerian Banks List',
    description='Get a list of all Nigerian banks with their codes and names. Users can select a bank from this list to get the bank code for account verification.',
    responses={
        200: {
            'description': 'List of banks',
            'examples': {
                'application/json': {
                    'status': True,
                    'banks': [
                        {'code': '044', 'name': 'Access Bank'},
                        {'code': '050', 'name': 'Ecobank Nigeria'},
                        {'code': '011', 'name': 'First Bank of Nigeria'},
                    ]
                }
            }
        },
        401: {'description': 'Authentication required'},
    },
    examples=[
        OpenApiExample(
            'Banks List Response',
            value={
                'status': True,
                'banks': [
                    {'code': '044', 'name': 'Access Bank'},
                    {'code': '050', 'name': 'Ecobank Nigeria'},
                    {'code': '011', 'name': 'First Bank of Nigeria'},
                    {'code': '214', 'name': 'First City Monument Bank'},
                    {'code': '058', 'name': 'Guaranty Trust Bank'},
                ],
                'count': 5
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint - banks list is public info
# Rate limit removed to prevent 403 errors behind load balancer
def list_banks(request):
    """
    Get list of Nigerian banks.
    GET /api/v1/core/banks/
    
    Returns list of banks with code and name for bank selection.
    """
    try:
        verification_service = PaystackAccountVerification()
        banks = verification_service.get_banks()
        
        # Format response to match expected structure
        formatted_banks = []
        for bank in banks:
            if isinstance(bank, dict):
                # Handle both local JSON format and Paystack API format
                bank_code = bank.get('code') or bank.get('id') or ''
                bank_name = bank.get('name') or ''
                bank_slug = bank.get('slug') or ''
                
                # Skip if no code or name
                if not bank_code and not bank_name:
                    continue
                
                formatted_banks.append({
                    'code': str(bank_code),
                    'name': bank_name,
                    'slug': bank_slug,
                })
        
        # Sort banks by name for better UX
        formatted_banks.sort(key=lambda x: x['name'].lower())
        
        return success_response(
            data={'banks': formatted_banks, 'count': len(formatted_banks)},
            message='Banks retrieved successfully'
        )
        
    except Exception as e:
        logger.error(f"Error fetching banks: {e}", exc_info=True)
        return error_response('Failed to fetch banks list', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Core'],
    summary='Verify Bank Account',
    description='Verify bank account details using Paystack account resolution API. You can provide either bank_code or bank_name. If bank_name is provided, it will be resolved to bank_code automatically.',
    parameters=[
        OpenApiParameter(
            name='account_number',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Bank account number',
            required=True,
        ),
        OpenApiParameter(
            name='bank_code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Bank code (use this if you have the bank code)',
            required=False,
        ),
        OpenApiParameter(
            name='bank_name',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Bank name (use this if you want to search by name instead of code)',
            required=False,
        ),
    ],
    responses={
        200: {
            'description': 'Account resolved successfully',
            'examples': {
                'application/json': {
                    'status': True,
                    'message': 'Account number resolved',
                    'data': {
                        'account_number': '8115333313',
                        'account_name': 'PETER BENJAMIN ANI',
                        'bank_id': 171,
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request or account not found',
            'examples': {
                'application/json': {
                    'status': False,
                    'message': 'Account resolution failed',
                }
            }
        },
        401: {'description': 'Authentication required'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Verify Account Request (with bank_code)',
            value={
                'account_number': '8115333313',
                'bank_code': '044',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Verify Account Request (with bank_name)',
            value={
                'account_number': '8115333313',
                'bank_name': 'Access Bank',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Verify Account Response',
            value={
                'status': True,
                'message': 'Account number resolved',
                'data': {
                    'account_number': '8115333313',
                    'account_name': 'PETER BENJAMIN ANI',
                    'bank_id': 171,
                }
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# Rate limit removed to prevent 403 errors
def verify_account(request):
    """
    Verify bank account details.
    GET /api/v1/core/verify-account/?account_number=8115333313&bank_code=044
    OR
    GET /api/v1/core/verify-account/?account_number=8115333313&bank_name=Access Bank
    
    This endpoint calls Paystack's bank resolution API to verify account details.
    You can provide either bank_code or bank_name. If bank_name is provided, it will be resolved to bank_code automatically.
    """
    account_number = request.query_params.get('account_number')
    bank_code = request.query_params.get('bank_code')
    bank_name = request.query_params.get('bank_name')
    
    if not account_number:
        return error_response('account_number is required', status_code=status.HTTP_400_BAD_REQUEST)
    
    # If bank_code is not provided, try to resolve from bank_name
    if not bank_code:
        if not bank_name:
            return error_response('Either bank_code or bank_name is required', status_code=status.HTTP_400_BAD_REQUEST)
        
        # Resolve bank_code from bank_name
        verification_service = PaystackAccountVerification()
        bank_code = verification_service.get_bank_code_by_name(bank_name)
        
        if not bank_code:
            return error_response(f'Bank "{bank_name}" not found. Please use the /api/v1/core/banks/ endpoint to get available banks.', status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification_service = PaystackAccountVerification()
        response = verification_service.resolve_account(account_number, bank_code)
        
        if response.get('status'):
            # Paystack returns response with status: true and data
            return success_response(
                data=response.get('data', {}),
                message='Account verified successfully'
            )
        else:
            # Paystack returns error response with status: false
            error_msg = response.get('message', 'Failed to verify account')
            return error_response(error_msg, status_code=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error verifying account: {e}", exc_info=True)
        return error_response('Failed to verify account. Please try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Core'],
    summary='Get Nigerian States',
    description='Get a list of all 36 states in Nigeria plus FCT.',
    responses={
        200: {
            'description': 'List of states',
            'examples': {
                'application/json': {
                    'status': True,
                    'states': [
                        'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 
                        'Bayelsa', 'Benue', 'Borno', 'Cross River', 'Delta', 
                        'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Gombe', 'Imo', 
                        'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 
                        'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 
                        'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 
                        'Sokoto', 'Taraba', 'Yobe', 'Zamfara', 'Federal Capital Territory'
                    ],
                    'count': 37
                }
            }
        },
        401: {'description': 'Authentication required'},
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_states(request):
    """
    Get list of Nigerian states.
    GET /api/v1/core/states/
    """
    states = [
        'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 
        'Bayelsa', 'Benue', 'Borno', 'Cross River', 'Delta', 
        'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Gombe', 'Imo', 
        'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 
        'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 
        'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 
        'Sokoto', 'Taraba', 'Yobe', 'Zamfara', 'Federal Capital Territory'
    ]
    return success_response(
        data={'states': states, 'count': len(states)},
        message='States retrieved successfully'
    )

