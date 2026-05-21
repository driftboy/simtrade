"""
URL configuration for documents app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.documents import views

app_name = 'documents'

router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('templates/', views.template_list, name='template-list'),
    path('documents/<int:pk>/submit/', views.submit_document, name='document-submit'),
    path('documents/<int:pk>/approve/', views.approve_document, name='document-approve'),
    path('documents/<int:pk>/reject/', views.reject_document, name='document-reject'),
]
