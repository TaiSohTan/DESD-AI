from rest_framework import viewsets, permissions
from .models import User,Role
from rest_framework.response import Response
from .serializers import CustomUserSerializer
from rest_framework.decorators import action

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['assign_role']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def update_role(self, request, pk=None):
        user = self.get_object()
        if request.user.role != Role.ADMIN:
            return Response({'error': 'Only Admins can assign roles'}, status=403)
        
        role = request.data.get('role')
        if role not in [choice[0] for choice in Role.choices]:
            return Response({'error': 'Invalid role'}, status=400)
        
        user.role = role
        user.save()
        return Response({'message': f'Role updated to {role}'}, status=200)

