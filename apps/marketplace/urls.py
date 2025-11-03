from django.urls import path
from apps.marketplace.views import (
    list_categories,
    list_stores,
    list_products,
    product_detail,
    get_cart,
    add_to_cart,
    remove_from_cart,
    checkout,
)

app_name = 'marketplace'

urlpatterns = [
    path('categories/', list_categories, name='list_categories'),
    path('stores/', list_stores, name='list_stores'),
    path('products/', list_products, name='list_products'),
    path('products/<int:product_id>/', product_detail, name='product_detail'),
    path('cart/', get_cart, name='get_cart'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', checkout, name='checkout'),
]

