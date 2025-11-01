import hashlib
import hmac
import json
import logging
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal

from apps.payments.models import Transaction, Notification, DedicatedVirtualAccount
from apps.payments.services.paystack_client import PaystackClient
from apps.accounts.models import UserProfile, CourierProfile

logger = logging.getLogger(__name__)


class PaystackWebhookHandler:
    """
    Handler for Paystack webhook events.
    """
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        if not self.secret_key:
            logger.warning("Paystack secret key not configured")
    
    def verify_signature(self, payload, signature):
        """
        Verify Paystack webhook signature.
        
        Args:
            payload: Raw request body
            signature: X-Paystack-Signature header value
        
        Returns:
            bool: True if signature is valid
        """
        if not self.secret_key:
            logger.error("Cannot verify signature: Paystack secret key not configured")
            return False
        
        computed_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
    
    def handle_charge_success(self, event_data):
        """
        Handle charge.success webhook event.
        
        Args:
            event_data: Webhook event data
        """
        try:
            data = event_data.get('data', {})
            reference = data.get('reference')
            amount = data.get('amount', 0) / 100  # Convert from kobo
            customer_email = data.get('customer', {}).get('email')
            channel = data.get('channel')
            
            # Find user by email
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(email=customer_email)
            except User.DoesNotExist:
                logger.error(f"User not found for email: {customer_email}")
                return
            
            # Use database transaction to ensure atomicity
            with db_transaction.atomic():
                # Check if transaction already exists
                transaction_obj, created = Transaction.objects.get_or_create(
                    paystack_reference=reference,
                    defaults={
                        'user': user,
                        'transaction_type': 'DEPOSIT',
                        'status': 'SUCCESS',
                        'payment_method': 'DVA' if channel == 'dedicated_nuban' else 'BANK_TRANSFER',
                        'amount': Decimal(str(amount)),
                        'fee': Decimal('0.00'),
                        'net_amount': Decimal(str(amount)),
                        'reference': reference,
                        'paystack_transaction_id': str(data.get('id', '')),
                        'paystack_reference': reference,
                        'description': f'Deposit via {channel}',
                        'metadata': data,
                        'completed_at': timezone.now(),
                    }
                )
                
                if created:
                    # Update user balance
                    self._add_balance(user, Decimal(str(amount)), transaction_obj.reference)
                    
                    # Create notification
                    Notification.objects.create(
                        user=user,
                        notification_type='DEPOSIT_RECEIVED',
                        title='Deposit Received',
                        message=f'You received ₦{amount:,.2f} via {channel}',
                        related_transaction=transaction_obj,
                        metadata={'channel': channel}
                    )
                    
                    logger.info(f"Deposit processed: {reference} for user {user.email}")
                else:
                    logger.info(f"Transaction already exists: {reference}")
                
        except Exception as e:
            logger.error(f"Error handling charge.success: {e}", exc_info=True)
    
    def handle_transfer_success(self, event_data):
        """
        Handle transfer.success webhook event.
        
        Args:
            event_data: Webhook event data
        """
        try:
            data = event_data.get('data', {})
            transfer_code = data.get('transfer_code')
            reference = data.get('reference')
            amount = data.get('amount', 0) / 100  # Convert from kobo
            
            # Find transaction by reference
            try:
                transaction_obj = Transaction.objects.get(reference=reference)
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for reference: {reference}")
                return
            
            # Use database transaction to ensure atomicity
            with db_transaction.atomic():
                # Update transaction status
                transaction_obj.status = 'SUCCESS'
                transaction_obj.paystack_transaction_id = transfer_code
                transaction_obj.completed_at = timezone.now()
                transaction_obj.metadata.update(data)
                transaction_obj.save()
                
                # Create notification
                Notification.objects.create(
                    user=transaction_obj.user,
                    notification_type='WITHDRAWAL_SUCCESS',
                    title='Withdrawal Successful',
                    message=f'Your withdrawal of ₦{amount:,.2f} was successful',
                    related_transaction=transaction_obj,
                )
            
            logger.info(f"Withdrawal processed: {reference}")
            
        except Exception as e:
            logger.error(f"Error handling transfer.success: {e}", exc_info=True)
    
    def handle_transfer_failed(self, event_data):
        """
        Handle transfer.failed webhook event.
        
        Args:
            event_data: Webhook event data
        """
        try:
            data = event_data.get('data', {})
            reference = data.get('reference')
            reason = data.get('reason', 'Transfer failed')
            
            # Find transaction by reference
            try:
                transaction_obj = Transaction.objects.get(reference=reference)
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for reference: {reference}")
                return
            
            # Use database transaction to ensure atomicity
            with db_transaction.atomic():
                # Reverse balance if not already reversed
                if transaction_obj.status == 'PENDING':
                    self._add_balance(transaction_obj.user, transaction_obj.amount, transaction_obj.reference)
                
                # Update transaction status
                transaction_obj.status = 'FAILED'
                transaction_obj.completed_at = timezone.now()
                transaction_obj.metadata.update({'failure_reason': reason})
                transaction_obj.save()
                
                # Create notification
                Notification.objects.create(
                    user=transaction_obj.user,
                    notification_type='WITHDRAWAL_FAILED',
                    title='Withdrawal Failed',
                    message=f'Your withdrawal of ₦{transaction_obj.amount:,.2f} failed: {reason}',
                    related_transaction=transaction_obj,
                )
            
            logger.info(f"Withdrawal failed: {reference} - {reason}")
            
        except Exception as e:
            logger.error(f"Error handling transfer.failed: {e}", exc_info=True)
    
    def handle_transfer_reversed(self, event_data):
        """
        Handle transfer.reversed webhook event.
        
        Args:
            event_data: Webhook event data
        """
        try:
            data = event_data.get('data', {})
            reference = data.get('reference')
            
            # Find transaction by reference
            try:
                transaction_obj = Transaction.objects.get(reference=reference)
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found for reference: {reference}")
                return
            
            # Use database transaction to ensure atomicity
            with db_transaction.atomic():
                # Reverse balance
                self._add_balance(transaction_obj.user, transaction_obj.amount, transaction_obj.reference)
                
                # Update transaction status
                transaction_obj.status = 'REVERSED'
                transaction_obj.completed_at = timezone.now()
                transaction_obj.metadata.update(data)
                transaction_obj.save()
                
                # Create notification
                Notification.objects.create(
                    user=transaction_obj.user,
                    notification_type='WITHDRAWAL_REVERSED',
                    title='Withdrawal Reversed',
                    message=f'Your withdrawal of ₦{transaction_obj.amount:,.2f} was reversed',
                    related_transaction=transaction_obj,
                )
            
            logger.info(f"Withdrawal reversed: {reference}")
            
        except Exception as e:
            logger.error(f"Error handling transfer.reversed: {e}", exc_info=True)
    
    def handle_dva_assigned(self, event_data):
        """
        Handle dedicatedaccount.assign.success webhook event.
        
        Args:
            event_data: Webhook event data
        """
        try:
            data = event_data.get('data', {})
            customer_email = data.get('customer', {}).get('email')
            dedicated_account = data.get('dedicated_account', {})
            
            # Find user by email
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(email=customer_email)
            except User.DoesNotExist:
                logger.error(f"User not found for email: {customer_email}")
                return
            
            # Use database transaction to ensure atomicity
            with db_transaction.atomic():
                # Create or update DVA
                dva, created = DedicatedVirtualAccount.objects.update_or_create(
                    user=user,
                    defaults={
                        'paystack_customer_id': str(data.get('customer', {}).get('id', '')),
                        'account_number': dedicated_account.get('account_number', ''),
                        'bank_name': dedicated_account.get('bank', {}).get('name', ''),
                        'bank_slug': dedicated_account.get('bank', {}).get('slug', ''),
                        'account_name': dedicated_account.get('account_name', ''),
                        'currency': dedicated_account.get('currency', 'NGN'),
                    }
                )
                
                # Create notification
                Notification.objects.create(
                    user=user,
                    notification_type='DVA_CREATED',
                    title='Dedicated Account Created',
                    message=f'Your dedicated account {dva.account_number} has been created at {dva.bank_name}',
                    metadata={'account_number': dva.account_number, 'bank_name': dva.bank_name}
                )
            
            logger.info(f"DVA assigned: {dva.account_number} for user {user.email}")
            
        except Exception as e:
            logger.error(f"Error handling dedicatedaccount.assign.success: {e}", exc_info=True)
    
    def process_webhook(self, event_type, event_data):
        """
        Process webhook event based on event type.
        
        Args:
            event_type: Paystack event type
            event_data: Webhook event data
        """
        handlers = {
            'charge.success': self.handle_charge_success,
            'transfer.success': self.handle_transfer_success,
            'transfer.failed': self.handle_transfer_failed,
            'transfer.reversed': self.handle_transfer_reversed,
            'dedicatedaccount.assign.success': self.handle_dva_assigned,
        }
        
        handler = handlers.get(event_type)
        if handler:
            handler(event_data)
        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")
    
    def _add_balance(self, user, amount, reference):
        """
        Add balance to user profile atomically.
        
        Args:
            user: User instance
            amount: Amount to add
            reference: Transaction reference for logging
        """
        from django.db.models import F
        
        try:
            if user.user_type == 'USER':
                profile = user.user_profile
            elif user.user_type == 'COURIER':
                profile = user.courier_profile
            else:
                logger.error(f"Unknown user type: {user.user_type}")
                return
            
            # Atomic balance update
            profile.__class__.objects.filter(pk=profile.pk).update(
                balance=F('balance') + Decimal(str(amount)).quantize(Decimal('0.01'))
            )
            
            # Refresh from database
            profile.refresh_from_db()
            
            logger.info(f"Balance updated for {user.email}: +₦{amount:,.2f} (Reference: {reference})")
            
        except Exception as e:
            logger.error(f"Error updating balance for {user.email}: {e}", exc_info=True)

