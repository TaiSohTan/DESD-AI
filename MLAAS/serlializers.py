from rest_framework import serializers
from . import User 

class UserSerializer(serializers.BaseSerializer):
    class Meta:
        model = User