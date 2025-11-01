from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    get_balance,
    initialize_payment,
    verify_payment,
    create_dva,
    get_dva,
    create_transfer_recipient,
    list_transfer_recipients,
    create_transfer,
    finalize_transfer,
    paystack_webhook,
    TransactionViewSet,
    NotificationViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'notifications', NotificationViewSet, basename='notification')

app_name = 'payments'

urlpatterns = [
    # Balance
    path('balance/', get_balance, name='get_balance'),
    
    # Payment (Deposit)
    path('initialize/', initialize_payment, name='initialize_payment'),
    path('verify/', verify_payment, name='verify_payment'),
    
    # DVA
    path('dva/create/', create_dva, name='create_dva'),
    path('dva/', get_dva, name='get_dva'),
    
    # Transfer Recipients
    path('transfer/recipient/create/', create_transfer_recipient, name='create_transfer_recipient'),
    path('transfer/recipients/', list_transfer_recipients, name='list_transfer_recipients'),
    
    # Transfer (Withdrawal)
    path('transfer/', create_transfer, name='create_transfer'),
    path('transfer/finalize/', finalize_transfer, name='finalize_transfer'),
    
    # Webhook
    path('webhook/', paystack_webhook, name='paystack_webhook'),
    
    # Include router URLs
    path('', include(router.urls)),
]

