from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.users.urls')),
    path('', include('apps.users.urls')),
    path('api/v1/documents/', include('apps.documents.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/', include('apps.transactions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 页面路由
urlpatterns += [
    path('market/', lambda r: render(r, 'products/market.html'), name='market'),
    path('transactions/', lambda r: render(r, 'transactions/list.html'), name='transaction-list'),
    path('transactions/<int:id>/', lambda r, id: render(r, 'transactions/detail.html'), name='transaction-detail'),
]
