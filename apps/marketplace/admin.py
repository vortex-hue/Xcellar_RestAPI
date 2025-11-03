from django.contrib import admin
from apps.marketplace.models import Category, Store, Product, Cart, CartItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_featured', 'is_active']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['name', 'slug']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner_name', 'email', 'rating', 'is_verified', 'is_active']
    list_filter = ['is_verified', 'is_active']
    search_fields = ['name', 'owner_name', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'category', 'price', 'stock_quantity', 
                    'is_available', 'is_featured', 'rating']
    list_filter = ['category', 'store', 'is_available', 'is_featured']
    search_fields = ['name', 'sku', 'store__name']
    readonly_fields = ['sku', 'created_at', 'updated_at']
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'sku', 'description', 'short_description')
        }),
        ('Store & Category', {
            'fields': ('store', 'category')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'weight_kg', 'dimensions')
        }),
        ('Media', {
            'fields': ('images',)
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured', 'rating', 'total_sales')
        }),
        ('Metadata', {
            'fields': ('metadata', 'is_active')
        }),
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'total_amount', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'subtotal']
    readonly_fields = ['subtotal', 'created_at', 'updated_at']

