from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator
from decimal import Decimal

from apps.core.models import AbstractBaseModel


def validate_image_file(value):
    """Validate image file types"""
    import os
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    if ext not in allowed_extensions:
        from django.core.exceptions import ValidationError
        raise ValidationError(
            f'File type not allowed. Allowed image types: JPG, JPEG, PNG, GIF, BMP, WEBP'
        )


class UserManager(BaseUserManager):
    """Custom user manager"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with user_type differentiation.
    """
    USER_TYPE_CHOICES = [
        ('USER', 'Regular Customer'),
        ('COURIER', 'Courier/Driver'),
    ]

    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def get_full_name(self):
        if self.user_type == 'USER' and hasattr(self, 'user_profile'):
            return self.user_profile.full_name
        elif self.user_type == 'COURIER' and hasattr(self, 'courier_profile'):
            return self.courier_profile.full_name
        return self.email

    def get_short_name(self):
        if self.user_type == 'USER' and hasattr(self, 'user_profile'):
            return self.user_profile.full_name.split()[0] if self.user_profile.full_name else self.email
        elif self.user_type == 'COURIER' and hasattr(self, 'courier_profile'):
            return self.courier_profile.full_name.split()[0] if self.courier_profile.full_name else self.email
        return self.email


class UserProfile(AbstractBaseModel):
    """
    Profile for regular customers.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='user_profile'
    )
    full_name = models.CharField(max_length=200, default='')
    address = models.TextField(blank=True, null=True, help_text='User address')
    profile_image = models.ImageField(
        upload_to='profiles/user/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text='User profile image'
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Available balance (always rounded to 2 decimal places)'
    )
    # Add more customer-specific fields as needed

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.full_name} - {self.user.email}"


class CourierProfile(AbstractBaseModel):
    """
    Profile for couriers/drivers.
    """
    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='courier_profile'
    )
    full_name = models.CharField(max_length=200, default='')
    license_number = models.CharField(max_length=50, blank=True, null=True)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    vehicle_registration = models.CharField(max_length=50, blank=True, null=True)
    is_available = models.BooleanField(default=False)
    current_location = models.JSONField(null=True, blank=True)
    address = models.TextField(blank=True, null=True, help_text='Courier address')
    profile_image = models.ImageField(
        upload_to='profiles/courier/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text='Courier profile image'
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Available balance (always rounded to 2 decimal places)'
    )
    
    # Bank Verification Number
    bvn = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        help_text='Bank Verification Number (11 digits)'
    )
    
    # Bank Account Information
    bank_account_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Bank account number'
    )
    bank_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='Bank code (e.g., from Paystack)'
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Bank name'
    )
    account_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Account holder name'
    )
    
    # Approval Status
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='PENDING',
        help_text='Courier approval status for operations'
    )
    approval_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notes from admin regarding approval/rejection'
    )
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Date and time when courier was approved'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_couriers',
        help_text='Admin user who approved the courier',
        limit_choices_to={'is_staff': True}
    )

    class Meta:
        db_table = 'courier_profiles'
        verbose_name = 'Courier Profile'
        verbose_name_plural = 'Courier Profiles'

    def __str__(self):
        return f"{self.full_name} - {self.user.email}"

