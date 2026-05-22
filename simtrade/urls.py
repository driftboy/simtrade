from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.http import HttpResponse
from apps.documents.models import Document, DocumentTemplate

# 单证管理临时视图
def document_create(request):
    """单证创建页面 - 临时实现"""
    templates = DocumentTemplate.objects.filter(is_active=True)
    return render(request, 'documents/create.html', {'templates': templates})

def document_preview(request, id):
    """单证预览页面 - 临时实现"""
    try:
        document = Document.objects.get(pk=id)
    except Document.DoesNotExist:
        return HttpResponse('单证不存在', status=404)
    return render(request, 'documents/preview.html', {'document': document})

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
    path('documents/', lambda r: render(r, 'documents/list.html'), name='document-list'),
    path('documents/create/', document_create, name='document-create'),
    path('documents/<int:id>/preview/', document_preview, name='document-preview'),
]
