from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    # Placeholder - will be implemented in future tasks
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]
