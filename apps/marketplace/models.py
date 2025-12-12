from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from decimal import Decimal
from apps.core.models import AbstractBaseModel


class Category(AbstractBaseModel):
    """
    Product categories for organizing marketplace items.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='marketplace/categories/', null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Store(AbstractBaseModel):
    """
    Store model for marketplace vendors.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    owner_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='marketplace/stores/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='marketplace/stores/', null=True, blank=True)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    total_sales = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'stores'
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(AbstractBaseModel):
    """
    Product model for marketplace items.
    """
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    primary_image = models.ImageField(upload_to='marketplace/products/', null=True, blank=True)
    images = models.JSONField(default=list, blank=True)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    dimensions = models.CharField(max_length=100, blank=True)  # e.g., "30x20x15 cm"
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    total_sales = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        unique_together = [['store', 'slug']]
        indexes = [
            models.Index(fields=['store', 'category']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_available', 'is_featured']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.store.name}"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            import uuid
            self.sku = f"PRD-{uuid.uuid4().hex[:10].upper()}"
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Cart(AbstractBaseModel):
    """
    Shopping cart for marketplace purchases.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    
    class Meta:
        db_table = 'carts'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(AbstractBaseModel):
    """
    Individual items in shopping cart.
    """
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = [['cart', 'product']]
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def subtotal(self):
        return self.product.price * self.quantity

