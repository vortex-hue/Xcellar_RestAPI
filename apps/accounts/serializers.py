from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import os

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data"""
    full_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    
    # Status fields for USER type
    isAddressSet = serializers.SerializerMethodField()
    
    # Status fields for COURIER type (only returned for couriers)
    isDeliveryOptionSet = serializers.SerializerMethodField()
    isPaymentInfoSet = serializers.SerializerMethodField()
    isBvnSet = serializers.SerializerMethodField()
    isApproved = serializers.SerializerMethodField()
    isDriverLicenseSet = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'user_type', 'date_joined', 
            'full_name', 'address', 'profile_image', 'profile_image_url',
            'isAddressSet', 'isDeliveryOptionSet', 'isPaymentInfoSet', 
            'isBvnSet', 'isApproved', 'isDriverLicenseSet'
        ]
        read_only_fields = ['id', 'email', 'phone_number', 'user_type', 'date_joined']
    
    def to_representation(self, instance):
        """Customize representation to exclude type-specific fields"""
        data = super().to_representation(instance)
        
        # Remove courier-specific fields for regular users
        if instance.user_type != 'COURIER':
            data.pop('isDeliveryOptionSet', None)
            data.pop('isPaymentInfoSet', None)
            data.pop('isBvnSet', None)
            data.pop('isApproved', None)
            data.pop('isDriverLicenseSet', None)
        
        # Remove user-specific fields for couriers
        if instance.user_type != 'USER':
            data.pop('isAddressSet', None)
        
        return data
    
    def get_full_name(self, obj):
        """Get full name from profile"""
        return obj.get_full_name()
    
    def get_address(self, obj):
        """Get address from profile"""
        if obj.user_type == 'USER' and hasattr(obj, 'user_profile'):
            return obj.user_profile.address
        elif obj.user_type == 'COURIER' and hasattr(obj, 'courier_profile'):
            return obj.courier_profile.address
        return None
    
    def get_profile_image(self, obj):
        """Get profile image path from profile"""
        if obj.user_type == 'USER' and hasattr(obj, 'user_profile'):
            return obj.user_profile.profile_image.url if obj.user_profile.profile_image else None
        elif obj.user_type == 'COURIER' and hasattr(obj, 'courier_profile'):
            return obj.courier_profile.profile_image.url if obj.courier_profile.profile_image else None
        return None
    
    def get_profile_image_url(self, obj):
        """Get full URL for profile image"""
        profile_image = self.get_profile_image(obj)
        if profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile_image)
            return profile_image
        return None
    
    def get_isAddressSet(self, obj):
        """Check if user has set their address"""
        if obj.user_type == 'USER' and hasattr(obj, 'user_profile'):
            address = obj.user_profile.address
            return bool(address and address.strip())
        return None
    
    def get_isDeliveryOptionSet(self, obj):
        """Check if courier has delivery options configured (at least one vehicle)"""
        if obj.user_type == 'COURIER':
            # Check if courier has at least one active vehicle
            return obj.vehicles.filter(is_active=True).exists()
        return None
    
    def get_isPaymentInfoSet(self, obj):
        """Check if courier has payment/bank account information set"""
        if obj.user_type == 'COURIER' and hasattr(obj, 'courier_profile'):
            profile = obj.courier_profile
            return bool(
                profile.bank_account_number and profile.bank_account_number.strip() and
                profile.bank_code and profile.bank_code.strip() and
                profile.account_name and profile.account_name.strip()
            )
        return None
    
    def get_isBvnSet(self, obj):
        """Check if courier has BVN set"""
        if obj.user_type == 'COURIER' and hasattr(obj, 'courier_profile'):
            bvn = obj.courier_profile.bvn
            return bool(bvn and bvn.strip())
        return None
    
    def get_isApproved(self, obj):
        """Check if courier is approved"""
        if obj.user_type == 'COURIER' and hasattr(obj, 'courier_profile'):
            return obj.courier_profile.approval_status == 'APPROVED'
        return None
    
    def get_isDriverLicenseSet(self, obj):
        """Check if courier has driver license added"""
        if obj.user_type == 'COURIER' and hasattr(obj, 'courier_profile'):
            try:
                # Check if driver license exists (OneToOne relationship)
                # Accessing the related object will raise AttributeError if it doesn't exist
                driver_license = obj.courier_profile.driver_license
                return True
            except AttributeError:
                # RelatedObjectDoesNotExist is a subclass of AttributeError
                return False
        return None


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer for user registration"""
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=True, max_length=20)
    password = serializers.CharField(required=True, write_only=True, min_length=8, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True, min_length=8)
    full_name = serializers.CharField(required=True, max_length=200)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match. Please ensure both password fields are identical.")
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            user_type='USER'
        )
        from apps.accounts.models import UserProfile
        UserProfile.objects.create(
            user=user,
            full_name=validated_data['full_name']
        )
        return user


class CourierRegistrationSerializer(serializers.Serializer):
    """Serializer for courier registration"""
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=True, max_length=20)
    password = serializers.CharField(required=True, write_only=True, min_length=8, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True, min_length=8)
    full_name = serializers.CharField(required=True, max_length=200)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match. Please ensure both password fields are identical.")
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            user_type='COURIER'
        )
        from apps.accounts.models import CourierProfile
        CourierProfile.objects.create(
            user=user,
            full_name=validated_data['full_name']
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user_type"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = user.user_type
        token['email'] = user.email
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        # Store user for use in view
        self.user = self.user
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated users)"""
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        validators=[validate_password],
        help_text='New password (minimum 8 characters)'
    )
    confirm_new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        help_text='Confirm new password'
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError("New passwords do not match. Please ensure both new password fields are identical.")
        return attrs


class PhoneNumberUpdateSerializer(serializers.Serializer):
    """Serializer for updating phone number"""
    phone_number = serializers.CharField(
        required=True,
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        help_text='New phone number in international format (e.g., +1234567890)'
    )
    
    def validate_phone_number(self, value):
        """Normalize phone number format"""
        # Ensure phone number starts with +
        if not value.startswith('+'):
            # If it doesn't start with +, assume it's a local number and prepend +
            value = '+' + value.lstrip('+')
        
        # Remove any spaces, dashes, or parentheses
        value = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        return value
    
    def validate(self, attrs):
        """Check if phone number is already in use"""
        phone_number = attrs['phone_number']
        user = self.context.get('request').user
        
        # Check if another user already has this phone number
        if User.objects.filter(phone_number=phone_number).exclude(pk=user.pk).exists():
            raise serializers.ValidationError({
                'phone_number': 'This phone number is already registered. Please use a different phone number or sign in with your existing account.'
            })
        
        # Check if user is trying to set the same phone number
        if user.phone_number == phone_number:
            raise serializers.ValidationError({
                'phone_number': 'This is already your current phone number. No changes needed.'
            })
        
        return attrs


class ProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating profile (address and profile image)"""
    address = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
        help_text='User address (optional)'
    )
    profile_image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text='Profile image (JPG, PNG, GIF, BMP, WEBP - max 5MB)'
    )
    
    def validate_profile_image(self, value):
        """Validate profile image"""
        if value:
            # Check file size (max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    'Profile image file size cannot exceed 5MB.'
                )
            
            # Check file extension
            ext = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    'Invalid file type. Allowed image types: JPG, JPEG, PNG, GIF, BMP, WEBP'
                )
        return value
