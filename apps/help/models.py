from django.db import models
from django.conf import settings
from apps.core.models import AbstractBaseModel


class HelpRequest(AbstractBaseModel):
    """
    Help/Support request model.
    Users can submit help requests which are processed via n8n workflows.
    """
    CATEGORY_CHOICES = [
        ('GENERAL', 'General Inquiry'),
        ('ACCOUNT', 'Account & Profile'),
        ('ORDERS', 'Orders & Delivery'),
        ('PAYMENT', 'Payment & Billing'),
        ('COURIER', 'Courier & Driver'),
        ('TECHNICAL', 'Technical Support'),
        ('OTHER', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    # User information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='help_requests',
        help_text='User who submitted the request (null if anonymous)'
    )
    user_email = models.EmailField(
        help_text='Email address of the requester'
    )
    user_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Name of the requester'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Phone number (optional)'
    )
    
    # Request details
    subject = models.CharField(
        max_length=200,
        help_text='Subject/title of the help request'
    )
    message = models.TextField(
        help_text='Detailed message/description'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='GENERAL',
        help_text='Category of the help request'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='NORMAL',
        help_text='Priority level'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text='Current status of the request'
    )
    
    # n8n integration
    n8n_workflow_triggered = models.BooleanField(
        default=False,
        help_text='Whether n8n workflow was successfully triggered'
    )
    n8n_workflow_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='n8n workflow ID or webhook URL used'
    )
    
    class Meta:
        db_table = 'help_requests'
        ordering = ['-created_at']
        verbose_name = 'Help Request'
        verbose_name_plural = 'Help Requests'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.user_email} ({self.status})"
    
    def get_user_display_name(self):
        """Get display name for the user"""
        if self.user:
            return self.user.get_full_name() or self.user.email
        return self.user_name or self.user_email

