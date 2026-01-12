from django.urls import path
from apps.orders.views import (
    create_order,
    confirm_order,
    list_orders,
    order_detail,
    track_order,
    available_orders,
    accept_order,
    reject_order,
    update_order_status,
)
from apps.orders.image_upload import upload_parcel_image

app_name = 'orders'

urlpatterns = [
    # User endpoints
    path('upload-image/', upload_parcel_image, name='upload_parcel_image'),
    path('create/', create_order, name='create_order'),
    path('<int:order_id>/confirm/', confirm_order, name='confirm_order'),
    path('list/', list_orders, name='list_orders'),
    path('<int:order_id>/', order_detail, name='order_detail'),
    path('<int:order_id>/track/', track_order, name='track_order'),
    
    # Courier endpoints
    path('available/', available_orders, name='available_orders'),
    path('<int:order_id>/accept/', accept_order, name='accept_order'),
    path('<int:order_id>/reject/', reject_order, name='reject_order'),
    path('<int:order_id>/update-status/', update_order_status, name='update_order_status'),
]

