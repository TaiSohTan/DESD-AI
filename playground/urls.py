from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .viewsets import CustomUserViewSet

Router = DefaultRouter()
Router.register(r'users',CustomUserViewSet)

urlpatterns = [
    path('', include(Router.urls))
]