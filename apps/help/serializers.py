from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import HelpRequest

User = get_user_model()


class HelpRequestSerializer(serializers.ModelSerializer):
    """Serializer for help request submission"""
    
    user_email = serializers.EmailField(
        required=False,  # Not required if authenticated
        help_text='Email address (optional if authenticated)'
    )
    user_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        help_text='Your name (optional if authenticated)'
    )
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        help_text='Your phone number (optional)'
    )
    subject = serializers.CharField(
        required=True,
        max_length=200,
        help_text='Subject/title of your help request'
    )
    message = serializers.CharField(
        required=True,
        help_text='Detailed description of your issue or question'
    )
    category = serializers.ChoiceField(
        choices=HelpRequest.CATEGORY_CHOICES,
        default='GENERAL',
        required=False,
        help_text='Category of your request'
    )
    priority = serializers.ChoiceField(
        choices=HelpRequest.PRIORITY_CHOICES,
        default='NORMAL',
        required=False,
        help_text='Priority level (default: NORMAL)'
    )
    
    class Meta:
        model = HelpRequest
        fields = [
            'id',
            'user_email',
            'user_name',
            'phone_number',
            'subject',
            'message',
            'category',
            'priority',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def validate(self, attrs):
        """Validate that user_email is provided if not authenticated"""
        request = self.context.get('request')
        
        # If not authenticated, user_email is required
        if not request or not request.user.is_authenticated:
            if not attrs.get('user_email'):
                raise serializers.ValidationError({
                    'user_email': 'Email address is required for anonymous requests.'
                })
        
        return attrs
    
    def validate_message(self, value):
        """Validate message length"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                'Message must be at least 10 characters long.'
            )
        if len(value) > 5000:
            raise serializers.ValidationError(
                'Message is too long. Maximum 5000 characters allowed.'
            )
        return value
    
    def validate_subject(self, value):
        """Validate subject length"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                'Subject must be at least 5 characters long.'
            )
        return value
    
    def create(self, validated_data):
        """Create help request with user association if authenticated"""
        request = self.context.get('request')
        
        # Auto-fill user information if authenticated
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
            if not validated_data.get('user_email'):
                validated_data['user_email'] = request.user.email
            if not validated_data.get('user_name'):
                validated_data['user_name'] = request.user.get_full_name()
            if not validated_data.get('phone_number'):
                validated_data['phone_number'] = request.user.phone_number
        
        return super().create(validated_data)


class HelpRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing help requests (admin view)"""
    
    user_email_display = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = HelpRequest
        fields = [
            'id',
            'user',
            'user_email',
            'user_email_display',
            'user_name',
            'subject',
            'category',
            'category_display',
            'priority',
            'priority_display',
            'status',
            'status_display',
            'n8n_workflow_triggered',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_email_display(self, obj):
        """Get user email display"""
        if obj.user:
            return obj.user.email
        return obj.user_email

