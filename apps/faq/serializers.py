from rest_framework import serializers
from .models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQ data"""
    
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True,
        help_text='Human-readable category name'
    )
    
    class Meta:
        model = FAQ
        fields = [
            'id',
            'question',
            'answer',
            'category',
            'category_display',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

