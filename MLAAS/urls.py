from django.urls import path,include
from rest_framework.routers import DefaultRouter

Router = DefaultRouter()

urlpatterns = [
    path('', include(Router.urls))
]