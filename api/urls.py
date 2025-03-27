from django.urls import path, include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet, InvoiceViewSet

# Register the UserViewSet with a router
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'invoices', InvoiceViewSet)

urlpatterns = [
    path('', include(router.urls))
]