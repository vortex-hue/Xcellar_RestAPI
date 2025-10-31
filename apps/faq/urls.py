from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FAQViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', FAQViewSet, basename='faq')

app_name = 'faq'

urlpatterns = [
    path('', include(router.urls)),
]

