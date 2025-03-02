from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

# Defining the Roles of Eacb of the Users
class Roles():
    Admin = 'admin'
    AIEngineer = 'AIEngineer'
    FinanceDepartment = 'FinanceDepartment'
    EndUser = 'EndUser'

# Defining the CustomUser class which is an extension of the AbstractUser class 
class CustomUser(AbstractUser):
    email = models.EmailField(unique= True ,max_length = 100)
    role = models.CharField(
        max_length = 10,
        choices = Roles.choices,
        default = Roles.EndUser
    )




    