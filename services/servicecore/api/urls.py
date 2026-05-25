from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('odoo/products/', views.OdooRawProductListView.as_view(), name='odoo_products'),
    path('integrate/products/', views.IntegrateProductsView.as_view(), name='integrate_products'),
    path('products/', views.ProductListCreateView.as_view(), name='product_list_create'),
    path('products/catalogs/', views.CatalogListCreateView.as_view(), name='catalog_list_create'),
    path('products/catalogs/<str:catalog_id>/', views.CatalogDetailView.as_view(), name='catalog_detail'),
    path('products/products/<str:product_id>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<str:sku>/enrich/', views.ProductEnrichmentView.as_view(), name='product_enrich'),
    path('internal/sync-product/', views.InternalProductSyncView.as_view(), name='internal_sync_product'),
    path('internal/odoo/products/', views.OdooProductListView.as_view(), name='internal_odoo_products'),
    path('orders/', views.OrderListCreateView.as_view(), name='order_list_create'),
    path('transactions/', views.TransactionListCreateView.as_view(), name='transaction_list_create'),
]
