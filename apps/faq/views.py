from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import FAQ
from .serializers import FAQSerializer


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for FAQ.
    Only returns active FAQs.
    Public endpoint - no authentication required.
    """
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]  # Public endpoint
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['question', 'answer']  # Search in question and answer
    ordering_fields = ['order', 'created_at', 'updated_at']
    ordering = ['order', 'created_at']  # Default ordering
    
    def get_queryset(self):
        """Return only active FAQs, optionally filtered by category"""
        queryset = FAQ.objects.filter(is_active=True)
        
        # Filter by category if provided
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    @extend_schema(
        tags=['FAQ'],
        summary='List FAQs',
        description='Retrieve a list of all active frequently asked questions. Supports filtering by category and searching.',
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter FAQs by category (GENERAL, ACCOUNT, ORDERS, PAYMENT, COURIER, TECHNICAL, OTHER)',
                required=False,
                enum=['GENERAL', 'ACCOUNT', 'ORDERS', 'PAYMENT', 'COURIER', 'TECHNICAL', 'OTHER'],
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in question and answer fields',
                required=False,
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order results by field (order, created_at, updated_at). Prefix with "-" for descending.',
                required=False,
            ),
        ],
        responses={
            200: FAQSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                'List FAQs Response',
                value=[
                    {
                        'id': 1,
                        'question': 'How do I create an account?',
                        'answer': 'You can create an account by clicking on the Sign Up button...',
                        'category': 'ACCOUNT',
                        'category_display': 'Account & Profile',
                        'order': 1,
                        'created_at': '2025-10-30T18:00:00Z',
                        'updated_at': '2025-10-30T18:00:00Z',
                    },
                    {
                        'id': 2,
                        'question': 'What payment methods do you accept?',
                        'answer': 'We accept credit cards, debit cards, and mobile payments...',
                        'category': 'PAYMENT',
                        'category_display': 'Payment & Billing',
                        'order': 2,
                        'created_at': '2025-10-30T18:00:00Z',
                        'updated_at': '2025-10-30T18:00:00Z',
                    },
                ],
                response_only=True,
            ),
        ],
    )
    @method_decorator(ratelimit(key='ip', rate='100/h', method='GET'))
    def list(self, request, *args, **kwargs):
        """List all active FAQs"""
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        tags=['FAQ'],
        summary='Get FAQ',
        description='Retrieve a specific FAQ by ID. Only active FAQs are accessible.',
        responses={
            200: FAQSerializer,
            404: {'description': 'FAQ not found or inactive'},
        },
        examples=[
            OpenApiExample(
                'Get FAQ Response',
                value={
                    'id': 1,
                    'question': 'How do I create an account?',
                    'answer': 'You can create an account by clicking on the Sign Up button and providing your email address, phone number, and password. After registration, you will receive a verification email.',
                    'category': 'ACCOUNT',
                    'category_display': 'Account & Profile',
                    'order': 1,
                    'created_at': '2025-10-30T18:00:00Z',
                    'updated_at': '2025-10-30T18:00:00Z',
                },
                response_only=True,
            ),
        ],
    )
    @method_decorator(ratelimit(key='ip', rate='100/h', method='GET'))
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific FAQ"""
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        tags=['FAQ'],
        summary='List FAQ Categories',
        description='Get a list of all available FAQ categories with their counts.',
        responses={
            200: {
                'description': 'List of categories with counts',
                'examples': {
                    'application/json': {
                        'categories': [
                            {'code': 'GENERAL', 'name': 'General', 'count': 5},
                            {'code': 'ACCOUNT', 'name': 'Account & Profile', 'count': 3},
                            {'code': 'PAYMENT', 'name': 'Payment & Billing', 'count': 4},
                        ]
                    }
                }
            }
        },
    )
    @action(detail=False, methods=['get'])
    @method_decorator(ratelimit(key='ip', rate='100/h', method='GET'))
    def categories(self, request):
        """Get all FAQ categories with counts"""
        categories = []
        for category_code, category_name in FAQ.CATEGORY_CHOICES:
            count = FAQ.objects.filter(category=category_code, is_active=True).count()
            categories.append({
                'code': category_code,
                'name': category_name,
                'count': count,
            })
        
        return Response({'categories': categories}, status=status.HTTP_200_OK)

