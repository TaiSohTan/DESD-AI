from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime 

# Create your models here.

# Defining the Roles of Each of the Users
class Roles():
    Admin = 'Admin'
    AIEngineer = 'AIEngineer'
    FinanceDepartment = 'FinanceDepartment'
    EndUser = 'EndUser'

# Defining the CustomUser class which is an extension of the AbstractUser class 
class CustomUser(AbstractUser):
    email = models.EmailField(unique= True ,max_length = 100)
    name = models.CharField(max_length = 50)
    role = models.CharField(
        choices = Roles.choices,
        default = Roles.EndUser
    )




    