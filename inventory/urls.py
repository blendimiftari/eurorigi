from django.urls import path
from . import views

app_name = 'inventory'
 
urlpatterns = [
    path('chart/stock-levels/', views.get_stock_levels_chart, name='chart_stock_levels'),
    path('chart/top-selling/', views.get_top_selling_products, name='chart_top_selling'),
    path('chart/sales-profit/', views.get_sales_profit_chart, name='chart_sales_profit'),
    path('chart/stock-status/', views.get_stock_status_chart, name='chart_stock_status'),
    path('chart/new-customers/', views.get_new_customers_chart, name='chart_new_customers'),
    path('chart/sales-by-category/', views.get_sales_by_category_chart, name='chart_sales_by_category'),
    path('api/product/<int:product_id>/price/', views.get_product_price, name='get_product_price'),
    
    # POS URLs
    path('pos/', views.pos_view, name='pos'),
    path('api/product/barcode/<str:barcode>/', views.get_product_by_barcode, name='get_product_by_barcode'),
    path('api/sale/create/', views.create_sale, name='create_sale'),
] 