from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import AbstractBaseModel


class FAQ(AbstractBaseModel):
    """
    Frequently Asked Questions model.
    Only active FAQs are exposed via API.
    """
    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('ACCOUNT', 'Account & Profile'),
        ('ORDERS', 'Orders & Delivery'),
        ('PAYMENT', 'Payment & Billing'),
        ('COURIER', 'Courier & Driver'),
        ('TECHNICAL', 'Technical Support'),
        ('OTHER', 'Other'),
    ]
    
    question = models.CharField(
        max_length=500,
        help_text='The FAQ question (max 500 characters)'
    )
    answer = models.TextField(
        help_text='Detailed answer to the FAQ question'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='GENERAL',
        help_text='Category to group related FAQs'
    )
    order = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(9999)],
        help_text='Display order (lower numbers appear first). Use this to manually order FAQs.'
    )
    
    class Meta:
        db_table = 'faqs'
        ordering = ['order', 'created_at']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.category}: {self.question[:50]}..."
    
    def get_short_question(self):
        """Get truncated question for display"""
        return self.question[:100] + '...' if len(self.question) > 100 else self.question

