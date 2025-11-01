from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

from apps.core.models import AbstractBaseModel


class Transaction(AbstractBaseModel):
    """
    Transaction model to record both deposits and withdrawals.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CARD', 'Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('DVA', 'Dedicated Virtual Account'),
        ('USSD', 'USSD'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('PAYSTACK_BALANCE', 'Paystack Balance'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Transaction fee'
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Amount after fees (amount - fee)'
    )
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    paystack_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    paystack_reference = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_type', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status} - {self.reference}"
    
    def save(self, *args, **kwargs):
        """Calculate net_amount before saving"""
        if not self.net_amount:
            self.net_amount = self.amount - self.fee
        # Round to 2 decimal places
        self.net_amount = Decimal(str(self.net_amount)).quantize(Decimal('0.01'))
        self.amount = Decimal(str(self.amount)).quantize(Decimal('0.01'))
        self.fee = Decimal(str(self.fee)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class DedicatedVirtualAccount(AbstractBaseModel):
    """
    Dedicated Virtual Account (DVA) model for customers.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dedicated_virtual_account'
    )
    paystack_customer_id = models.CharField(max_length=255, db_index=True)
    account_number = models.CharField(max_length=20, unique=True, db_index=True)
    bank_name = models.CharField(max_length=200)
    bank_slug = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200)
    currency = models.CharField(max_length=3, default='NGN')
    
    class Meta:
        db_table = 'dedicated_virtual_accounts'
        verbose_name = 'Dedicated Virtual Account'
        verbose_name_plural = 'Dedicated Virtual Accounts'
    
    def __str__(self):
        return f"{self.account_name} - {self.account_number} ({self.bank_name})"


class TransferRecipient(AbstractBaseModel):
    """
    Transfer recipient model for storing Paystack transfer recipients.
    """
    RECIPIENT_TYPE_CHOICES = [
        ('nuban', 'NUBAN'),
        ('mobile_money', 'Mobile Money'),
        ('basa', 'BASA'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfer_recipients'
    )
    paystack_recipient_code = models.CharField(max_length=255, unique=True, db_index=True)
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=20)
    bank_code = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    currency = models.CharField(max_length=3, default='NGN')
    
    class Meta:
        db_table = 'transfer_recipients'
        verbose_name = 'Transfer Recipient'
        verbose_name_plural = 'Transfer Recipients'
    
    def __str__(self):
        return f"{self.name} - {self.account_number} ({self.bank_name or 'N/A'})"


class Notification(AbstractBaseModel):
    """
    Notification model for recording important user activities.
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('TRANSACTION_SUCCESS', 'Transaction Success'),
        ('TRANSACTION_FAILED', 'Transaction Failed'),
        ('DEPOSIT_RECEIVED', 'Deposit Received'),
        ('WITHDRAWAL_SUCCESS', 'Withdrawal Success'),
        ('WITHDRAWAL_FAILED', 'Withdrawal Failed'),
        ('WITHDRAWAL_REVERSED', 'Withdrawal Reversed'),
        ('DVA_CREATED', 'DVA Created'),
        ('BALANCE_LOW', 'Balance Low'),
        ('TRANSFER_PENDING', 'Transfer Pending'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.notification_type} - {self.user.email} - {self.title}"

