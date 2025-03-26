from djoser.serializers import UserCreateSerializer, UserSerializer as DjoserUserSerializer
from rest_framework import serializers
from .models import User, Invoice 

# User Serializer using Djoser
class CustomUserSerializer(DjoserUserSerializer):
    class Meta:
        model = User
        fields = ['email', 'name', 'role', 'member_since']

# Custom Registration Serializer
class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ['email', 'name', 'password']

# Invoice Serializer
class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'user', 'amount', 'issued_date', 'due_date', 'status']