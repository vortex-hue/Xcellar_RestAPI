from django.contrib import admin
from django.utils.html import format_html
from .models import HelpRequest


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'subject_preview',
        'user_info',
        'category',
        'priority',
        'status',
        'n8n_workflow_triggered',
        'created_at',
    ]
    list_filter = [
        'category',
        'priority',
        'status',
        'n8n_workflow_triggered',
        'created_at',
    ]
    search_fields = [
        'subject',
        'message',
        'user_email',
        'user_name',
        'user__email',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'n8n_workflow_triggered',
        'n8n_workflow_id',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'subject',
                'message',
                'category',
                'priority',
                'status',
            )
        }),
        ('User Information', {
            'fields': (
                'user',
                'user_email',
                'user_name',
                'phone_number',
            )
        }),
        ('n8n Integration', {
            'fields': (
                'n8n_workflow_triggered',
                'n8n_workflow_id',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def subject_preview(self, obj):
        """Display truncated subject in list view"""
        max_length = 60
        if len(obj.subject) > max_length:
            return format_html(
                '<span title="{}">{}</span>',
                obj.subject,
                obj.subject[:max_length] + '...'
            )
        return obj.subject
    subject_preview.short_description = 'Subject'
    subject_preview.admin_order_field = 'subject'
    
    def user_info(self, obj):
        """Display user information"""
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.get_full_name() or obj.user.email,
                obj.user.email
            )
        return format_html(
            '<strong>{}</strong><br><small>Anonymous</small>',
            obj.user_name or obj.user_email
        )
    user_info.short_description = 'User'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    actions = ['mark_resolved', 'mark_closed', 'mark_in_progress']
    
    def mark_resolved(self, request, queryset):
        """Bulk action to mark requests as resolved"""
        updated = queryset.update(status='RESOLVED')
        self.message_user(request, f'{updated} help request(s) marked as resolved.')
    mark_resolved.short_description = 'Mark selected as resolved'
    
    def mark_closed(self, request, queryset):
        """Bulk action to mark requests as closed"""
        updated = queryset.update(status='CLOSED')
        self.message_user(request, f'{updated} help request(s) marked as closed.')
    mark_closed.short_description = 'Mark selected as closed'
    
    def mark_in_progress(self, request, queryset):
        """Bulk action to mark requests as in progress"""
        updated = queryset.update(status='IN_PROGRESS')
        self.message_user(request, f'{updated} help request(s) marked as in progress.')
    mark_in_progress.short_description = 'Mark selected as in progress'

