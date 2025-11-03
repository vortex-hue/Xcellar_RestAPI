from django.contrib import admin
from apps.orders.models import Order, TrackingHistory


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'tracking_number', 'sender', 'assigned_courier', 
                    'status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_status', 'parcel_type', 'created_at']
    search_fields = ['order_number', 'tracking_number', 'sender__email', 'recipient_name']
    readonly_fields = ['order_number', 'tracking_number', 'created_at', 'updated_at']
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'tracking_number', 'status')
        }),
        ('Parties', {
            'fields': ('sender', 'assigned_courier')
        }),
        ('Pickup Details', {
            'fields': ('pickup_address', 'pickup_latitude', 'pickup_longitude')
        }),
        ('Delivery Details', {
            'fields': ('dropoff_address', 'dropoff_latitude', 'dropoff_longitude')
        }),
        ('Recipient Information', {
            'fields': ('recipient_name', 'recipient_email', 'recipient_phone',
                      'recipient_alternate_phone', 'delivery_instructions',
                      'require_recipient_signature')
        }),
        ('Parcel Details', {
            'fields': ('parcel_type', 'parcel_description', 'parcel_condition',
                      'parcel_quantity', 'parcel_weight_kg', 'parcel_financial_worth',
                      'parcel_images')
        }),
        ('Financial Information', {
            'fields': ('delivery_fee', 'service_charge', 'insurance_fee',
                      'total_amount', 'payment_status', 'courier_payout')
        }),
        ('Tracking', {
            'fields': ('current_location', 'estimated_delivery_time')
        }),
        ('Courier Assignment', {
            'fields': ('offered_to_couriers', 'offer_expires_at')
        }),
        ('Timestamps', {
            'fields': ('picked_up_at', 'delivered_at', 'cancelled_at', 'created_at', 'updated_at')
        }),
        ('Metadata', {
            'fields': ('metadata', 'is_active')
        }),
    )


@admin.register(TrackingHistory)
class TrackingHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'location', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number', 'order__tracking_number']
    readonly_fields = ['created_at', 'updated_at']

