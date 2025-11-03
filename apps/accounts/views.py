from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging

from .serializers import (
    UserRegistrationSerializer,
    CourierRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    PasswordChangeSerializer,
    PhoneNumberUpdateSerializer,
    ProfileUpdateSerializer
)

logger = logging.getLogger(__name__)


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
    description='Register a new regular customer account. JWT tokens are automatically generated and included in the response.',
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
                        'full_name': 'John Doe',
                    },
                    'tokens': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
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
                'full_name': 'John Doe',
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
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        return Response(
            {
                'message': 'User registered successfully',
                'user': UserSerializer(user, context={'request': request}).data,
                'tokens': {
                    'access': access_token,
                    'refresh': refresh_token
                }
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Register Courier',
    description='Register a new courier/driver account. JWT tokens are automatically generated and included in the response.',
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
                        'full_name': 'Jane Driver',
                    },
                    'tokens': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
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
                'full_name': 'Jane Driver',
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
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        return Response(
            {
                'message': 'Courier registered successfully',
                'user': UserSerializer(user, context={'request': request}).data,
                'tokens': {
                    'access': access_token,
                    'refresh': refresh_token
                }
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Change Password',
    description='Change password for authenticated users/couriers. Requires JWT authentication. No need to provide current password.',
    request=PasswordChangeSerializer,
    responses={
        200: {
            'description': 'Password changed successfully',
            'examples': {
                'application/json': {
                    'message': 'Password changed successfully',
                }
            }
        },
        400: {'description': 'Validation error - passwords don\'t match or invalid'},
        401: {'description': 'Authentication required - provide valid JWT token'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Change Password Request',
            value={
                'new_password': 'newpassword123',
                'confirm_new_password': 'newpassword123',
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/h', method='POST')
def change_password(request):
    """
    Change password for authenticated user.
    POST /api/v1/auth/password/change/
    """
    serializer = PasswordChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    new_password = serializer.validated_data['new_password']
    
    try:
        with transaction.atomic():
            user = request.user
            user.set_password(new_password)
            user.save()
            
        logger.info(f"Password changed successfully for user {user.email}")
        
        return Response(
            {
                'message': 'Password changed successfully',
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Failed to change password for user {request.user.email}: {e}")
        return Response(
            {'error': 'Failed to change password. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
                'full_name': 'John Doe',
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
                'full_name': 'Jane Driver',
            },
            response_only=True,
        ),
    ],
)
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
                'full_name': 'John Doe',
                'address': '123 Main St, City, Country',
                'profile_image': '/media/profiles/user/profile_1.jpg',
                'profile_image_url': 'http://localhost:8000/media/profiles/user/profile_1.jpg',
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
                'full_name': 'Jane Driver',
                'address': '456 Oak Ave, City, Country',
                'profile_image': '/media/profiles/courier/profile_2.jpg',
                'profile_image_url': 'http://localhost:8000/media/profiles/courier/profile_2.jpg',
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
    serializer = UserSerializer(request.user, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    summary='Update Phone Number',
    description='Update phone number for authenticated users/couriers. Requires JWT authentication. Phone number must be unique and in international format.',
    request=PhoneNumberUpdateSerializer,
    responses={
        200: {
            'description': 'Phone number updated successfully',
            'examples': {
                'application/json': {
                    'message': 'Phone number updated successfully',
                    'phone_number': '+1234567890',
                }
            }
        },
        400: {'description': 'Validation error - phone number already in use or invalid format'},
        401: {'description': 'Authentication required - provide valid JWT token'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Update Phone Number Request',
            value={
                'phone_number': '+1234567890',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Update Phone Number Response',
            value={
                'message': 'Phone number updated successfully',
                'phone_number': '+1234567890',
            },
            response_only=True,
        ),
    ],
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='5/h', method=['PUT', 'PATCH'])
def update_phone_number(request):
    """
    Update phone number for authenticated user.
    PUT/PATCH /api/v1/auth/phone/update/
    """
    serializer = PhoneNumberUpdateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    new_phone_number = serializer.validated_data['phone_number']
    
    try:
        with transaction.atomic():
            user = request.user
            old_phone_number = user.phone_number
            user.phone_number = new_phone_number
            user.save(update_fields=['phone_number'])
            
        logger.info(f"Phone number updated for user {user.email}: {old_phone_number} -> {new_phone_number}")
        
        return Response(
            {
                'message': 'Phone number updated successfully',
                'phone_number': new_phone_number,
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Failed to update phone number for user {request.user.email}: {e}")
        return Response(
            {'error': 'Failed to update phone number. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Authentication'],
    summary='Update Profile',
    description='Update profile information (address and profile image) for authenticated users/couriers. Requires JWT authentication. Supports file uploads.',
    request=ProfileUpdateSerializer,
    responses={
        200: {
            'description': 'Profile updated successfully',
            'examples': {
                'application/json': {
                    'message': 'Profile updated successfully',
                    'address': '123 Main St, City, Country',
                    'profile_image_url': 'http://localhost:8000/media/profiles/user/profile_1.jpg',
                }
            }
        },
        400: {'description': 'Validation error - invalid image format or size'},
        401: {'description': 'Authentication required - provide valid JWT token'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Update Profile Request (with image)',
            value={
                'address': '123 Main St, City, Country',
                'profile_image': '<file>',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Update Profile Request (address only)',
            value={
                'address': '123 Main St, City, Country',
            },
            request_only=True,
        ),
    ],
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/h', method=['PUT', 'PATCH'])
def update_profile(request):
    """
    Update profile (address and profile image) for authenticated user.
    PUT/PATCH /api/v1/auth/profile/update/
    """
    serializer = ProfileUpdateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    try:
        with transaction.atomic():
            # Get the appropriate profile
            if user.user_type == 'USER':
                profile = user.user_profile
            elif user.user_type == 'COURIER':
                profile = user.courier_profile
            else:
                return Response(
                    {'error': 'Invalid user type.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update address if provided
            if 'address' in serializer.validated_data:
                profile.address = serializer.validated_data.get('address') or None
                profile.save(update_fields=['address'])
            
            # Update profile image if provided
            if 'profile_image' in serializer.validated_data:
                # Delete old image if exists
                if profile.profile_image:
                    profile.profile_image.delete(save=False)
                profile.profile_image = serializer.validated_data['profile_image']
                profile.save(update_fields=['profile_image'])
            
        logger.info(f"Profile updated for user {user.email}")
        
        # Return updated profile data
        user_serializer = UserSerializer(user, context={'request': request})
        
        return Response(
            {
                'message': 'Profile updated successfully',
                'address': profile.address,
                'profile_image_url': user_serializer.data.get('profile_image_url'),
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Failed to update profile for user {user.email}: {e}")
        return Response(
            {'error': 'Failed to update profile. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    tags=['Authentication'],
    summary='Logout',
    description='Logout user by blacklisting the refresh token. The access token will expire naturally. All refresh tokens associated with the user can be optionally blacklisted.',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'refresh': {
                    'type': 'string',
                    'description': 'Refresh token to blacklist (optional - if not provided, blacklists all tokens for user)',
                    'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                },
                'blacklist_all': {
                    'type': 'boolean',
                    'description': 'If true, blacklists all refresh tokens for the user (default: false)',
                    'example': False,
                },
            },
        }
    },
    responses={
        200: {
            'description': 'Logout successful',
            'examples': {
                'application/json': {
                    'message': 'Successfully logged out',
                    'tokens_blacklisted': 1,
                }
            }
        },
        400: {'description': 'Invalid refresh token format'},
        401: {'description': 'Authentication required - provide valid JWT token'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Logout Request (with refresh token)',
            value={
                'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Logout Request (blacklist all tokens)',
            value={
                'blacklist_all': True,
            },
            request_only=True,
        ),
        OpenApiExample(
            'Logout Response',
            value={
                'message': 'Successfully logged out',
                'tokens_blacklisted': 1,
            },
            response_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/h', method='POST')
def logout(request):
    """
    Logout user by blacklisting refresh token(s).
    POST /api/v1/auth/logout/
    
    Can blacklist:
    - Specific refresh token (if provided)
    - All refresh tokens for the user (if blacklist_all=True)
    """
    try:
        refresh_token = request.data.get('refresh', '').strip()
        blacklist_all = request.data.get('blacklist_all', False)
        
        tokens_blacklisted = 0
        
        with transaction.atomic():
            if blacklist_all:
                # Blacklist all outstanding tokens for this user (ignore refresh token if provided)
                outstanding_tokens = OutstandingToken.objects.filter(user=request.user)
                for token in outstanding_tokens:
                    # Check if already blacklisted
                    if not BlacklistedToken.objects.filter(token=token).exists():
                        BlacklistedToken.objects.create(token=token)
                        tokens_blacklisted += 1
                
                logger.info(f"Blacklisted all tokens ({tokens_blacklisted}) for user {request.user.email}")
            elif refresh_token:
                # Blacklist specific refresh token
                try:
                    token = RefreshToken(refresh_token)
                    # Verify token belongs to authenticated user
                    if token.get('user_id') != request.user.id:
                        return Response(
                            {'error': 'Refresh token does not belong to authenticated user.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    token.blacklist()
                    tokens_blacklisted = 1
                    logger.info(f"Blacklisted refresh token for user {request.user.email}")
                except Exception as e:
                    logger.warning(f"Failed to blacklist token for user {request.user.email}: {e}")
                    return Response(
                        {'error': 'Invalid refresh token provided.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # No refresh token provided and blacklist_all=False
                # Blacklist all tokens for the user as fallback
                outstanding_tokens = OutstandingToken.objects.filter(user=request.user)
                for token in outstanding_tokens:
                    if not BlacklistedToken.objects.filter(token=token).exists():
                        BlacklistedToken.objects.create(token=token)
                        tokens_blacklisted += 1
                
                logger.info(f"Blacklisted all tokens ({tokens_blacklisted}) for user {request.user.email} (no refresh token provided)")
        
        return Response(
            {
                'message': 'Successfully logged out',
                'tokens_blacklisted': tokens_blacklisted,
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Failed to logout user {request.user.email}: {e}")
        return Response(
            {'error': 'Failed to logout. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

