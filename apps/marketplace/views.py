from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.core.response import success_response, error_response, created_response, validation_error_response, not_found_response
from drf_spectacular.utils import extend_schema
from django.db import transaction as db_transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

from apps.marketplace.models import Category, Store, Product, Cart, CartItem
from apps.marketplace.serializers import (
    CategorySerializer,
    StoreSerializer,
    ProductSerializer,
    CartSerializer,
    CartItemSerializer,
    CheckoutSerializer
)
from apps.orders.models import Order
from apps.core.permissions import IsUser


@extend_schema(
    tags=['Marketplace'],
    summary='List Categories',
    description='Get all product categories',
    responses={200: CategorySerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_categories(request):
    """List all product categories"""
    categories = Category.objects.filter(is_active=True).order_by('name')
    serializer = CategorySerializer(categories, many=True)
    return success_response(data={'categories': serializer.data})


@extend_schema(
    tags=['Marketplace'],
    summary='List Stores',
    description='Get all stores',
    responses={200: StoreSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_stores(request):
    """List all active stores"""
    stores = Store.objects.filter(is_active=True).order_by('name')
    serializer = StoreSerializer(stores, many=True)
    return success_response(data={'stores': serializer.data})


@extend_schema(
    tags=['Marketplace'],
    summary='List Products',
    description='List products with filtering by category and store',
    responses={200: ProductSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_products(request):
    """List products with optional filtering"""
    queryset = Product.objects.filter(is_active=True, is_available=True)
    
    # Filter by category
    category = request.query_params.get('category')
    if category:
        queryset = queryset.filter(category__slug=category)
    
    # Filter by store
    store = request.query_params.get('store')
    if store:
        queryset = queryset.filter(store__slug=store)
    
    # Filter by featured
    featured = request.query_params.get('featured')
    if featured:
        queryset = queryset.filter(is_featured=True)
    
    serializer = ProductSerializer(queryset, many=True)
    return success_response(data={'products': serializer.data})


@extend_schema(
    tags=['Marketplace'],
    summary='Product Detail',
    description='Get product details',
    responses={200: ProductSerializer}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    """Get product details"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return not_found_response('Product not found. Please check the product ID and try again.')
    
    serializer = ProductSerializer(product)
    return success_response(data={'product': serializer.data})


@extend_schema(
    tags=['Marketplace'],
    summary='Get Cart',
    description='Get user shopping cart',
    responses={200: CartSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsUser])
def get_cart(request):
    """Get user's shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    serializer = CartSerializer(cart)
    return success_response(data={'cart': serializer.data})


@extend_schema(
    tags=['Marketplace'],
    summary='Add to Cart',
    description='Add product to shopping cart',
    responses={200: CartSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsUser])
def add_to_cart(request):
    """Add product to cart"""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    serializer = CartItemSerializer(data=request.data, context={'cart': cart})
    
    if serializer.is_valid():
        try:
            serializer.save()
            # Return updated cart
            cart.refresh_from_db()
            cart_serializer = CartSerializer(cart)
            return success_response(data={'cart': cart_serializer.data}, message='Item added to cart successfully')
        except Exception as e:
            logger.error(f"Error adding item to cart: {e}", exc_info=True)
            return error_response('Failed to add item to cart. Please try again.', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return validation_error_response(serializer.errors, message='Validation error')


@extend_schema(
    tags=['Marketplace'],
    summary='Remove from Cart',
    description='Remove item from cart',
    responses={200: {'message': 'Item removed'}}
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsUser])
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
        cart_item.delete()
        return success_response(message='Item removed from cart')
    except CartItem.DoesNotExist:
        return not_found_response('Cart item not found. The item may have been removed from your cart.')


@extend_schema(
    tags=['Marketplace'],
    summary='Checkout',
    description='Checkout cart and create order',
    responses={200: {'message': 'Order created', 'order_id': 'int'}}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsUser])
def checkout(request):
    """Checkout cart and create order"""
    serializer = CheckoutSerializer(data=request.data)
    if not serializer.is_valid():
        return validation_error_response(serializer.errors, message='Validation error')
    
    # Get user's cart
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return error_response('Your cart is empty. Please add items before checkout.', status_code=status.HTTP_400_BAD_REQUEST)
    
    if cart.items.count() == 0:
        return error_response('Your cart is empty. Please add items before checkout.', status_code=status.HTTP_400_BAD_REQUEST)
    
    # Create order with atomic transaction
    with db_transaction.atomic():
        # Build order description from cart items
        order_description = "Marketplace Order:\n"
        total_weight = 0
        total_value = 0
        
        for item in cart.items.all():
            order_description += f"- {item.product.name} x {item.quantity}\n"
            total_weight += item.product.weight_kg * item.quantity
            total_value += item.product.price * item.quantity
        
        # Create order (simplified - assumes pickup/dropoff from user profile)
        order = Order.objects.create(
            sender=request.user,
            pickup_address=request.data.get('pickup_address', 'Store Location'),
            dropoff_address=request.data.get('dropoff_address', 'Not specified'),
            recipient_name=request.data.get('recipient_name', request.user.get_full_name()),
            recipient_email=request.user.email,
            recipient_phone=request.user.phone_number,
            delivery_instructions=request.data.get('delivery_instructions', ''),
            parcel_type='OTHER',  # Default type for marketplace orders
            parcel_description=order_description,
            parcel_condition='Normal',
            parcel_quantity=cart.total_items,
            parcel_weight_kg=total_weight if total_weight > 0 else Decimal('1.00'),  # Default 1kg if no weight
            parcel_financial_worth=total_value,
            delivery_fee=Decimal(str(request.data.get('delivery_fee', 0))),
            service_charge=Decimal(str(request.data.get('service_charge', 0))),
            total_amount=cart.total_amount + Decimal(str(request.data.get('delivery_fee', 0))) + Decimal(str(request.data.get('service_charge', 0))),
            status='PENDING',
            metadata={'source': 'marketplace', 'payment_method': serializer.validated_data.get('payment_method')}
        )
        
        # Clear cart
        cart.items.all().delete()
    
    return created_response(
        data={'order_id': order.id, 'order_number': order.order_number},
        message='Order created successfully'
    )

