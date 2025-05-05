# No views needed - using only the Django admin interface 

from django.http import JsonResponse
from django.db.models import Count, Sum, F, Q
from django.utils import timezone
from datetime import timedelta
from .models import Product, Sale, Customer, Category, StockTransaction, SaleItem
from django.views.decorators.cache import cache_page

def get_stock_levels_chart(request):
    """Bar chart showing current stock levels vs min stock levels for all products"""
    search_query = request.GET.get('search', '').strip()
    print(f"Search query received: {search_query}")  # Debug print
    
    products = Product.objects.filter(is_active=True)
    
    if search_query:
        products = products.filter(name__icontains=search_query)
        print(f"Filtered products count: {products.count()}")  # Debug print
    
    products = products.values(
        'name', 'stock_quantity', 'min_stock_level'
    ).order_by('name')

    data = {
        'labels': [p['name'] for p in products],
        'datasets': [
            {
                'label': 'Current Stock',
                'data': [p['stock_quantity'] for p in products],
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1
            },
            {
                'label': 'Minimum Stock Level',
                'data': [p['min_stock_level'] for p in products],
                'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                'borderColor': 'rgba(255, 99, 132, 1)',
                'borderWidth': 1
            }
        ]
    }
    print(f"Returning {len(data['labels'])} products")  # Debug print
    return JsonResponse(data)

def get_top_selling_products(request):
    """Bar chart showing top 5 selling products by quantity"""
    category_id = request.GET.get('category')
    days = int(request.GET.get('days', 30))
    search_query = request.GET.get('search', '').strip()
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Start with SaleItem to avoid duplicate counting
    query = SaleItem.objects.filter(
        sale__date__gte=start_date,
        product__is_active=True
    )
    
    if category_id:
        query = query.filter(product__category_id=category_id)
    
    if search_query:
        query = query.filter(product__name__icontains=search_query)
    
    # Group by product name and sum quantities
    top_products = query.values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:5]

    return JsonResponse({
        'labels': [p['product__name'] for p in top_products],
        'datasets': [{
            'label': 'Units Sold',
            'data': [p['total_quantity'] for p in top_products],
            'backgroundColor': [
                'rgba(255, 99, 132, 0.5)',
                'rgba(54, 162, 235, 0.5)',
                'rgba(255, 206, 86, 0.5)',
                'rgba(75, 192, 192, 0.5)',
                'rgba(153, 102, 255, 0.5)'
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)'
            ],
            'borderWidth': 1
        }]
    })

def get_sales_profit_chart(request):
    """Line chart showing sales and profit over time"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    sales_data = Sale.objects.filter(
        date__gte=start_date
    ).values('date__date').annotate(
        total_sales=Sum('total_amount'),
        total_profit=Sum('profit')
    ).order_by('date__date')

    return JsonResponse({
        'labels': [str(entry['date__date']) for entry in sales_data],
        'datasets': [
            {
                'label': 'Sales',
                'data': [float(entry['total_sales']) for entry in sales_data],
                'borderColor': 'rgba(54, 162, 235, 1)',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'fill': True
            },
            {
                'label': 'Profit',
                'data': [float(entry['total_profit']) for entry in sales_data],
                'borderColor': 'rgba(75, 192, 192, 1)',
                'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                'fill': True
            }
        ]
    })

def get_stock_status_chart(request):
    """Pie chart showing stock status distribution"""
    products = Product.objects.filter(is_active=True)
    
    out_of_stock = products.filter(stock_quantity=0).count()
    low_stock = products.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=F('min_stock_level')
    ).count()
    in_stock = products.filter(
        stock_quantity__gt=F('min_stock_level')
    ).count()

    return JsonResponse({
        'labels': ['Out of Stock', 'Low Stock', 'In Stock'],
        'datasets': [{
            'data': [out_of_stock, low_stock, in_stock],
            'backgroundColor': [
                'rgba(255, 99, 132, 0.5)',
                'rgba(255, 206, 86, 0.5)',
                'rgba(75, 192, 192, 0.5)'
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)'
            ],
            'borderWidth': 1
        }]
    })

def get_new_customers_chart(request):
    """Line chart showing new customer acquisitions over time"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    customers = Customer.objects.filter(
        created_at__gte=start_date
    ).values('created_at__date').annotate(
        count=Count('id')
    ).order_by('created_at__date')

    return JsonResponse({
        'labels': [str(entry['created_at__date']) for entry in customers],
        'datasets': [{
            'label': 'New Customers',
            'data': [entry['count'] for entry in customers],
            'borderColor': 'rgba(153, 102, 255, 1)',
            'backgroundColor': 'rgba(153, 102, 255, 0.1)',
            'fill': True
        }]
    })

def get_sales_by_category_chart(request):
    """Bar chart showing sales distribution by category"""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    sales_by_category = Sale.objects.filter(
        date__gte=start_date
    ).values(
        'items__product__category__name'
    ).annotate(
        total_sales=Sum('items__price_at_sale')
    ).order_by('-total_sales')

    return JsonResponse({
        'labels': [s['items__product__category__name'] or 'Uncategorized' for s in sales_by_category],
        'datasets': [{
            'label': 'Sales by Category',
            'data': [float(s['total_sales']) for s in sales_by_category],
            'backgroundColor': 'rgba(54, 162, 235, 0.5)',
            'borderColor': 'rgba(54, 162, 235, 1)',
            'borderWidth': 1
        }]
    }) 