from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.
# Creating UserManager class. Required as we set email as the unique identifier for the user

# User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, role='EndUser'):
        ## Email cannot be an empty field as it is an unique identifier
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None):
        return self.create_user(email, name, password, role='Admin')
    
# Role Choices
class Role(models.TextChoices):
    END_USER = "EndUser", "End User"
    ADMIN = "Admin", "Admin"
    AI_ENGINEER = "AI Engineer", "AI Engineer"
    FINANCE_TEAM = "FinanceTeam", "Finance Team"

# User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.END_USER
    )
    member_since = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    def save(self, *args, **kwargs):
        # First user gets Admin role
        if not User.objects.exists():  
            self.role = Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
