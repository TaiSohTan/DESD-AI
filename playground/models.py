from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime 

# Create your models here.

# Defining the Roles of Each of the Users
class Roles(models.TextChoices):
    ADMIN = 'Admin', 'Admin'
    AI_ENGINEER = 'AIEngineer', 'AI Engineer'
    FINANCE_DEPARTMENT = 'FinanceDepartment', 'Finance Department'
    END_USER = 'EndUser', 'End User'

# Defining the CustomUser class which is an extension of the AbstractUser class 
class CustomUser(AbstractUser):
    email = models.EmailField(unique= True ,max_length = 100)
    name = models.CharField(max_length = 50, blank = False)
    role = models.CharField(
        choices = Roles.choices,
        default = Roles.END_USER
    )
    member_since = models.DateTimeField(default=datetime.datetime.now)

    def is_admin(self):
        return self.role == Roles.ADMIN
    
    def is_ai_engineer(self):
        return self.role == Roles.AI_ENGINEER

    def is_finance_department(self):
        return self.role == Roles.FINANCE_DEPARTMENT

    def is_end_user(self):
        return self.role == Roles.END_USER



    