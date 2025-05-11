from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import F, Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    min_stock_level = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    max_stock_level = models.IntegerField(default=100, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    low_stock_alert = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_available_stock(self):
        """Get the current available stock, considering any pending sales."""
        self.refresh_from_db()  # Ensure we have the latest data
        print(f"DEBUG: Product {self.name} current stock: {self.stock_quantity}")
        return self.stock_quantity

    def update_stock(self, quantity_change, transaction_type='ADJUSTMENT', notes=''):
        """
        Update the stock quantity by the given amount.
        Positive values increase stock, negative values decrease stock.
        Returns the actual quantity change applied.
        """
        self.refresh_from_db()  # Ensure we have the latest data
        current_stock = self.stock_quantity
        new_stock = current_stock + quantity_change

        # Validate against max_stock_level for increases
        if quantity_change > 0 and new_stock > self.max_stock_level:
            raise ValidationError(f'Cannot exceed maximum stock level of {self.max_stock_level}')

        # Prevent negative stock
        new_stock = max(0, new_stock)
        
        with transaction.atomic():
            self.stock_quantity = new_stock
            self.save()
            
            # Create stock transaction record
            StockTransaction.objects.create(
                product=self,
                quantity=abs(quantity_change),
                is_increase=quantity_change > 0,
                transaction_type=transaction_type,
                notes=notes,
                previous_stock=current_stock,
                new_stock=new_stock
            )
            
            # Check for low stock alert
            if self.low_stock_alert and self.stock_quantity <= self.min_stock_level:
                self.send_low_stock_alert()
                
        return new_stock - current_stock

    def send_low_stock_alert(self):
        subject = f'Low Stock Alert: {self.name}'
        message = f'''
        Low stock alert for {self.name}
        Current stock: {self.stock_quantity}
        Minimum stock level: {self.min_stock_level}
        Please restock soon.
        '''
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.STOCK_ALERT_EMAIL],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send low stock alert: {e}")

    class Meta:
        ordering = ['name']

