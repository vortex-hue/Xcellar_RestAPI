from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.response import success_response, error_response, created_response, validation_error_response, not_found_response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction as db_transaction
from django.db import IntegrityError
from django.db.models import Q, F
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from decimal import Decimal
import uuid
import logging

from apps.payments.models import Transaction, Notification, DedicatedVirtualAccount, TransferRecipient
from apps.payments.serializers import (
    TransactionSerializer,
    DedicatedVirtualAccountSerializer,
    TransferRecipientSerializer,
    CreateTransferRecipientSerializer,
    CreateTransferSerializer,
    FinalizeTransferSerializer,
    NotificationSerializer,
)
from apps.payments.services.paystack_client import PaystackClient
from apps.core.services.paystack_account_verification import PaystackAccountVerification
from apps.core.utils import get_user_balance, deduct_balance, add_balance

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Payments'],
    summary='Get Balance',
    description='Get current account balance for authenticated user.',
    responses={
        200: {
            'description': 'Balance retrieved successfully',
            'examples': {
                'application/json': {
                    'balance': '5000.00',
                    'currency': 'NGN',
                }
            }
        },
        401: {'description': 'Authentication required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='100/h', method='GET')
def get_balance(request):
    """Get user balance"""
    balance = get_user_balance(request.user)
    return success_response(
        data={'balance': str(balance), 'currency': 'NGN'},
        message='Balance retrieved successfully'
    )


@extend_schema(
    tags=['Payments'],
    summary='Initialize Payment',
    description='Initialize a payment transaction. Returns authorization URL for payment.',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'amount': {'type': 'number', 'description': 'Amount in NGN'},
                'callback_url': {'type': 'string', 'format': 'uri', 'description': 'Callback URL after payment'},
            },
            'required': ['amount'],
        }
    },
    responses={
        200: {
            'description': 'Payment initialized successfully',
            'examples': {
                'application/json': {
                    'authorization_url': 'https://checkout.paystack.com/...',
                    'access_code': 'access_code_123',
                    'reference': 'ref_123456789',
                }
            }
        },
        400: {'description': 'Validation error'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/h', method='POST')
def initialize_payment(request):
    """Initialize a payment transaction"""
    amount = request.data.get('amount')
    callback_url = request.data.get('callback_url')
    
    if not amount:
        return error_response('Payment amount is required.', status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            raise ValueError('Amount must be greater than 0')
    except (ValueError, TypeError):
        return error_response('Invalid payment amount. Amount must be greater than zero.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Generate unique reference (ensure uniqueness)
    max_attempts = 10
    reference = None
    for attempt in range(max_attempts):
        reference = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        if not Transaction.objects.filter(reference=reference).exists():
            break
        if attempt == max_attempts - 1:
            logger.error(f"Failed to generate unique transaction reference after {max_attempts} attempts")
            return error_response('Unable to process payment request. Please try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    try:
        paystack_client = PaystackClient()
        response = paystack_client.initialize_transaction(
            email=request.user.email,
            amount=amount_decimal,
            reference=reference,
            callback_url=callback_url,
            metadata={
                'user_id': request.user.id,
                'user_type': request.user.user_type,
            }
        )
        
        if response.get('status'):
            # Create pending transaction record
            Transaction.objects.create(
                user=request.user,
                transaction_type='DEPOSIT',
                status='PENDING',
                payment_method='CARD',
                amount=amount_decimal,
                fee=Decimal('0.00'),
                net_amount=amount_decimal,
                reference=reference,
                paystack_reference=response['data']['reference'],
                description='Payment initialization',
            )
            
            return success_response(
                data={
                    'authorization_url': response['data']['authorization_url'],
                    'access_code': response['data']['access_code'],
                    'reference': reference,
                },
                message='Payment initialized successfully'
            )
        else:
            error_message = response.get('message', 'Unable to start payment. Please check your details and try again.')
            return error_response(error_message, status_code=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error initializing payment for user {request.user.email}: {e}", exc_info=True)
        return error_response('Unable to start payment at this time. Please try again later.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Payments'],
    summary='Verify Payment',
    description='Verify a payment transaction by reference.',
    parameters=[
        OpenApiParameter(
            name='reference',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Transaction reference',
            required=True,
        ),
    ],
    responses={
        200: {
            'description': 'Payment verified',
            'examples': {
                'application/json': {
                    'status': 'success',
                    'amount': '5000.00',
                    'reference': 'ref_123456789',
                }
            }
        },
        400: {'description': 'Invalid reference'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='100/h', method='GET')
def verify_payment(request):
    """Verify a payment transaction"""
    reference = request.query_params.get('reference')
    
    if not reference:
        return error_response('Transaction reference is required to verify payment.', status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find transaction
        transaction_obj = Transaction.objects.get(
            reference=reference,
            user=request.user
        )
        
        # Verify with Paystack
        paystack_client = PaystackClient()
        response = paystack_client.verify_transaction(reference)
        
        if response.get('status') and response['data']['status'] == 'success':
            # Update transaction
            amount = Decimal(str(response['data']['amount'])) / 100
            
            if transaction_obj.status == 'PENDING':
                transaction_obj.status = 'SUCCESS'
                transaction_obj.completed_at = timezone.now()
                transaction_obj.metadata.update(response['data'])
                transaction_obj.save()
                
                # Update balance
                add_balance(request.user, amount, reference)
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='DEPOSIT_RECEIVED',
                    title='Payment Received',
                    message=f'You received ₦{amount:,.2f}',
                    related_transaction=transaction_obj,
                )
            
            return success_response(
                data={
                    'status': 'success',
                    'amount': str(amount),
                    'reference': reference,
                },
                message='Payment verified successfully'
            )
        else:
            return error_response('Payment verification failed. Please check your transaction reference and try again.', status_code=status.HTTP_400_BAD_REQUEST)
            
    except Transaction.DoesNotExist:
        return not_found_response('Transaction not found. Please check your transaction reference and try again.')
    except Exception as e:
        logger.error(f"Error verifying payment: {e}", exc_info=True)
        return error_response('Unable to verify payment at this time. Please try again later.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Payments'],
    summary='Create Dedicated Virtual Account',
    description='Create a dedicated virtual account (DVA) for the authenticated user using single-step assignment.',
    responses={
        200: {
            'description': 'DVA created successfully',
            'examples': {
                'application/json': {
                    'account_number': '8115333313',
                    'bank_name': 'Test Bank',
                    'account_name': 'John Doe',
                }
            }
        },
        400: {'description': 'Error creating DVA'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_dva(request):
    """Create dedicated virtual account (single-step)"""
    # Debug logging
    logger.info(f"create_dva called by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
    logger.info(f"User authenticated: {request.user.is_authenticated}")
    logger.info(f"User type: {request.user.user_type if request.user.is_authenticated else 'N/A'}")
    
    try:
        # Step 1: Check if DVA already exists locally
        if hasattr(request.user, 'dedicated_virtual_account'):
            dva = request.user.dedicated_virtual_account
            serializer = DedicatedVirtualAccountSerializer(dva)
            return success_response(
                data={'dva': serializer.data},
                message='DVA already exists'
            )
        
        # Step 2: Get or create Paystack customer and check for existing DVA
        paystack_client = PaystackClient()
        
        # Get customer from Paystack (or create if doesn't exist)
        customer_response = paystack_client.get_customer(email=request.user.email)
        
        if not customer_response.get('status'):
            # Customer doesn't exist, create one
            full_name = request.user.get_full_name()
            name_parts = full_name.split(' ', 1) if full_name else ['', '']
            first_name = name_parts[0] if len(name_parts) > 0 else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            customer_response = paystack_client.create_customer(
                email=request.user.email,
                first_name=first_name,
                last_name=last_name,
                phone=request.user.phone_number,
                metadata={
                    'user_id': request.user.id,
                    'user_type': request.user.user_type,
                }
            )
            
            if not customer_response.get('status'):
                error_message = customer_response.get('message', 'Failed to create customer')
                logger.error(f"Failed to create Paystack customer: {error_message}. Response: {customer_response}")
                return error_response(error_message, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Validate customer response has data
        if 'data' not in customer_response:
            logger.error(f"Invalid Paystack customer response structure: {customer_response}")
            return error_response('Invalid response from Paystack. Please try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        customer_code = customer_response['data'].get('customer_code')
        if not customer_code:
            logger.error(f"Customer code not found in Paystack response: {customer_response}")
            return error_response('Failed to get customer code from Paystack', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Step 3: Check if DVA already exists in Paystack for this customer
        logger.info(f"Checking for existing DVA for customer {customer_code}...")
        existing_dva_response = paystack_client.get_dedicated_accounts(customer_code=customer_code)
        
        if existing_dva_response.get('status') and existing_dva_response.get('data'):
            # DVA already exists in Paystack, sync it to our database
            logger.info(f"Found existing DVA in Paystack for customer {customer_code}")
            dedicated_accounts = existing_dva_response['data']
            
            # Handle both array and single object responses
            if not isinstance(dedicated_accounts, list):
                dedicated_accounts = [dedicated_accounts]
            
            # Get the first active account
            for account_data in dedicated_accounts:
                # Extract dedicated_account - could be nested or direct
                dedicated_account = None
                if isinstance(account_data, dict):
                    if 'dedicated_account' in account_data:
                        dedicated_account = account_data['dedicated_account']
                    elif account_data.get('account_number'):
                        dedicated_account = account_data
                
                if dedicated_account and isinstance(dedicated_account, dict) and dedicated_account.get('account_number'):
                    # Sync DVA to database
                    dva, created = DedicatedVirtualAccount.objects.update_or_create(
                        user=request.user,
                        defaults={
                            'paystack_customer_id': str(customer_response['data'].get('id', '')),
                            'account_number': dedicated_account.get('account_number', ''),
                            'bank_name': dedicated_account.get('bank', {}).get('name', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                            'bank_slug': dedicated_account.get('bank', {}).get('slug', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                            'account_name': dedicated_account.get('account_name', ''),
                            'currency': dedicated_account.get('currency', 'NGN'),
                        }
                    )
                    
                    if created:
                        Notification.objects.create(
                            user=request.user,
                            notification_type='DVA_CREATED',
                            title='Dedicated Account Synced',
                            message=f'Your dedicated account {dva.account_number} has been synced from Paystack',
                            metadata={
                                'account_number': dva.account_number,
                                'bank_name': dva.bank_name,
                            }
                        )
                    
                    serializer = DedicatedVirtualAccountSerializer(dva)
                    return success_response(
                        data={'dva': serializer.data},
                        message='DVA already exists and has been synced'
                    )
        
        # Step 4: Create new DVA (only if none exists)
        logger.info(f"No existing DVA found. Creating new DVA for customer {customer_code}...")
        
        full_name = request.user.get_full_name()
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Assign DVA (single-step)
        dva_response = paystack_client.assign_dedicated_account(
            customer_code=customer_code,
            email=request.user.email,
            first_name=first_name,
            last_name=last_name,
            phone=request.user.phone_number,
        )
        
        if not dva_response.get('status'):
            error_message = dva_response.get('message', 'Failed to assign DVA')
            logger.error(f"Failed to assign DVA: {error_message}. Response: {dva_response}")
            return error_response(error_message, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Paystack single-step DVA assignment can be asynchronous
        # Check if DVA was created immediately or is in progress
        message = dva_response.get('message', '').lower()
        dva_data = dva_response.get('data', {})
        dedicated_account = dva_data.get('dedicated_account', {}) if dva_data else {}
        
        # If response indicates "in progress" or no data, fetch from Paystack
        if 'in progress' in message or not dedicated_account or not dedicated_account.get('account_number'):
            logger.info(f"DVA assignment in progress for user {request.user.email}. Fetching from Paystack...")
            
            # Wait a moment and fetch DVA from Paystack API
            import time
            time.sleep(2)  # Brief delay for async processing
            
            dva_list_response = paystack_client.get_dedicated_accounts(customer_code=customer_code)
            
            if dva_list_response.get('status') and dva_list_response.get('data'):
                dedicated_accounts = dva_list_response['data']
                
                # Handle both array and single object responses
                if not isinstance(dedicated_accounts, list):
                    dedicated_accounts = [dedicated_accounts]
                
                # Get the first active account
                for account_data in dedicated_accounts:
                    # Extract dedicated_account - could be nested or direct
                    dedicated_account = None
                    if isinstance(account_data, dict):
                        if 'dedicated_account' in account_data:
                            dedicated_account = account_data['dedicated_account']
                        elif account_data.get('account_number'):
                            dedicated_account = account_data
                    
                    if dedicated_account and isinstance(dedicated_account, dict) and dedicated_account.get('account_number'):
                        # DVA exists in Paystack, sync it to our database
                        dva, created = DedicatedVirtualAccount.objects.update_or_create(
                            user=request.user,
                            defaults={
                                'paystack_customer_id': str(customer_response['data'].get('id', '')),
                                'account_number': dedicated_account.get('account_number', ''),
                                'bank_name': dedicated_account.get('bank', {}).get('name', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                                'bank_slug': dedicated_account.get('bank', {}).get('slug', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                                'account_name': dedicated_account.get('account_name', ''),
                                'currency': dedicated_account.get('currency', 'NGN'),
                            }
                        )
                        
                        if created:
                            Notification.objects.create(
                                user=request.user,
                                notification_type='DVA_CREATED',
                                title='Dedicated Account Created',
                                message=f'Your dedicated account {dva.account_number} has been created at {dva.bank_name}',
                                metadata={
                                    'account_number': dva.account_number,
                                    'bank_name': dva.bank_name,
                                }
                            )
                        
                        serializer = DedicatedVirtualAccountSerializer(dva)
                        return created_response(data=serializer.data, message='Dedicated account created successfully')
            
            # If still not found, return accepted status (webhook will update later)
            logger.info(f"DVA assignment in progress. Will be synced via webhook.")
            return success_response(
                message='DVA creation in progress. You will be notified when ready.',
                status_code=status.HTTP_202_ACCEPTED
            )
        
        # DVA was created successfully (synchronous response)
        if not dedicated_account or not dedicated_account.get('account_number'):
            logger.error(f"Invalid DVA response structure: {dva_response}")
            return error_response('Invalid DVA response from Paystack', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Save DVA to database
        dva, created = DedicatedVirtualAccount.objects.update_or_create(
            user=request.user,
            defaults={
                'paystack_customer_id': str(customer_response['data'].get('id', '')),
                'account_number': dedicated_account.get('account_number', ''),
                'bank_name': dedicated_account.get('bank', {}).get('name', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                'bank_slug': dedicated_account.get('bank', {}).get('slug', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                'account_name': dedicated_account.get('account_name', ''),
                'currency': dedicated_account.get('currency', 'NGN'),
            }
        )
        
        if created:
            Notification.objects.create(
                user=request.user,
                notification_type='DVA_CREATED',
                title='Dedicated Account Created',
                message=f'Your dedicated account {dva.account_number} has been created at {dva.bank_name}',
                metadata={
                    'account_number': dva.account_number,
                    'bank_name': dva.bank_name,
                }
            )
        
        serializer = DedicatedVirtualAccountSerializer(dva)
        return created_response(data=serializer.data, message='Dedicated account created successfully')
        
    except Exception as e:
        logger.error(f"Error creating DVA: {e}", exc_info=True)
        return error_response('Unable to create dedicated account at this time. Please try again later.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Payments'],
    summary='Get Dedicated Virtual Account',
    description='Get dedicated virtual account details for authenticated user. If not found locally, will sync from Paystack.',
    responses={
        200: DedicatedVirtualAccountSerializer,
        404: {'description': 'DVA not found'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='100/h', method='GET')
def get_dva(request):
    """Get user's DVA, sync from Paystack if not found locally"""
    try:
        dva = request.user.dedicated_virtual_account
        serializer = DedicatedVirtualAccountSerializer(dva)
        return success_response(data=serializer.data, message='Dedicated account retrieved successfully')
    except AttributeError:
        # DVA not found locally, try to sync from Paystack
        logger.info(f"DVA not found locally for user {request.user.email}. Attempting to sync from Paystack...")
        
        try:
            paystack_client = PaystackClient()
            
            # Get customer from Paystack
            customer_response = paystack_client.get_customer(email=request.user.email)
            
            if not customer_response.get('status') or 'data' not in customer_response:
                logger.warning(f"Customer not found in Paystack for {request.user.email}. Response: {customer_response}")
                return not_found_response('No dedicated account found. Please create a dedicated account first.')
            
            customer_code = customer_response['data'].get('customer_code')
            if not customer_code:
                logger.warning(f"Customer code not found in Paystack response: {customer_response}")
                return not_found_response('No dedicated account found. Please create a dedicated account first.')
            
            # Get dedicated accounts from Paystack
            dva_list_response = paystack_client.get_dedicated_accounts(customer_code=customer_code)
            
            if not dva_list_response.get('status'):
                logger.warning(f"Failed to fetch dedicated accounts from Paystack: {dva_list_response}")
                return not_found_response('No dedicated account found. Please create a dedicated account first.')
            
            if dva_list_response.get('data'):
                dedicated_accounts = dva_list_response['data']
                
                # Handle both array and single object responses
                if not isinstance(dedicated_accounts, list):
                    dedicated_accounts = [dedicated_accounts]
                
                # Find the first active account with account_number
                for account_data in dedicated_accounts:
                    # Extract dedicated_account - could be nested or direct
                    dedicated_account = None
                    
                    if isinstance(account_data, dict):
                        # Check if dedicated_account is nested
                        if 'dedicated_account' in account_data:
                            dedicated_account = account_data['dedicated_account']
                        # Check if account_data IS the dedicated_account
                        elif account_data.get('account_number'):
                            dedicated_account = account_data
                    
                    if dedicated_account and isinstance(dedicated_account, dict):
                        account_number = dedicated_account.get('account_number')
                        if account_number:
                            # Sync DVA to database
                            dva, created = DedicatedVirtualAccount.objects.update_or_create(
                                user=request.user,
                                defaults={
                                    'paystack_customer_id': str(customer_response['data'].get('id', '')),
                                    'account_number': account_number,
                                    'bank_name': dedicated_account.get('bank', {}).get('name', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                                    'bank_slug': dedicated_account.get('bank', {}).get('slug', '') if isinstance(dedicated_account.get('bank'), dict) else '',
                                    'account_name': dedicated_account.get('account_name', ''),
                                    'currency': dedicated_account.get('currency', 'NGN'),
                                }
                            )
                            
                            if created:
                                # Create notification only if newly synced
                                Notification.objects.create(
                                    user=request.user,
                                    notification_type='DVA_CREATED',
                                    title='Dedicated Account Synced',
                                    message=f'Your dedicated account {dva.account_number} has been synced from Paystack',
                                    metadata={
                                        'account_number': dva.account_number,
                                        'bank_name': dva.bank_name,
                                    }
                                )
                            
                            serializer = DedicatedVirtualAccountSerializer(dva)
                            return success_response(data=serializer.data, message='Dedicated account retrieved successfully')
            
            # No DVA found in Paystack either
            logger.warning(f"No dedicated accounts found in Paystack for customer {customer_code}. Response: {dva_list_response}")
            return not_found_response('No dedicated account found. Please create a dedicated account first.')
            
        except Exception as e:
            logger.error(f"Error syncing DVA from Paystack: {e}", exc_info=True)
            return not_found_response('No dedicated account found. Please create a dedicated account first.')


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing transaction history.
    Supports filtering by type, status, payment_method, and date range.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['reference', 'paystack_reference', 'description']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return transactions for authenticated user only"""
        queryset = Transaction.objects.filter(user=self.request.user)
        
        # Filter by transaction type
        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    @extend_schema(
        tags=['Payments'],
        summary='List Transactions',
        description='Get transaction history with filtering options.',
        parameters=[
            OpenApiParameter(
                name='transaction_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by type (DEPOSIT, WITHDRAWAL)',
                enum=['DEPOSIT', 'WITHDRAWAL'],
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status',
                enum=['PENDING', 'SUCCESS', 'FAILED', 'REVERSED'],
            ),
            OpenApiParameter(
                name='payment_method',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by payment method',
            ),
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter from date (ISO format)',
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter to date (ISO format)',
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """List transactions"""
        return super().list(request, *args, **kwargs)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return notifications for authenticated user only"""
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_read=is_read_bool)
        
        # Filter by notification type
        notification_type = self.request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset
    
    @extend_schema(
        tags=['Payments'],
        summary='Get Notification',
        description='Retrieve a specific notification by ID.',
        responses={
            200: NotificationSerializer,
            404: {'description': 'Notification not found'},
            401: {'description': 'Authentication required'},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific notification"""
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        tags=['Payments'],
        summary='List Notifications',
        description='Get notifications with filtering options.',
        parameters=[
            OpenApiParameter(
                name='is_read',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by read status',
            ),
            OpenApiParameter(
                name='notification_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by notification type',
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """List notifications"""
        queryset = self.get_queryset()
        unread_count = queryset.filter(is_read=False).count()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'unread_count': unread_count,
                'results': serializer.data,
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data={'unread_count': unread_count, 'results': serializer.data},
            message='Notifications retrieved successfully'
        )
    
    @extend_schema(
        tags=['Payments'],
        summary='Mark Notification as Read',
        description='Mark a notification as read.',
    )
    @action(detail=True, methods=['put'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        serializer = self.get_serializer(notification)
        return success_response(data=serializer.data, message='Notification retrieved successfully')
    
    @extend_schema(
        tags=['Payments'],
        summary='Mark All Notifications as Read',
        description='Mark all notifications as read for authenticated user.',
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return success_response(
            data={'updated_count': updated},
            message=f'{updated} notifications marked as read'
        )


@extend_schema(
    tags=['Payments'],
    summary='Create Transfer Recipient',
    description='Create a transfer recipient for withdrawals.',
    request=CreateTransferRecipientSerializer,
    responses={
        201: TransferRecipientSerializer,
        400: {'description': 'Validation error'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/h', method='POST')
def create_transfer_recipient(request):
    """Create transfer recipient"""
    serializer = CreateTransferRecipientSerializer(data=request.data)
    
    if not serializer.is_valid():
        return validation_error_response(serializer.errors, message='Validation error')
    
    try:
        paystack_client = PaystackClient()
        response = paystack_client.create_transfer_recipient(
            type=serializer.validated_data['recipient_type'],
            name=serializer.validated_data['name'],
            account_number=serializer.validated_data['account_number'],
            bank_code=serializer.validated_data.get('bank_code'),
            currency=serializer.validated_data.get('currency', 'NGN'),
        )
        
        if not response.get('status'):
            error_message = response.get('message', 'Failed to create recipient')
            # Provide user-friendly error messages
            if 'already exists' in error_message.lower() or 'duplicate' in error_message.lower():
                error_message = 'Bank account details already exist. Please use a different account or check your existing recipients.'
            return error_response(error_message, status_code=status.HTTP_400_BAD_REQUEST)
        
        recipient_data = response['data']
        
        # Check if recipient already exists before creating
        existing_recipient = TransferRecipient.objects.filter(
            paystack_recipient_code=recipient_data['recipient_code']
        ).first()
        
        if existing_recipient:
            # Recipient already exists, return existing one
            serializer_response = TransferRecipientSerializer(existing_recipient)
            return success_response(
                data={'recipient': serializer_response.data},
                message='Bank account details already exist'
            )
        
        # Create recipient record
        recipient = TransferRecipient.objects.create(
            user=request.user,
            paystack_recipient_code=recipient_data['recipient_code'],
            recipient_type=serializer.validated_data['recipient_type'],
            name=serializer.validated_data['name'],
            account_number=serializer.validated_data['account_number'],
            bank_code=serializer.validated_data.get('bank_code'),
            bank_name=recipient_data.get('details', {}).get('bank_name'),
            currency=serializer.validated_data.get('currency', 'NGN'),
        )
        
        serializer_response = TransferRecipientSerializer(recipient)
        return created_response(data=serializer_response.data, message='Bank account added successfully')
        
    except IntegrityError as e:
        # Handle database integrity errors (duplicate keys)
        error_str = str(e).lower()
        if 'paystack_recipient_code' in error_str or 'recipient_code' in error_str:
            logger.warning(f"Duplicate recipient code for user {request.user.email}: {e}")
            return error_response('Bank account details already exist. Please use a different account or check your existing recipients.', status_code=status.HTTP_400_BAD_REQUEST)
        elif 'account_number' in error_str or 'unique' in error_str:
            logger.warning(f"Duplicate account number for user {request.user.email}: {e}")
            return error_response('This bank account is already registered. Please use a different account.', status_code=status.HTTP_400_BAD_REQUEST)
        else:
            logger.warning(f"Integrity error for user {request.user.email}: {e}")
            return error_response('This information already exists. Please use different details.', status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error creating transfer recipient for user {request.user.email}: {e}", exc_info=True)
        return error_response('Unable to add bank account. Please check your details and try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Payments'],
    summary='List Transfer Recipients',
    description='Get list of transfer recipients for authenticated user.',
    responses={
        200: TransferRecipientSerializer(many=True),
        401: {'description': 'Authentication required'},
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='100/h', method='GET')
def list_transfer_recipients(request):
    """List transfer recipients"""
    recipients = TransferRecipient.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-created_at')
    
    serializer = TransferRecipientSerializer(recipients, many=True)
    return success_response(data={'recipients': serializer.data}, message='Recipients retrieved successfully')


@extend_schema(
    tags=['Payments'],
    summary='Create Transfer',
    description='Create a transfer (withdrawal) to a recipient. Balance will be deducted immediately.',
    request=CreateTransferSerializer,
    responses={
        200: {
            'description': 'Transfer created',
            'examples': {
                'application/json': {
                    'transfer_code': 'TRF_abc123',
                    'reference': 'ref_123456',
                    'status': 'pending',
                    'otp_required': False,
                }
            }
        },
        400: {'description': 'Validation error or insufficient balance'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/h', method='POST')
def create_transfer(request):
    """Create transfer (withdrawal)"""
    serializer = CreateTransferSerializer(data=request.data)
    
    if not serializer.is_valid():
        return validation_error_response(serializer.errors, message='Validation error')
    
    amount = serializer.validated_data['amount']
    recipient_code = serializer.validated_data['recipient_code']
    
    # Check balance
    balance = get_user_balance(request.user)
    if balance < amount:
        return error_response('Insufficient balance. Please add funds to your account before making a withdrawal.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Generate unique reference (ensure uniqueness)
    max_attempts = 10
    reference = None
    for attempt in range(max_attempts):
        reference = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        if not Transaction.objects.filter(reference=reference).exists():
            break
        if attempt == max_attempts - 1:
            logger.error(f"Failed to generate unique transaction reference after {max_attempts} attempts")
            return error_response('Unable to process payment request. Please try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    try:
        # Use database transaction to ensure atomicity
        with db_transaction.atomic():
            # Deduct balance immediately
            if not deduct_balance(request.user, amount, reference):
                return error_response('Insufficient balance. Please add funds to your account before making a withdrawal.', status_code=status.HTTP_400_BAD_REQUEST)
            
            # Create pending transaction
            transaction_obj = Transaction.objects.create(
                user=request.user,
                transaction_type='WITHDRAWAL',
                status='PENDING',
                payment_method='PAYSTACK_BALANCE',
                amount=amount,
                fee=Decimal('0.00'),
                net_amount=amount,
                reference=reference,
                description=f'Transfer to {recipient_code}',
            )
            
            # Create Paystack transfer
            paystack_client = PaystackClient()
            response = paystack_client.create_transfer(
                source='balance',
                amount=amount,
                recipient=recipient_code,
                reason=serializer.validated_data.get('reason'),
                reference=reference,
                currency=serializer.validated_data.get('currency', 'NGN'),
            )
            
            if not response.get('status'):
                # Reverse balance if transfer creation failed
                add_balance(request.user, amount, reference)
                transaction_obj.status = 'FAILED'
                transaction_obj.save()
                
                return error_response(response.get('message', 'Failed to create transfer'), status_code=status.HTTP_400_BAD_REQUEST)
            
            transfer_data = response['data']
            
            # Update transaction with Paystack details
            transaction_obj.paystack_transaction_id = transfer_data.get('transfer_code', '')
            transaction_obj.paystack_reference = transfer_data.get('reference', reference)
            transaction_obj.metadata.update(transfer_data)
            
            # Check if OTP is required
            otp_required = 'otp' in transfer_data
            
            if otp_required:
                transaction_obj.status = 'PROCESSING'
                transaction_obj.save()
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='TRANSFER_PENDING',
                    title='Transfer Initiated',
                    message=f'Your transfer of ₦{amount:,.2f} requires OTP verification',
                    related_transaction=transaction_obj,
                )
                
                return success_response(
                    data={
                        'transfer_code': transfer_data.get('transfer_code', ''),
                        'reference': reference,
                        'status': 'processing',
                        'otp_required': True,
                    },
                    message='Transfer created. OTP required.'
                )
            else:
                transaction_obj.status = 'SUCCESS'
                transaction_obj.completed_at = timezone.now()
                transaction_obj.save()
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='WITHDRAWAL_SUCCESS',
                    title='Transfer Successful',
                    message=f'Your transfer of ₦{amount:,.2f} was successful',
                    related_transaction=transaction_obj,
                )
                
                return success_response(
                    data={
                        'transfer_code': transfer_data.get('transfer_code', ''),
                        'reference': reference,
                        'status': 'success',
                        'otp_required': False,
                    },
                    message='Transfer created successfully'
                )
            
    except Exception as e:
        logger.error(f"Error creating transfer: {e}", exc_info=True)
        # Reverse balance if error occurred (reference might not exist if error occurred early)
        try:
            if 'reference' in locals():
                add_balance(request.user, amount, reference)
        except:
            pass
        
        return error_response('Unable to process withdrawal at this time. Please try again later.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Payments'],
    summary='Finalize Transfer',
    description='Finalize a transfer with OTP.',
    request=FinalizeTransferSerializer,
    responses={
        200: {
            'description': 'Transfer finalized',
            'examples': {
                'application/json': {
                    'message': 'Transfer finalized successfully',
                    'status': 'success',
                }
            }
        },
        400: {'description': 'Invalid OTP or transfer code'},
        401: {'description': 'Authentication required'},
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/h', method='POST')
def finalize_transfer(request):
    """Finalize transfer with OTP"""
    serializer = FinalizeTransferSerializer(data=request.data)
    
    if not serializer.is_valid():
        return validation_error_response(serializer.errors, message='Validation error')
    
    transfer_code = serializer.validated_data['transfer_code']
    otp = serializer.validated_data['otp']
    
    try:
        paystack_client = PaystackClient()
        response = paystack_client.finalize_transfer(transfer_code, otp)
        
        if not response.get('status'):
            return error_response(response.get('message', 'Failed to finalize transfer'), status_code=status.HTTP_400_BAD_REQUEST)
        
        # Find and update transaction
        transfer_data = response['data']
        reference = transfer_data.get('reference')
        
        try:
            transaction_obj = Transaction.objects.get(
                paystack_reference=reference,
                user=request.user
            )
            
            transaction_obj.status = 'SUCCESS'
            transaction_obj.completed_at = timezone.now()
            transaction_obj.save()
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                notification_type='WITHDRAWAL_SUCCESS',
                title='Transfer Successful',
                message=f'Your transfer of ₦{transaction_obj.amount:,.2f} was successful',
                related_transaction=transaction_obj,
            )
            
            return success_response(
                data={'status': 'success'},
                message='Transfer finalized successfully'
            )
            
        except Transaction.DoesNotExist:
            return not_found_response('Transaction not found. Please check your transaction reference and try again.')
            
    except Exception as e:
        logger.error(f"Error finalizing transfer: {e}", exc_info=True)
        return error_response('Unable to complete withdrawal at this time. Please try again later.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Payments'],
    summary='Paystack Webhook',
    description='Webhook endpoint for Paystack events. Public endpoint (no authentication).',
    request={
        'application/json': {
            'type': 'object',
        }
    },
    responses={
        200: {'description': 'Webhook processed'},
        400: {'description': 'Invalid webhook'},
    },
)
@api_view(['POST'])
@permission_classes([])  # Public endpoint
def paystack_webhook(request):
    """Handle Paystack webhook events"""
    from apps.payments.services.webhook_handler import PaystackWebhookHandler
    
    # Get signature from header
    signature = request.headers.get('X-Paystack-Signature', '')
    
    if not signature:
        return error_response('Webhook signature is missing. Request rejected for security.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Get raw body
    payload = request.body.decode('utf-8')
    
    try:
        handler = PaystackWebhookHandler()
        
        # Verify signature
        if not handler.verify_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            return error_response('Invalid webhook signature. Request rejected for security.', status_code=status.HTTP_400_BAD_REQUEST)
        
        # Parse event data
        import json
        event_data = json.loads(payload)
        event_type = event_data.get('event')
        
        if not event_type:
            return error_response('Webhook event type is missing. Unable to process webhook.', status_code=status.HTTP_400_BAD_REQUEST)
        
        # Process webhook
        handler.process_webhook(event_type, event_data)
        
        return success_response(message='Webhook processed successfully')
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return error_response('Unable to process webhook event. Please contact support if this persists.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

