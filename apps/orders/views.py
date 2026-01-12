from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.response import success_response, error_response, created_response, validation_error_response, not_found_response
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Q
import random
import logging

from apps.orders.models import Order, TrackingHistory
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    TrackingHistorySerializer
)
from apps.core.permissions import IsUser, IsCourier
from apps.accounts.models import User

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Orders'],
    summary='Create Order',
    description='Create a new parcel order',
    request=OrderCreateSerializer,
    responses={201: OrderDetailSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsUser])
def create_order(request):
    """Create a new parcel order"""
    serializer = OrderCreateSerializer(data=request.data)
    if serializer.is_valid():
        order = serializer.save(sender=request.user, status='PENDING')
        
        # Create initial tracking entry
        TrackingHistory.objects.create(
            order=order,
            status='PENDING',
            notes='Order created and awaiting confirmation'
        )
        
        return created_response(data={'order': OrderDetailSerializer(order).data}, message='Order created successfully')
    return validation_error_response(serializer.errors, message='Validation error')


@extend_schema(
    tags=['Orders'],
    summary='Confirm Order',
    description='Confirm order and make it available to couriers',
    responses={200: OrderDetailSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsUser])
def confirm_order(request, order_id):
    """Confirm order and make it available to couriers"""
    try:
        order = Order.objects.get(id=order_id, sender=request.user)
    except Order.DoesNotExist:
        return not_found_response('Order not found. Please check the order ID and try again.')
    
    if order.status != 'PENDING':
        return error_response(f'This order is already {order.get_status_display().lower()}.', status_code=status.HTTP_400_BAD_REQUEST)
    
    if order.payment_status != 'PAID':
        return error_response('Order must be paid before it can be confirmed and sent to couriers.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Update order status to available
    order.status = 'AVAILABLE'
    order.save()
    
    # Create tracking entry
    TrackingHistory.objects.create(
        order=order,
        status='AVAILABLE',
        notes='Order confirmed and made available to couriers'
    )
    
    # Assign to couriers (simple random selection)
    assign_order_to_couriers(order)
    return success_response(data=OrderDetailSerializer(order).data, message='Order confirmed successfully')


def assign_order_to_couriers(order):
    """
    Assign order to random couriers for pickup.
    Simple random selection algorithm.
    """
    # Get available couriers
    available_couriers = User.objects.filter(
        user_type='COURIER',
        is_active=True
    ).exclude(id__in=order.offered_to_couriers)
    
    # Select random 5 couriers (or all if less than 5)
    num_to_select = min(5, available_couriers.count())
    if num_to_select > 0:
        selected_couriers = random.sample(list(available_couriers), num_to_select)
        order.offered_to_couriers = [c.id for c in selected_couriers]
        order.offer_expires_at = timezone.now() + timezone.timedelta(hours=24)
        order.save()
        
        # Create tracking entries for each courier offer
        for courier in selected_couriers:
            TrackingHistory.objects.create(
                order=order,
                status='AVAILABLE',
                notes=f'Order offered to courier: {courier.email}'
            )


@extend_schema(
    tags=['Orders'],
    summary='List Orders',
    description='List user orders with filtering',
    responses={200: OrderListSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_orders(request):
    """List orders for authenticated user"""
    user = request.user
    queryset = Order.objects.all()
    
    # Filter based on user type
    if user.user_type == 'USER':
        queryset = queryset.filter(sender=user)
    elif user.user_type == 'COURIER':
        queryset = queryset.filter(assigned_courier=user)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    serializer = OrderListSerializer(queryset, many=True)
    return success_response(data={'orders': serializer.data})


@extend_schema(
    tags=['Orders'],
    summary='Order Detail',
    description='Get order details with tracking history',
    responses={200: OrderDetailSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """Get order details"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return not_found_response('Order not found. Please check the order ID and try again.')
    
    # Check permission
    user = request.user
    if user.user_type == 'USER' and order.sender != user:
        return error_response('You do not have permission to access this order.', status_code=status.HTTP_403_FORBIDDEN)
    elif user.user_type == 'COURIER' and order.assigned_courier != user:
        return error_response('You do not have permission to access this order.', status_code=status.HTTP_403_FORBIDDEN)
    
    serializer = OrderDetailSerializer(order)
    return success_response(data={'order': serializer.data})


@extend_schema(
    tags=['Orders'],
    summary='Track Order',
    description='Get tracking history for an order',
    responses={200: TrackingHistorySerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_order(request, order_id):
    """Get tracking history for an order"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return not_found_response('Order not found. Please check the order ID and try again.')
    
    # Check permission
    user = request.user
    if user.user_type == 'USER' and order.sender != user:
        return error_response('You do not have permission to access this order.', status_code=status.HTTP_403_FORBIDDEN)
    elif user.user_type == 'COURIER' and order.assigned_courier != user:
        return error_response('You do not have permission to access this order.', status_code=status.HTTP_403_FORBIDDEN)
    
    tracking = order.tracking_history.all()
    serializer = TrackingHistorySerializer(tracking, many=True)
    return success_response(data={'tracking_history': serializer.data})


@extend_schema(
    tags=['Couriers'],
    summary='List Available Orders',
    description='List orders available for courier pickup',
    responses={200: OrderListSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCourier])
def available_orders(request):
    """List orders available for courier to accept"""
    courier_id = request.user.id
    
    # Find orders where this courier is in the offered_to_couriers list
    # We need to check each order's JSON field manually since we can't query JSON directly in all DB backends
    all_orders = Order.objects.filter(
        status='AVAILABLE',
        assigned_courier__isnull=True
    )[:100]  # Limit to 100 for performance
    
    # Filter orders where courier_id is in the offered_to_couriers list
    available_orders_list = [
        order for order in all_orders 
        if courier_id in (order.offered_to_couriers or [])
    ]
    
    serializer = OrderListSerializer(available_orders_list, many=True)
    return success_response(data={'orders': serializer.data})


@extend_schema(
    tags=['Couriers'],
    summary='Accept Order',
    description='Accept an order for delivery (atomic operation)',
    responses={200: OrderDetailSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCourier])
def accept_order(request, order_id):
    """Accept an order for delivery"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return not_found_response('Order not found. Please check the order ID and try again.')
    
    # Atomic acceptance with select_for_update to prevent race conditions
    with db_transaction.atomic():
        # Lock the order row
        order = Order.objects.select_for_update().get(id=order_id)
        
        # Check if order is available
        if order.status != 'AVAILABLE':
            return error_response('This order is no longer available for acceptance.', status_code=status.HTTP_400_BAD_REQUEST)
        
        # Check if already assigned
        if order.assigned_courier is not None:
            return error_response('This order has already been assigned to another courier.', status_code=status.HTTP_400_BAD_REQUEST)
        
        # Assign to this courier
        order.assigned_courier = request.user
        order.status = 'ACCEPTED'
        order.save()
        
        # Create tracking entry
        TrackingHistory.objects.create(
            order=order,
            status='ACCEPTED',
            notes=f'Order accepted by courier: {request.user.email}'
        )
    
    serializer = OrderDetailSerializer(order)
    return success_response(data={'order': serializer.data})


@extend_schema(
    tags=['Couriers'],
    summary='Reject Order',
    description='Reject an offered order',
    responses={200: {'message': 'Order rejected'}}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCourier])
def reject_order(request, order_id):
    """Reject an offered order"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return not_found_response('Order not found. Please check the order ID and try again.')
    
    # Remove courier from offered list
    offered_list = order.offered_to_couriers or []
    if request.user.id in offered_list:
        offered_list = [cid for cid in offered_list if cid != request.user.id]
        order.offered_to_couriers = offered_list
        order.save()
    
    return success_response(message='Order rejected successfully')


@extend_schema(
    tags=['Couriers'],
    summary='Update Order Status',
    description='Update order status during delivery',
    request={'application/json': {'type': 'object', 'properties': {'status': {'type': 'string'}}}},
    responses={200: OrderDetailSerializer}
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsCourier])
def update_order_status(request, order_id):
    """Update order status during delivery"""
    try:
        order = Order.objects.get(id=order_id, assigned_courier=request.user)
    except Order.DoesNotExist:
        return not_found_response('Order not found. Please check the order ID and try again.')
    
    new_status = request.data.get('status')
    if not new_status:
        return error_response('Order status is required to update the order.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Validate status transition
    valid_transitions = {
        'ACCEPTED': ['PICKED_UP'],
        'PICKED_UP': ['IN_TRANSIT'],
        'IN_TRANSIT': ['DELIVERED'],
    }
    
    if order.status not in valid_transitions:
        return error_response(f'Cannot update order status from {order.get_status_display()} to the requested status.', status_code=status.HTTP_400_BAD_REQUEST)
    
    if new_status not in valid_transitions[order.status]:
        return error_response(f'Invalid status update. Cannot change order from {order.get_status_display()} to {new_status}.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Update status
    order.status = new_status
    
    # Set timestamps
    if new_status == 'PICKED_UP':
        order.picked_up_at = timezone.now()
    elif new_status == 'DELIVERED':
        order.delivered_at = timezone.now()
    
    order.save()
    
    # Create tracking entry
    location = request.data.get('location', '')
    TrackingHistory.objects.create(
        order=order,
        status=new_status,
        location=location,
        notes=request.data.get('notes', '')
    )
    
    serializer = OrderDetailSerializer(order)
    return success_response(data={'order': serializer.data})

