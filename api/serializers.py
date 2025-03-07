from djoser.serializers import UserCreateSerializer, UserSerializer as DjoserUserSerializer
from .models import User 

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