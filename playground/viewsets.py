from rest_framework import viewsets, status, permissions
from .models import CustomUser 
from .serializers import UserCreateSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.isAdmin():
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=CustomUser.id)
    
    def update_role(self, serializer):
        user = self.request.user 
        if user.isAdmin():
            serializer.save()
        else:
            serializer.save(role=user.role)            

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser])
    def update_role(self,request,pk):
        user = self.get.object(pk=pk)
        role = request.data.get('role')
        if role and role in dict(CustomUser.Roles.choices):
            user.role = role
            user.save()
            return Response({'status':'Role Updated'}, status = status.HTTP_200_OK)
        else :
            return Response({'status':'Invalid Role!!'}, status = status.HTTP_400_BAD_REQUEST)