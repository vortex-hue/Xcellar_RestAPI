import os
import random
import uuid
from decimal import Decimal
from django.utils.text import slugify

# Standalone setup not needed when running via manage.py shell
from apps.marketplace.models import Category, Store, Product

CATEGORIES = [
    ("Electronics", "Gadgets, phones, and computers"),
    ("Fashion", "Clothing, shoes, and accessories"),
    ("Home & Garden", "Furniture, decor, and gardening tools"),
    ("Health & Beauty", "Skincare, makeup, and wellness"),
    ("Sports & Outdoors", "Equipment for sports and outdoor activities"),
    ("Groceries", "Daily essentials and food items"),
    ("Automotive", "Car parts and accessories"),
    ("Books & Stationery", "Books, office supplies, and more"),
    ("Toys & Games", "Fun for kids and adults"),
    ("Computing", "Laptops, desktops, and peripherals"),
]

STORE_NAMES = [
    "TechHaven", "FashionForward", "GreenThumb Gardens", "GlowUp Beauty", 
    "SportySpic", "DailyFresh Mart", "AutoZone Plus", "ReadMore Books", 
    "ToyKingdom", "CyberSpace", "UrbanOutfitters", "HomeDepot Lite", 
    "HealthyLiving", "GearUp Sports", "QuickStop Grocers"
]

PRODUCT_TEMPLATES = {
    "Electronics": [("iPhone 15", 1000000), ("Samsung S24", 950000), ("Sony Headphones", 150000), ("Smart Watch", 50000)],
    "Fashion": [("Denim Jacket", 25000), ("Running Shoes", 45000), ("Summer Dress", 15000), ("Leather Bag", 35000)],
    "Home & Garden": [("Garden Hose", 12000), ("Sofa Set", 450000), ("Desk Lamp", 15000), ("Plant Pot", 5000)],
    "Health & Beauty": [("Face Serum", 15000), ("Lipstick", 5000), ("Vitamins", 8000), ("Shampoo", 4000)],
    "Sports & Outdoors": [("Yoga Mat", 10000), ("Dumbbells", 20000), ("Tent", 85000), ("Bicycle", 150000)],
    "Groceries": [("Rice 50kg", 60000), ("Vegetable Oil", 12000), ("Cereal Box", 3000), ("Pasta Pack", 1500)],
    "Automotive": [("Car Battery", 45000), ("Car Wash Fluid", 3000), ("Seat Covers", 25000), ("Tire Pump", 15000)],
    "Books & Stationery": [("Notebook", 1500), ("Pen Set", 2000), ("Novel", 5000), ("Textbook", 12000)],
    "Toys & Games": [("Lego Set", 45000), ("Doll", 10000), ("Board Game", 15000), ("RC Car", 25000)],
    "Computing": [("MacBook Air", 1200000), ("USB Hub", 15000), ("Monitor 24inch", 120000), ("Keyboard", 25000)],
}

def seed_marketplace():
    print("Starting bulk seed...")
    
    # 1. Create Categories
    categories_dict = {}
    for name, desc in CATEGORIES:
        slug = slugify(name)
        cat, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'description': desc, 'is_featured': random.choice([True, False])}
        )
        categories_dict[name] = cat
        print(f"Category: {name}")

    # 2. Create Stores
    stores = []
    for i, name in enumerate(STORE_NAMES):
        slug = slugify(f"{name}-{i}")
        store, created = Store.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'description': f"Official store for {name}",
                'owner_name': f"Owner {name}",
                'address': f"{i*10} Market Street, Lagos",
                'phone_number': f"+23480{i:08d}",
                'email': f"contact@{slug.replace('-', '')}.com",
                'is_verified': random.choice([True, True, False]),
                'is_active': True
            }
        )
        stores.append(store)
        print(f"Store: {name}")

    # 3. Create Products
    for store in stores:
        # Each store sells items from 1-3 random categories
        store_cats = random.sample(list(PRODUCT_TEMPLATES.keys()), k=random.randint(1, 3))
        
        for cat_name in store_cats:
            cat = categories_dict.get(cat_name)
            products = PRODUCT_TEMPLATES.get(cat_name, [])
            
            # Create a few products for this category in this store
            for prod_name, base_price in products:
                # Add some randomness to price and name to make unique
                price = Decimal(base_price) * Decimal(random.uniform(0.9, 1.1))
                final_name = f"{prod_name} {random.choice(['Pro', 'Max', 'Lite', 'Edition', ''])}".strip()
                unique_slug = slugify(f"{final_name}-{store.id}-{uuid.uuid4().hex[:6]}")
                
                # Generate random image URLs based on category
                # Using loremflickr with keywords
                keyword = cat.name.split()[0].lower()
                image_urls = [
                    f"https://loremflickr.com/640/480/{keyword}?lock={random.randint(1, 10000)}",
                    f"https://loremflickr.com/640/480/{keyword}?lock={random.randint(10001, 20000)}",
                    f"https://loremflickr.com/640/480/{keyword}?lock={random.randint(20001, 30000)}"
                ]
                
                Product.objects.update_or_create(
                    slug=unique_slug,
                    store=store,
                    defaults={
                        'category': cat,
                        'name': final_name,
                        'description': f"High quality {final_name} sold by {store.name}",
                        'price': round(price, 2),
                        'stock_quantity': random.randint(5, 100),
                        'is_available': True,
                        'is_featured': random.choice([True, False]),
                        'images': image_urls  # Add images
                    }
                )
    
    print(f"Seeding complete. Total Products: {Product.objects.count()}")

seed_marketplace()
