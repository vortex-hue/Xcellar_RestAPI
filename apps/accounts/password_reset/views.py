from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.conf import settings
from datetime import timedelta
import logging

from .models import PasswordResetToken
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from .services import send_password_reset_email
from apps.core.response import success_response, error_response, validation_error_response

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Authentication'],
    summary='Request Password Reset',
    description='Request a password reset email. An email with reset link will be sent to the provided email address.',
    request=PasswordResetRequestSerializer,
    responses={
        200: {
            'description': 'Password reset email sent successfully',
            'examples': {
                'application/json': {
                    'message': 'Password reset email sent successfully',
                    'email': 'u***@example.com',
                }
            }
        },
        400: {'description': 'Validation error'},
        429: {'description': 'Rate limit exceeded'},
    },
    examples=[
        OpenApiExample(
            'Password Reset Request',
            value={
                'email': 'user@example.com',
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/h', method='POST', block=False)
@ratelimit(key='post:email', rate='3/h', method='POST', block=False)
def password_reset_request(request):
    """
    Request password reset email.
    POST /api/v1/auth/password/reset/request/
    """
    if getattr(request, 'limited', False):
        retry_after_minutes = 12
        return error_response(
            f'Too many password reset requests. Please wait {retry_after_minutes} minutes before trying again.',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return validation_error_response(serializer.errors, message='Validation error')
    
    email = serializer.validated_data['email'].lower().strip()
    
    # Find user by email (don't reveal if email exists)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if email exists for security
        return success_response(
            data={'email': _mask_email(email)},
            message='If an account exists with this email, a password reset link has been sent.'
        )
    
    # Generate reset token with transaction to ensure atomicity
    expires_at = timezone.now() + timedelta(minutes=getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY', 15))
    
    try:
        with transaction.atomic():
            # Invalidate any existing unused tokens for this user
            PasswordResetToken.objects.filter(
                user=user,
                is_used=False
            ).update(is_used=True)
            
            # Create new reset token
            reset_token = PasswordResetToken.objects.create(
                user=user,
                email=email,
                expires_at=expires_at
            )
            
            # Send reset email (if this fails, transaction will rollback)
            send_password_reset_email(user, reset_token.token)
            
    except Exception as e:
        # Log error but don't reveal it to user
        logger.error(f"Failed to process password reset request for {email}: {e}")
        return error_response('Unable to send password reset email at this time. Please try again later or contact support.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return success_response(
        data={'email': _mask_email(email)},
        message='Password reset email sent successfully'
    )


@extend_schema(
    tags=['Authentication'],
    summary='Confirm Password Reset',
    description='Reset password using token from email. Token expires after 15 minutes and can only be used once.',
    request=PasswordResetConfirmSerializer,
    responses={
        200: {
            'description': 'Password reset successfully',
            'examples': {
                'application/json': {
                    'message': 'Password reset successfully',
                }
            }
        },
        400: {'description': 'Invalid token or validation error'},
    },
    examples=[
        OpenApiExample(
            'Password Reset Confirm',
            value={
                'token': '550e8400-e29b-41d4-a716-446655440000',
                'password': 'newpassword123',
                'password_confirm': 'newpassword123',
            },
            request_only=True,
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/h', method='POST', block=False)
def password_reset_confirm(request):
    """
    Confirm password reset with token.
    POST /api/v1/auth/password/reset/confirm/
    """
    if getattr(request, 'limited', False):
        retry_after_minutes = 10
        return error_response(
            f'Too many password reset attempts. Please wait {retry_after_minutes} minutes before trying again.',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return validation_error_response(serializer.errors, message='Validation error')
    
    token = serializer.validated_data['token']
    password = serializer.validated_data['password']
    
    # Find token
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return error_response('Invalid or expired password reset link. Please request a new password reset.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Validate token
    if not reset_token.is_valid():
        if reset_token.is_used:
            return error_response('This password reset link has already been used. Please request a new password reset.', status_code=status.HTTP_400_BAD_REQUEST)
        elif reset_token.is_expired():
            return error_response('Password reset link has expired. Please request a new password reset link.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Reset password with transaction
    try:
        with transaction.atomic():
            user = reset_token.user
            user.set_password(password)
            user.save()
            
            # Mark token as used
            reset_token.mark_as_used()
    except Exception as e:
        logger.error(f"Failed to reset password for user {reset_token.user.email}: {e}")
        return error_response('Unable to reset password at this time. Please check your details and try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return success_response(message='Password reset successfully. You can now login with your new password.')


def _mask_email(email):
    """Mask email for privacy (e.g., u***@example.com)"""
    if not email or '@' not in email:
        return email
    try:
        local, domain = email.split('@', 1)
        if len(local) <= 1:
            masked_local = '*'
        else:
            masked_local = local[0] + '*' * (len(local) - 1)
        return f"{masked_local}@{domain}"
    except Exception:
        return email
