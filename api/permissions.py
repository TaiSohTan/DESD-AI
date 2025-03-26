from rest_framework import permissions 
from .models import Role

## AdminPermissions
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == Role.ADMIN

## FinanceTeamPermissions 
class IsFinanceTeam(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == Role.FINANCE_TEAM
    
## AIEngineerPermissions 
class IsAIEngineer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == Role.AI_ENGINEER
    