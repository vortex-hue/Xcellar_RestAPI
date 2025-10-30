from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .serializers import (
    UserRegistrationSerializer,
    CourierRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view with rate limiting.
    Obtain JWT access and refresh tokens by providing email and password.
    """
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        tags=['Authentication'],
        summary='Login',
        description='Authenticate user and obtain JWT access and refresh tokens. Use the access token for subsequent API requests.',
        request=CustomTokenObtainPairSerializer,
        responses={
            200: {
                'description': 'Successful authentication',
                'examples': {
                    'application/json': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    }
                }
            },
            401: {'description': 'Invalid credentials'},
            429: {'description': 'Rate limit exceeded (5 requests per minute)'},
        },
        examples=[
            OpenApiExample(
                'Login Request',
                value={
                    'email': 'user@example.com',
                    'password': 'password123',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Login Response',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                },
                response_only=True,
            ),
        ],
    )
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view with documentation.
    Refresh JWT access token using refresh token.
    """
    @extend_schema(
        tags=['Authentication'],
        summary='Refresh Token',
        description='Refresh your JWT access token using a valid refresh token. Use this when your access token expires.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {
                        'type': 'string',
                        'description': 'Refresh token obtained from login',
                        'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    },
                },
                'required': ['refresh'],
            }
        },
        responses={
            200: {
                'description': 'New access token generated',
                'examples': {
                    'application/json': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    }
                }
            },
            401: {'description': 'Invalid or expired refresh token'},
        },
        examples=[
            OpenApiExample(
                'Refresh Token Request',
                value={
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Refresh Token Response',
                value={
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    tags=['Authentication'],
    summary='Register User',
    description='Register a new regular customer account. After registration, use the login endpoint to obtain JWT tokens.',
    request=UserRegistrationSerializer,
    responses={
        201: {
            'description': 'User registered successfully',
            'examples': {
                'application/json': {
                    'message': 'User registered successfully',
                    'user': {
                        'id': 1,
                        'email': 'user@example.com',
                        'phone_number': '+1234567890',
                        'user_type': 'USER',
                        'date_joined': '2025-10-30T18:00:00Z',
                        'profile': {
                            'first_name': 'John',
                            'last_name': 'Doe',
                        }
                    }
                }
            }
        },
        400: {'description': 'Validation error - check request body'},
        429: {'description': 'Rate limit exceeded (10 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'Registration Request',
            value={
                'email': 'user@example.com',
                'phone_number': '+1234567890',
                'password': 'password123',
                'password_confirm': 'password123',
                'first_name': 'John',
                'last_name': 'Doe',
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/h', method='POST')
def register_user(request):
    """
    Register a new regular customer.
    POST /api/v1/auth/register/user/
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                'message': 'User registered successfully',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Register Courier',
    description='Register a new courier/driver account. After registration, use the login endpoint to obtain JWT tokens.',
    request=CourierRegistrationSerializer,
    responses={
        201: {
            'description': 'Courier registered successfully',
            'examples': {
                'application/json': {
                    'message': 'Courier registered successfully',
                    'user': {
                        'id': 2,
                        'email': 'courier@example.com',
                        'phone_number': '+1234567891',
                        'user_type': 'COURIER',
                        'date_joined': '2025-10-30T18:00:00Z',
                        'profile': {
                            'first_name': 'Jane',
                            'last_name': 'Driver',
                            'is_available': False,
                        }
                    }
                }
            }
        },
        400: {'description': 'Validation error - check request body'},
        429: {'description': 'Rate limit exceeded (10 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'Courier Registration Request',
            value={
                'email': 'courier@example.com',
                'phone_number': '+1234567891',
                'password': 'password123',
                'password_confirm': 'password123',
                'first_name': 'Jane',
                'last_name': 'Driver',
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/h', method='POST')
def register_courier(request):
    """
    Register a new courier.
    POST /api/v1/auth/register/courier/
    """
    serializer = CourierRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                'message': 'Courier registered successfully',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Get User Profile',
    description='Retrieve the authenticated user\'s profile information. Requires JWT authentication.',
    responses={
        200: UserSerializer,
        401: {'description': 'Authentication required - provide valid JWT token'},
        429: {'description': 'Rate limit exceeded (100 requests per hour)'},
    },
    examples=[
        OpenApiExample(
            'User Profile Response (Regular User)',
            value={
                'id': 1,
                'email': 'user@example.com',
                'phone_number': '+1234567890',
                'user_type': 'USER',
                'date_joined': '2025-10-30T18:00:00Z',
                'profile': {
                    'first_name': 'John',
                    'last_name': 'Doe',
                }
            },
            response_only=True,
        ),
        OpenApiExample(
            'Courier Profile Response',
            value={
                'id': 2,
                'email': 'courier@example.com',
                'phone_number': '+1234567891',
                'user_type': 'COURIER',
                'date_joined': '2025-10-30T18:00:00Z',
                'profile': {
                    'first_name': 'Jane',
                    'last_name': 'Driver',
                    'is_available': False,
                }
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='100/h', method='GET')
def user_profile(request):
    """
    Get current user profile.
    GET /api/v1/auth/profile/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)

