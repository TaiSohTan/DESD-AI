from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.

class Claim(models.Model):
    uploaded_file = models.FileField(upload_to='claims/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    predicted_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Claim {self.id}"

class Feedback(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="feedbacks")
    feedback_text = models.TextField()
    rating = models.IntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {self.id} for Claim {self.claim.id}"

# User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, role='End User'):
        ## Email cannot be an empty field as it is an unique identifier
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None):
        user = self.create_user(email, name, password, role='Admin')
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
    
# Role Choices 
class Role(models.TextChoices):
    END_USER = "End User", "End User"
    ADMIN = "Admin", "Admin"
    AI_ENGINEER = "AI Engineer", "AI Engineer"
    FINANCE_TEAM = "Finance Team", "Finance Team"

# User Model (All Users)
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.END_USER
    )
    member_since = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
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

## Invoices Model (FinanceTeam)
class Invoice(models.Model):
    ## Create a Foriegn Key to User Model
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    issued_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    status = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Paid', 'Paid')])
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    payment_url = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"Invoice {self.id} for {self.user.email}"
