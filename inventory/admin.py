from django.contrib import admin
from django.db.models import F, Sum, Count
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Product, Customer, Sale, SaleItem, Category,
    StockTransaction, ProductPriceHistory, SaleReturn
)
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.db.transaction import atomic
from django.db import transaction
import json

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'product_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

class StockTransactionInline(admin.TabularInline):
    model = StockTransaction
    extra = 0
    readonly_fields = ('created_at', 'previous_stock', 'new_stock')
    fields = ('transaction_type', 'quantity', 'is_increase', 'notes', 'created_at', 'previous_stock', 'new_stock')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

class ProductPriceHistoryInline(admin.TabularInline):
    model = ProductPriceHistory
    extra = 0
    readonly_fields = ('changed_at',)
    fields = ('purchase_price', 'selling_price', 'changed_at')
    can_delete = False
    ordering = ('-changed_at',)

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'image_preview', 'stock_status',
        'stock_quantity', 'min_stock_level', 'purchase_price',
        'selling_price', 'profit_margin', 'is_active'
    )
    list_filter = ('category', 'is_active', 'low_stock_alert')
    search_fields = ('name', 'category__name')
    ordering = ('name',)
    readonly_fields = ('profit_margin', 'image_preview', 'created_at', 'updated_at')
    list_editable = ('is_active', 'min_stock_level', 'purchase_price', 'selling_price')
    inlines = [StockTransactionInline, ProductPriceHistoryInline]
    actions = ['bulk_restock']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # If editing an existing object
            return self.readonly_fields + ('stock_quantity',)
        return self.readonly_fields  # If adding a new object

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'image', 'image_preview', 'is_active')
        }),
        ('Stock Management', {
            'fields': (
                'stock_quantity', 'min_stock_level', 'max_stock_level',
                'low_stock_alert'
            )
        }),
        ('Pricing', {
            'fields': ('purchase_price', 'selling_price', 'profit_margin')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def stock_status(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: grey;">Inactive</span>')
        if obj.stock_quantity == 0:
            return format_html('<span style="color: red; font-weight: bold;">Out of Stock</span>')
        elif obj.stock_quantity <= obj.min_stock_level:
            return format_html('<span style="color: orange; font-weight: bold;">Low Stock</span>')
        else:
            return format_html('<span style="color: green;">In Stock</span>')
    stock_status.short_description = 'Status'

    def profit_margin(self, obj):
        if obj.purchase_price and obj.selling_price:
            margin = ((obj.selling_price - obj.purchase_price) / obj.purchase_price) * 100
            return format_html('<span style="font-weight: bold;">{}</span>', '{:.1f}%'.format(margin))
        return '-'
    profit_margin.short_description = 'Margin'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px;"/>', obj.image.url)
        return '-'
    image_preview.short_description = 'Image'

    def bulk_restock(self, request, queryset):
        for product in queryset:
            space_available = product.max_stock_level - product.stock_quantity
            if space_available > 0:
                product.update_stock(
                    space_available,
                    transaction_type='PURCHASE',
                    notes='Bulk restock to maximum level'
                )
        self.message_user(request, f"Successfully restocked {queryset.count()} products")
    bulk_restock.short_description = "Restock selected products to maximum level"

    class Media:
        css = {
            'all': ['admin/css/custom.css']
        }

class SaleReturnInline(admin.TabularInline):
    model = SaleReturn
    extra = 0
    readonly_fields = ('processed_at', 'refund_amount')
    fields = ('quantity', 'reason', 'processed_at', 'refund_amount')

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'quantity', 'price_at_sale', 'profit')
    readonly_fields = ('profit',)

    class Media:
        js = ('admin/js/preload_price.js',)

    def get_readonly_fields(self, request, obj=None):
        return ('profit',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'product':
            field.widget.attrs.update({
                'class': 'product-selector'
            })
        return field

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date', 'total_amount', 'profit', 'is_paid')
    list_filter = ('is_paid', 'date', 'customer')
    search_fields = ('customer__name',)
    inlines = [SaleItemInline]
    readonly_fields = ('total_amount', 'profit', 'date')
    ordering = ('-date',)
    
    class Media:
        js = ('admin/js/sale_form.js',)

    def get_readonly_fields(self, request, obj=None):
        return ('total_amount', 'profit', 'date')

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to handle bulk deletions properly"""
        with transaction.atomic():
            # First restore stock for all sale items
            for sale in queryset:
                items_to_restore = list(sale.items.all())
                for item in items_to_restore:
                    print(f"DEBUG: Bulk delete - Restoring {item.quantity} units of {item.product.name}")
                    actual_change = item.product.update_stock(
                        item.quantity,
                        transaction_type='ADJUSTMENT',
                        notes=f'Restored from bulk sale deletion'
                    )
                    if actual_change != item.quantity:
                        print(f"DEBUG: Warning: Could not fully restore stock for {item.product.name}. Expected +{item.quantity}, actual +{actual_change}")
            
            # Then delete all sales
            queryset.delete()

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity', 'is_increase',
                   'previous_stock', 'new_stock', 'created_at')
    list_filter = ('transaction_type', 'is_increase', 'created_at', 'product__category')
    search_fields = ('product__name', 'notes')
    ordering = ('-created_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # If editing existing transaction
            return ('product', 'transaction_type', 'quantity', 'is_increase', 
                   'previous_stock', 'new_stock', 'created_at', 'notes')
        # If adding new transaction
        return ('previous_stock', 'new_stock', 'created_at')

    def has_change_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:  # Only for new transactions
            obj.previous_stock = obj.product.stock_quantity
            quantity_change = obj.quantity if obj.is_increase else -obj.quantity
            obj.new_stock = obj.previous_stock + quantity_change
            
            # Validate the new stock level
            if obj.new_stock < 0:
                raise ValidationError('Cannot reduce stock below 0')
            if obj.new_stock > obj.product.max_stock_level:
                raise ValidationError(f'Cannot exceed maximum stock level of {obj.product.max_stock_level}')
            
            # Update the product's stock quantity
            with transaction.atomic():
                obj.product.stock_quantity = obj.new_stock
                obj.product.save()
                obj.created_by = request.user
                super().save_model(request, obj, form, change)

@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'purchase_price', 'selling_price', 'changed_at')
    list_filter = ('product', 'changed_at')
    search_fields = ('product__name',)
    readonly_fields = ('product', 'purchase_price', 'selling_price', 'changed_at', 'changed_by')
    ordering = ('-changed_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ('sale_item', 'quantity', 'refund_amount', 'processed_at')
    list_filter = ('processed_at',)
    search_fields = ('sale_item__product__name', 'reason')
    readonly_fields = ('processed_at', 'refund_amount')
    ordering = ('-processed_at',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'created_at')
    search_fields = ('name', 'contact_info')
    ordering = ('name',)
    readonly_fields = ('created_at',)
    list_filter = ('created_at',)

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'price_at_sale')
    list_filter = ('sale__date',)
    search_fields = ('product__name', 'sale__customer__name')
    readonly_fields = ()
    ordering = ('-sale__date',)

    def delete_queryset(self, request, queryset):
        """Override delete_queryset to handle bulk deletions properly"""
        with transaction.atomic():
            # First restore stock for all items
            for item in queryset:
                print(f"DEBUG: Bulk delete - Restoring {item.quantity} units of {item.product.name}")
                actual_change = item.product.update_stock(
                    item.quantity,
                    transaction_type='ADJUSTMENT',
                    notes=f'Restored from bulk sale item deletion'
                )
                if actual_change != item.quantity:
                    print(f"DEBUG: Warning: Could not fully restore stock for {item.product.name}. Expected +{item.quantity}, actual +{actual_change}")
            
            # Then delete all items
            queryset.delete() 