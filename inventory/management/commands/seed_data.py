from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Category, Product, Customer, Sale, SaleItem, StockTransaction
from django.utils import timezone
from datetime import timedelta, datetime
import random
from decimal import Decimal
from django.db import transaction

class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def create_sales_for_date(self, date, num_sales, customers, products, product_stock):
        """Create a specified number of sales for a given date"""
        for _ in range(num_sales):
            try:
                with transaction.atomic():
                    customer = random.choice(customers)
                    
                    # Create sale with the exact date
                    sale = Sale.objects.create(
                        customer=customer,
                        date=date,
                        is_paid=True
                    )

                    # Add 1-5 items to each sale
                    num_items = random.randint(1, 5)
                    total_amount = Decimal('0')
                    total_profit = Decimal('0')
                    
                    # Filter products that have stock available
                    available_products = [p for p in products if product_stock[p.id] > 0]
                    if not available_products:
                        continue
                        
                    # Select random products from available ones
                    selected_products = random.sample(
                        available_products,
                        min(num_items, len(available_products))
                    )
                    
                    for product in selected_products:
                        # Calculate available quantity for this product
                        available_stock = product_stock[product.id]
                        if available_stock <= 0:
                            continue
                            
                        # Generate a random quantity that won't exceed available stock
                        max_quantity = min(5, available_stock)  # Limit to 5 items per sale
                        quantity = random.randint(1, max_quantity)
                        
                        # Create sale item
                        sale_item = SaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            price_at_sale=product.selling_price
                        )
                        
                        # Update stock tracking
                        product_stock[product.id] -= quantity
                        
                        # Update product stock in database
                        product.stock_quantity = product_stock[product.id]
                        product.save()
                        
                        # Create stock transaction
                        StockTransaction.objects.create(
                            product=product,
                            quantity=quantity,
                            transaction_type='SALE',
                            is_increase=False,
                            notes=f'Sale #{sale.id}',
                            previous_stock=product_stock[product.id] + quantity,
                            new_stock=product_stock[product.id]
                        )
                        
                        # Update sale totals
                        item_total = product.selling_price * quantity
                        item_profit = (product.selling_price - product.purchase_price) * quantity
                        total_amount += item_total
                        total_profit += item_profit

                    if total_amount > 0:  # Only save sales with items
                        sale.total_amount = total_amount
                        sale.profit = total_profit
                        sale.save()
                        self.stdout.write(f'Created sale for {date.strftime("%Y-%m-%d")} with {len(selected_products)} items')
                    else:
                        sale.delete()
                        
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating sale: {str(e)}'))
                continue

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        # Create superuser if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write('Superuser created')

        # Create categories
        categories = [
            'Electronics',
            'Clothing',
            'Books',
            'Home & Garden',
            'Sports Equipment',
            'Office Supplies',
            'Food & Beverages',
            'Health & Beauty'
        ]
        
        created_categories = []
        for cat_name in categories:
            category, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'All {cat_name.lower()} products'}
            )
            created_categories.append(category)
            if created:
                self.stdout.write(f'Created category: {cat_name}')

        # Create products with varied stock levels
        products_data = [
            # Electronics
            ('iPhone 13', 'Electronics', 800, 1200, 50, 5, 100),
            ('Samsung TV', 'Electronics', 500, 800, 20, 3, 30),
            ('Laptop Pro', 'Electronics', 1000, 1500, 15, 2, 25),
            ('Wireless Earbuds', 'Electronics', 50, 100, 100, 20, 200),
            
            # Clothing
            ('Winter Jacket', 'Clothing', 40, 89.99, 30, 10, 50),
            ('Running Shoes', 'Clothing', 30, 79.99, 45, 15, 100),
            ('Cotton T-Shirt', 'Clothing', 5, 19.99, 200, 50, 300),
            ('Jeans', 'Clothing', 25, 59.99, 75, 20, 150),
            
            # Books
            ('Python Programming', 'Books', 20, 49.99, 50, 10, 100),
            ('Business Strategy', 'Books', 15, 39.99, 30, 5, 50),
            ('Cooking Guide', 'Books', 10, 29.99, 40, 10, 80),
            
            # Home & Garden
            ('Garden Tools Set', 'Home & Garden', 50, 99.99, 25, 5, 40),
            ('Coffee Maker', 'Home & Garden', 30, 79.99, 35, 10, 60),
            ('Bed Sheets', 'Home & Garden', 20, 49.99, 60, 15, 100),
            
            # Sports Equipment
            ('Yoga Mat', 'Sports Equipment', 15, 39.99, 40, 10, 80),
            ('Dumbbells Set', 'Sports Equipment', 40, 89.99, 25, 5, 50),
            ('Tennis Racket', 'Sports Equipment', 35, 79.99, 20, 5, 40),
            
            # Office Supplies
            ('Printer Paper', 'Office Supplies', 3, 9.99, 500, 100, 1000),
            ('Stapler', 'Office Supplies', 5, 14.99, 100, 20, 200),
            ('Ink Cartridge', 'Office Supplies', 15, 34.99, 80, 20, 150),
            
            # Food & Beverages
            ('Coffee Beans', 'Food & Beverages', 10, 24.99, 100, 20, 200),
            ('Energy Drink', 'Food & Beverages', 1, 3.99, 300, 50, 500),
            ('Chocolate Bars', 'Food & Beverages', 0.5, 1.99, 1000, 200, 2000),
            
            # Health & Beauty
            ('Face Cream', 'Health & Beauty', 10, 29.99, 75, 15, 150),
            ('Shampoo', 'Health & Beauty', 5, 14.99, 150, 30, 300),
            ('Toothpaste', 'Health & Beauty', 2, 5.99, 200, 40, 400)
        ]

        # Dictionary to keep track of product stock
        product_stock = {}
        created_products = []
        
        for name, cat_name, purchase_price, selling_price, stock, min_stock, max_stock in products_data:
            category = Category.objects.get(name=cat_name)
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'purchase_price': purchase_price,
                    'selling_price': selling_price,
                    'stock_quantity': stock,
                    'min_stock_level': min_stock,
                    'max_stock_level': max_stock,
                    'is_active': True,
                    'low_stock_alert': True
                }
            )
            product_stock[product.id] = stock  # Track initial stock
            created_products.append(product)
            if created:
                self.stdout.write(f'Created product: {name}')

        # Create customers
        customer_names = [
            'John Smith', 'Emma Wilson', 'Michael Brown', 'Sarah Davis',
            'James Johnson', 'Lisa Anderson', 'Robert Taylor', 'Jennifer Thomas',
            'William Martinez', 'Elizabeth Robinson', 'David Garcia', 'Maria Rodriguez',
            'Joseph Lee', 'Margaret White', 'Charles King', 'Patricia Wright'
        ]

        created_customers = []
        for name in customer_names:
            customer, created = Customer.objects.get_or_create(
                name=name,
                defaults={'contact_info': f'{name.lower().replace(" ", ".")}@example.com'}
            )
            created_customers.append(customer)
            if created:
                self.stdout.write(f'Created customer: {name}')

        # Create sales with actual past dates
        # Set a fixed start date 90 days ago
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        # Last 7 days: 40% of sales
        for i in range(7):
            date = end_date - timedelta(days=i)
            num_sales = random.randint(10, 15)  # 10-15 sales per day
            self.create_sales_for_date(datetime.combine(date, datetime.min.time()), num_sales, created_customers, created_products, product_stock)
            
        # 8-30 days ago: 40% of sales
        for i in range(7, 30):
            date = end_date - timedelta(days=i)
            num_sales = random.randint(5, 8)  # 5-8 sales per day
            self.create_sales_for_date(datetime.combine(date, datetime.min.time()), num_sales, created_customers, created_products, product_stock)
            
        # 31-90 days ago: 20% of sales
        for i in range(30, 90):
            date = end_date - timedelta(days=i)
            num_sales = random.randint(1, 3)  # 1-3 sales per day
            self.create_sales_for_date(datetime.combine(date, datetime.min.time()), num_sales, created_customers, created_products, product_stock)

        self.stdout.write(self.style.SUCCESS('Successfully seeded database'))
        self.stdout.write('\nYou can now log in with:')
        self.stdout.write('Username: admin')
        self.stdout.write('Password: admin') 