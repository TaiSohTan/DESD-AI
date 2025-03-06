from rest_framework import permissions
from .models import Roles 

## Controls the Admin Permissions 
class kisAdmin(permissions.BasePermissions):
    def has_permission(self,request,view):
        return request.user.is_authenticated and request.user.role == Roles.ADMIN

## Controls the AI Engineer Permissions 
class isAIEngineer(permissions.BasePermissions):
    def has_permission(self,request,view):
        return request.user.is_authenticated and request.user.role == Roles.AI_ENGINEER
    
## Controls the Finance Department Permissions 
class isFinance(permissions.BasePermission):
    def has_permission(self,request,view):
        return request.user.is_authenticated and request.user.role == Roles.FINANCE_DEPARTMENT
    
## Controls the End User Permissions 
class isEndUser(permissions.BasePermission):
    def has_permission(self,request,view):
        return request.user.is_authenticated and request.user.role == Roles.END_USER