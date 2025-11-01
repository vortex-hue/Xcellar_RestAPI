from rest_framework import serializers
from decimal import Decimal
from .models import Transaction, Notification, DedicatedVirtualAccount, TransferRecipient


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transaction data"""
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'status',
            'payment_method',
            'amount',
            'fee',
            'net_amount',
            'reference',
            'paystack_reference',
            'description',
            'created_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'reference',
            'created_at',
            'completed_at',
        ]


class DedicatedVirtualAccountSerializer(serializers.ModelSerializer):
    """Serializer for DVA data"""
    
    class Meta:
        model = DedicatedVirtualAccount
        fields = [
            'id',
            'account_number',
            'bank_name',
            'bank_slug',
            'account_name',
            'currency',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class TransferRecipientSerializer(serializers.ModelSerializer):
    """Serializer for transfer recipient data"""
    
    class Meta:
        model = TransferRecipient
        fields = [
            'id',
            'paystack_recipient_code',
            'recipient_type',
            'name',
            'account_number',
            'bank_code',
            'bank_name',
            'currency',
            'created_at',
        ]
        read_only_fields = ['id', 'paystack_recipient_code', 'created_at']


class CreateTransferRecipientSerializer(serializers.Serializer):
    """Serializer for creating transfer recipient"""
    recipient_type = serializers.ChoiceField(
        choices=['nuban', 'mobile_money', 'basa'],
        required=True
    )
    name = serializers.CharField(max_length=200, required=True)
    account_number = serializers.CharField(max_length=20, required=True)
    bank_code = serializers.CharField(max_length=20, required=False)
    currency = serializers.CharField(max_length=3, default='NGN', required=False)
    
    def validate(self, attrs):
        """Validate bank_code is required for nuban"""
        if attrs.get('recipient_type') == 'nuban' and not attrs.get('bank_code'):
            raise serializers.ValidationError({
                'bank_code': 'Bank code is required for NUBAN recipients'
            })
        return attrs


class CreateTransferSerializer(serializers.Serializer):
    """Serializer for creating transfer"""
    recipient_code = serializers.CharField(max_length=255, required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=True
    )
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)
    currency = serializers.CharField(max_length=3, default='NGN', required=False)
    
    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0')
        return value


class FinalizeTransferSerializer(serializers.Serializer):
    """Serializer for finalizing transfer with OTP"""
    transfer_code = serializers.CharField(max_length=255, required=True)
    otp = serializers.CharField(max_length=10, required=True)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification data"""
    related_transaction = TransactionSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'is_read',
            'related_transaction',
            'created_at',
            'read_at',
        ]
        read_only_fields = ['id', 'created_at', 'read_at']

