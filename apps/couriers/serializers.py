from rest_framework import serializers
from .models import Vehicle, DriverLicense
from datetime import datetime
import os


class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for vehicle data"""
    courier_email = serializers.EmailField(source='courier.email', read_only=True)
    courier_name = serializers.CharField(source='courier.get_full_name', read_only=True)
    
    # File field URLs for read operations
    registration_proof_url = serializers.SerializerMethodField()
    insurance_policy_proof_url = serializers.SerializerMethodField()
    road_worthiness_proof_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id',
            'courier',
            'courier_email',
            'courier_name',
            'vehicle_type',
            'ownership_condition',
            'manufacturer',
            'model',
            'year_of_manufacturing',
            'license_plate_number',
            'registration_proof',
            'registration_proof_url',
            'insurance_policy_proof',
            'insurance_policy_proof_url',
            'road_worthiness_proof',
            'road_worthiness_proof_url',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'courier', 'created_at', 'updated_at']
    
    def get_registration_proof_url(self, obj):
        """Get full URL for registration proof"""
        if obj.registration_proof:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.registration_proof.url)
            return obj.registration_proof.url
        return None
    
    def get_insurance_policy_proof_url(self, obj):
        """Get full URL for insurance policy proof"""
        if obj.insurance_policy_proof:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.insurance_policy_proof.url)
            return obj.insurance_policy_proof.url
        return None
    
    def get_road_worthiness_proof_url(self, obj):
        """Get full URL for road worthiness proof"""
        if obj.road_worthiness_proof:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.road_worthiness_proof.url)
            return obj.road_worthiness_proof.url
        return None
    
    def validate_registration_proof(self, value):
        """Validate registration proof file"""
        if value:
            return self._validate_file(value, 'registration_proof')
        return value
    
    def validate_insurance_policy_proof(self, value):
        """Validate insurance policy proof file"""
        if value:
            return self._validate_file(value, 'insurance_policy_proof')
        return value
    
    def validate_road_worthiness_proof(self, value):
        """Validate road worthiness proof file"""
        if value:
            return self._validate_file(value, 'road_worthiness_proof')
        return value
    
    def _validate_file(self, value, field_name):
        """Common file validation logic"""
        if value:
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    f'{field_name.replace("_", " ").title()} file size cannot exceed 10MB.'
                )
            
            # Check file extension
            ext = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f'Invalid file type for {field_name.replace("_", " ")}. '
                    f'Allowed types: PDF, DOC, DOCX, JPG, JPEG, PNG, GIF, BMP, WEBP'
                )
        return value
    
    def validate_license_plate_number(self, value):
        """Validate and normalize license plate format"""
        if not value:
            raise serializers.ValidationError("License plate number is required")
        # Normalize: uppercase and strip whitespace
        normalized = value.upper().strip()
        # Remove any extra spaces
        normalized = ' '.join(normalized.split())
        return normalized
    
    def validate_year_of_manufacturing(self, value):
        """Validate year is reasonable"""
        from datetime import datetime
        current_year = datetime.now().year
        if value < 1900:
            raise serializers.ValidationError("Year cannot be before 1900")
        if value > current_year + 1:
            raise serializers.ValidationError(
                f"Year cannot be in the future (max {current_year + 1})"
            )
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        # Check if license plate already exists (excluding current instance)
        license_plate = attrs.get('license_plate_number')
        if license_plate:
            queryset = Vehicle.objects.filter(license_plate_number=license_plate)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({
                    'license_plate_number': 'This license plate number is already registered.'
                })
        return attrs


class DriverLicenseSerializer(serializers.ModelSerializer):
    """Serializer for driver license"""
    courier_email = serializers.EmailField(source='courier_profile.user.email', read_only=True)
    courier_name = serializers.CharField(source='courier_profile.full_name', read_only=True)
    
    # URL fields for read operations
    front_page_url = serializers.SerializerMethodField()
    back_page_url = serializers.SerializerMethodField()
    vehicle_insurance_url = serializers.SerializerMethodField()
    vehicle_registration_url = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = DriverLicense
        fields = [
            'id',
            'courier_profile',
            'courier_email',
            'courier_name',
            'license_number',
            'issue_date',
            'expiry_date',
            'issuing_authority',
            'front_page',
            'front_page_url',
            'back_page',
            'back_page_url',
            'vehicle_insurance',
            'vehicle_insurance_url',
            'vehicle_registration',
            'vehicle_registration_url',
            'is_expired',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'courier_profile', 'created_at', 'updated_at']
    
    def get_front_page_url(self, obj):
        """Get full URL for front page"""
        if obj.front_page:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.front_page.url)
            return obj.front_page.url
        return None
    
    def get_back_page_url(self, obj):
        """Get full URL for back page"""
        if obj.back_page:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.back_page.url)
            return obj.back_page.url
        return None
    
    def get_vehicle_insurance_url(self, obj):
        """Get full URL for vehicle insurance"""
        if obj.vehicle_insurance:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.vehicle_insurance.url)
            return obj.vehicle_insurance.url
        return None
    
    def get_vehicle_registration_url(self, obj):
        """Get full URL for vehicle registration"""
        if obj.vehicle_registration:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.vehicle_registration.url)
            return obj.vehicle_registration.url
        return None
    
    def get_is_expired(self, obj):
        """Get license expiry status"""
        return obj.is_expired()
    
    def validate_front_page(self, value):
        """Validate front page file"""
        if value:
            return self._validate_file(value, 'front_page')
        return value
    
    def validate_back_page(self, value):
        """Validate back page file"""
        if value:
            return self._validate_file(value, 'back_page')
        return value
    
    def validate_vehicle_insurance(self, value):
        """Validate vehicle insurance file"""
        if value:
            return self._validate_file(value, 'vehicle_insurance')
        return value
    
    def validate_vehicle_registration(self, value):
        """Validate vehicle registration file"""
        if value:
            return self._validate_file(value, 'vehicle_registration')
        return value
    
    def validate_expiry_date(self, value):
        """Validate expiry date format (allows expired licenses)"""
        if value:
            # Allow expired licenses - they'll be marked as expired
            # No validation needed, just accept the date
            pass
        return value
    
    def validate_issue_date(self, value):
        """Validate issue date is reasonable"""
        if value:
            today = datetime.now().date()
            # Issue date shouldn't be in the future
            if value > today:
                raise serializers.ValidationError(
                    'Issue date cannot be in the future.'
                )
            # Issue date shouldn't be too old (more than 50 years ago)
            from datetime import timedelta
            min_date = today - timedelta(days=50*365)
            if value < min_date:
                raise serializers.ValidationError(
                    'Issue date seems too old. Please verify.'
                )
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        issue_date = attrs.get('issue_date')
        expiry_date = attrs.get('expiry_date')
        
        # If both dates provided, ensure expiry is after issue
        if issue_date and expiry_date:
            if expiry_date <= issue_date:
                raise serializers.ValidationError({
                    'expiry_date': 'Expiry date must be after issue date.'
                })
        
        return attrs
    
    def _validate_file(self, value, field_name):
        """Common file validation logic"""
        if value:
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    f'{field_name.replace("_", " ").title()} file size cannot exceed 10MB.'
                )
            
            # Check file extension
            ext = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f'Invalid file type for {field_name.replace("_", " ")}. '
                    f'Allowed types: PDF, DOC, DOCX, JPG, JPEG, PNG, GIF, BMP, WEBP'
                )
        return value


