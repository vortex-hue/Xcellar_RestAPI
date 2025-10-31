from django.contrib import admin
from django.utils.html import format_html
from .models import FAQ


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'order',
        'question_preview',
        'category',
        'answer_preview',
        'is_active',
        'created_at',
    ]
    list_display_links = ['question_preview']  # Make question clickable for editing
    list_filter = [
        'category',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'question',
        'answer',
        'category',
    ]
    list_editable = ['order', 'is_active']  # Allow quick editing of order and status
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['order', 'created_at']
    
    fieldsets = (
        ('FAQ Content', {
            'fields': (
                'question',
                'answer',
            ),
            'description': 'Enter the question and detailed answer for the FAQ.'
        }),
        ('Organization', {
            'fields': (
                'category',
                'order',
            ),
            'description': 'Categorize and order FAQs. Lower order numbers appear first.'
        }),
        ('Status', {
            'fields': ('is_active',),
            'description': 'Only active FAQs are displayed via the API.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        """Display truncated question in list view"""
        max_length = 60
        if len(obj.question) > max_length:
            return format_html(
                '<span title="{}">{}</span>',
                obj.question,
                obj.question[:max_length] + '...'
            )
        return obj.question
    question_preview.short_description = 'Question'
    question_preview.admin_order_field = 'question'
    
    def answer_preview(self, obj):
        """Display truncated answer in list view"""
        max_length = 80
        # Remove HTML tags and whitespace for preview
        text = obj.answer.replace('\n', ' ').strip()
        if len(text) > max_length:
            return format_html(
                '<span title="{}">{}</span>',
                text,
                text[:max_length] + '...'
            )
        return text
    answer_preview.short_description = 'Answer'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related()
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        """Bulk action to activate FAQs"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} FAQ(s) marked as active.')
    make_active.short_description = 'Mark selected FAQs as active'
    
    def make_inactive(self, request, queryset):
        """Bulk action to deactivate FAQs"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} FAQ(s) marked as inactive.')
    make_inactive.short_description = 'Mark selected FAQs as inactive'

