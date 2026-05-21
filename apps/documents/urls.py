from django.urls import path
from django.views.generic import RedirectView

app_name = 'documents'

urlpatterns = [
    path('', RedirectView.as_view(url='admin/', permanent=False)),
]