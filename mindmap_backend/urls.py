from django.contrib import admin
from django.urls import path, include
from api.views import health  # Import health view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('health/', health), # Added root health check
]
