from rest_framework import serializers
from .models import CustomUser
from djoser.serializers import UserCreateSerializer

class UserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ['id','email','password','role','name']
        ## Cant retrieve pw only write
        extra_kwargs = {'password': {'write_only': True},'role': {'read_only': True}}

        def create(self,validated_data):
            user = CustomUser.objects.create_user(**validated_data)
            if CustomUser.objects.count() == 1:
                user.role = CustomUser.Roles.ADMIN
                user.save()
            return user

        

