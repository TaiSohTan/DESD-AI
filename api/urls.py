from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet

# Register the UserViewSet with a router
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
]