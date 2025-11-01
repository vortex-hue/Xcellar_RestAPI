from django.contrib import admin
from .models import Transaction, Notification, DedicatedVirtualAccount, TransferRecipient


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'transaction_type',
        'status',
        'payment_method',
        'amount',
        'fee',
        'net_amount',
        'reference',
        'created_at',
    ]
    list_filter = [
        'transaction_type',
        'status',
        'payment_method',
        'created_at',
    ]
    search_fields = [
        'reference',
        'paystack_reference',
        'user__email',
        'description',
    ]
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'user',
                'transaction_type',
                'status',
                'payment_method',
            )
        }),
        ('Amount Details', {
            'fields': (
                'amount',
                'fee',
                'net_amount',
            )
        }),
        ('References', {
            'fields': (
                'reference',
                'paystack_reference',
                'paystack_transaction_id',
            )
        }),
        ('Additional', {
            'fields': (
                'description',
                'metadata',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'notification_type',
        'title',
        'is_read',
        'created_at',
    ]
    list_filter = [
        'notification_type',
        'is_read',
        'created_at',
    ]
    search_fields = [
        'title',
        'message',
        'user__email',
    ]
    readonly_fields = ['created_at', 'updated_at', 'read_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Information', {
            'fields': (
                'user',
                'notification_type',
                'title',
                'message',
            )
        }),
        ('Status', {
            'fields': (
                'is_read',
                'read_at',
            )
        }),
        ('Related', {
            'fields': (
                'related_transaction',
                'metadata',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'related_transaction')


@admin.register(DedicatedVirtualAccount)
class DedicatedVirtualAccountAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'account_number',
        'account_name',
        'bank_name',
        'currency',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'bank_name',
        'currency',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'account_number',
        'account_name',
        'user__email',
        'bank_name',
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Account Details', {
            'fields': (
                'account_number',
                'account_name',
                'bank_name',
                'bank_slug',
                'currency',
            )
        }),
        ('Paystack Information', {
            'fields': ('paystack_customer_id',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(TransferRecipient)
class TransferRecipientAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'name',
        'account_number',
        'bank_name',
        'recipient_type',
        'currency',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'recipient_type',
        'currency',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'name',
        'account_number',
        'bank_name',
        'user__email',
        'paystack_recipient_code',
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Recipient Details', {
            'fields': (
                'recipient_type',
                'name',
                'account_number',
                'bank_code',
                'bank_name',
                'currency',
            )
        }),
        ('Paystack Information', {
            'fields': ('paystack_recipient_code',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')

