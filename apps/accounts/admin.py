from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, CourierProfile
from .password_reset.models import PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'phone_number', 'user_type', 'is_active', 'is_staff', 'date_joined', 'last_login']
    list_filter = ['user_type', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['email', 'phone_number']
    ordering = ['-date_joined']
    
    # Remove fieldsets that reference non-existent fields
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Additional Info', {'fields': ('user_type', 'phone_number')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'user_type', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'balance', 'has_address', 'has_profile_image', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['full_name', 'user__email', 'address']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name')
        }),
        ('Profile Details', {
            'fields': ('address', 'profile_image')
        }),
        ('Financial', {
            'fields': ('balance',),
            'description': 'User account balance'
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
    
    def has_address(self, obj):
        """Check if profile has address"""
        return bool(obj.address)
    has_address.boolean = True
    has_address.short_description = 'Has Address'
    
    def has_profile_image(self, obj):
        """Check if profile has image"""
        return bool(obj.profile_image)
    has_profile_image.boolean = True
    has_profile_image.short_description = 'Has Image'


@admin.register(CourierProfile)
class CourierProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'balance', 'approval_status', 'is_available', 'has_address', 'has_profile_image', 'is_active', 'created_at']
    search_fields = ['full_name', 'user__email', 'address', 'license_number', 'bvn', 'bank_account_number']
    list_filter = ['approval_status', 'is_available', 'is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Courier Information', {
            'fields': ('user', 'full_name', 'license_number')
        }),
        ('Profile Details', {
            'fields': ('address', 'profile_image')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'vehicle_registration'),
            'classes': ('collapse',)
        }),
        ('Bank Information', {
            'fields': ('bvn', 'bank_account_number', 'bank_code', 'bank_name', 'account_name'),
            'description': 'Bank account details for payment processing'
        }),
        ('Approval Status', {
            'fields': ('approval_status', 'approval_notes', 'approved_by', 'approved_at'),
            'description': 'Courier approval and review status'
        }),
        ('Financial', {
            'fields': ('balance',),
            'description': 'Courier account balance'
        }),
        ('Status & Location', {
            'fields': ('is_available', 'current_location')
        }),
        ('System', {
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
        return qs.select_related('user', 'approved_by')
    
    def has_address(self, obj):
        """Check if profile has address"""
        return bool(obj.address)
    has_address.boolean = True
    has_address.short_description = 'Has Address'
    
    def has_profile_image(self, obj):
        """Check if profile has image"""
        return bool(obj.profile_image)
    has_profile_image.boolean = True
    has_profile_image.short_description = 'Has Image'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'is_used', 'is_expired', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email', 'user__email', 'token']
    readonly_fields = ['token', 'created_at', 'used_at']
    ordering = ['-created_at']
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