class Customer(models.Model):
    name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Sale(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_paid = models.BooleanField(default=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales', null=True, blank=True)

    def __str__(self):
        customer_name = self.customer.name if self.customer else "Walkable Customer"
        return f"Sale #{self.id} - {customer_name} - {self.date.strftime('%Y-%m-%d')}"

    def calculate_profit(self):
        return sum(item.profit for item in self.items.all())

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
        else:
            self.total_amount = sum(item.price_at_sale * item.quantity for item in self.items.all())
            self.profit = self.calculate_profit()
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        print(f"DEBUG: Deleting entire sale #{self.id}")
        # Store all sale items before deletion to restore stock
        items_to_restore = list(self.items.all())
        
        with transaction.atomic():
            # First restore all stock
            for item in items_to_restore:
                print(f"DEBUG: Restoring {item.quantity} units of {item.product.name}")
                actual_change = item.product.update_stock(item.quantity)
                if actual_change != item.quantity:
                    print(f"DEBUG: Warning: Could not fully restore stock for {item.product.name}. Expected +{item.quantity}, actual +{actual_change}")
            
            # Then delete the sale (this will cascade delete the items)
            super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-date']

class SaleItem(models.Model):
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price_at_sale = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,  # Allow null
        blank=True,  # Allow blank in forms
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Leave empty to use product's current selling price"
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def clean(self):
        if not self.product:
            return

        # Check if quantity is None before comparisons
        if self.quantity is None:
            return  # Let the field validation handle the required error

        available_stock = self.product.get_available_stock()
        
        if self.pk:
            try:
                original = SaleItem.objects.get(pk=self.pk)
                original_quantity = original.quantity
                stock_change = self.quantity - original_quantity
                
                if stock_change > 0:
                    if stock_change > available_stock:
                        raise ValidationError({
                            'quantity': f'Not enough stock for the increase. Only {available_stock} additional units available.'
                        })
                print(f"DEBUG: Editing sale item {self.pk}")
                print(f"DEBUG: Original quantity: {original_quantity}")
                print(f"DEBUG: New quantity: {self.quantity}")
                print(f"DEBUG: Available stock: {available_stock}")
                print(f"DEBUG: Stock change needed: {stock_change}")
            except SaleItem.DoesNotExist:
                if self.quantity > available_stock:
                    raise ValidationError({
                        'quantity': f'Not enough stock. Only {available_stock} units available.'
                    })
                print(f"DEBUG: Original sale item not found")
                print(f"DEBUG: New quantity: {self.quantity}")
                print(f"DEBUG: Available stock: {available_stock}")
        else:
            if self.quantity > available_stock:
                raise ValidationError({
                    'quantity': f'Not enough stock. Only {available_stock} units available.'
                })
            print(f"DEBUG: New sale item")
            print(f"DEBUG: New quantity: {self.quantity}")
            print(f"DEBUG: Available stock: {available_stock}")

    def save(self, *args, **kwargs):
        self.clean()

        if self.pk:
            try:
                original = SaleItem.objects.get(pk=self.pk)
                original_quantity = original.quantity
                print(f"DEBUG: Save - Original quantity: {original_quantity}")
            except SaleItem.DoesNotExist:
                original_quantity = 0
                print(f"DEBUG: Save - No original item found")
        else:
            original_quantity = 0
            print(f"DEBUG: Save - New item")

        print(f"DEBUG: Save - New quantity: {self.quantity}")

        if not self.product:
            raise ValidationError('Product is required')

        # Use product's selling price if price_at_sale is not set
        if not self.price_at_sale:
            self.price_at_sale = self.product.selling_price

        with transaction.atomic():
            super().save(*args, **kwargs)

            quantity_difference = self.quantity - original_quantity
            if quantity_difference != 0:
                actual_change = self.product.update_stock(
                    -quantity_difference,
                    transaction_type='SALE',
                    notes=f'Sale #{self.sale.id}'
                )
                if actual_change != -quantity_difference:
                    print(f"DEBUG: Save - Warning: Could not apply full stock change")

            self.sale.save()

    def delete(self, *args, **kwargs):
        product = self.product
        quantity = self.quantity
        sale_id = self.sale_id
        
        print(f"DEBUG: Delete - Restoring {quantity} units to product {product.name}")
        
        with transaction.atomic():
            super().delete(*args, **kwargs)
            
            actual_change = product.update_stock(quantity)
            if actual_change != quantity:
                print(f"DEBUG: Delete - Warning: Could not fully restore stock. Expected +{quantity}, actual +{actual_change}")

    @property
    def profit(self):
        if not self.price_at_sale or not self.product or not self.product.purchase_price:
            return Decimal('0.00')
        return (self.price_at_sale - self.product.purchase_price) * self.quantity

    class Meta:
        ordering = ['-sale__date']

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('SALE', 'Sale'),
        ('RETURN', 'Return'),
        ('ADJUSTMENT', 'Adjustment'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_transactions')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    is_increase = models.BooleanField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    notes = models.TextField(blank=True)
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        direction = "IN" if self.is_increase else "OUT"
        return f"{self.transaction_type} {direction}: {self.product.name} x {self.quantity}"

    def clean(self):
        if not self.pk:  # Only for new transactions
            current_stock = self.product.stock_quantity
            quantity_change = self.quantity if self.is_increase else -self.quantity
            new_stock = current_stock + quantity_change
            
            if new_stock < 0:
                raise ValidationError({
                    'quantity': f'Cannot reduce stock below 0. Current stock: {current_stock}'
                })
            
            if self.is_increase and new_stock > self.product.max_stock_level:
                raise ValidationError({
                    'quantity': f'Cannot exceed maximum stock level of {self.product.max_stock_level}'
                })

    class Meta:
        ordering = ['-created_at']

class ProductPriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.changed_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Product Price History'
        verbose_name_plural = 'Product Price Histories'

class SaleReturn(models.Model):
    sale_item = models.ForeignKey('SaleItem', on_delete=models.CASCADE, related_name='returns')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    reason = models.TextField()
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.quantity > self.sale_item.quantity:
            raise ValidationError({
                'quantity': f'Cannot return more than purchased quantity ({self.sale_item.quantity})'
            })

    def save(self, *args, **kwargs):
        if not self.pk:  # Only for new returns
            self.refund_amount = self.sale_item.price_at_sale * self.quantity
            with transaction.atomic():
                super().save(*args, **kwargs)
                # Update stock
                self.sale_item.product.update_stock(
                    self.quantity,
                    transaction_type='RETURN',
                    notes=f'Return from Sale #{self.sale_item.sale.id}'
                )
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Store references before deletion
        product = self.sale_item.product
        quantity = self.quantity
        sale_id = self.sale_item.sale.id
        
        # Delete the return and update stock in a transaction
        with transaction.atomic():
            super().delete(*args, **kwargs)
            
            # Decrease the stock since the return is being cancelled
            actual_change = product.update_stock(
                -quantity,  # Negative quantity to decrease stock
                transaction_type='ADJUSTMENT',
                notes=f'Cancelled return from Sale #{sale_id}'
            )
            if actual_change != -quantity:
                print(f"Warning: Could not fully adjust stock. Expected -{quantity}, actual {actual_change}")

    def __str__(self):
        return f"Return: {self.sale_item.product.name} x {self.quantity} from Sale #{self.sale_item.sale.id}"

    class Meta:
        ordering = ['-processed_at']

# Signal to track price changes
@receiver(post_save, sender=Product)
def track_price_changes(sender, instance, created, **kwargs):
    if not created:
        # Get the latest price history
        latest = ProductPriceHistory.objects.filter(product=instance).first()
        
        # If no history or prices changed
        if not latest or \
           latest.purchase_price != instance.purchase_price or \
           latest.selling_price != instance.selling_price:
            ProductPriceHistory.objects.create(
                product=instance,
                purchase_price=instance.purchase_price,
                selling_price=instance.selling_price
            )

@receiver(post_delete, sender=SaleItem)
def check_and_delete_empty_sale(sender, instance, **kwargs):
    """Delete sales that have no items after a sale item is deleted."""
    try:
        # Get the sale and check if it exists and has no items
        sale = Sale.objects.get(pk=instance.sale_id)
        if sale.items.count() == 0:
            # Use a simple delete to avoid double stock restoration
            Sale.objects.filter(pk=sale.pk).delete()
    except Sale.DoesNotExist:
        # Sale was already deleted
        pass