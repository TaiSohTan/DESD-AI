from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.
# Creating UserManager class. Required as we set email as the unique identifier for the user

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
        return self.create_user(email, name, password, role='Admin')
    
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
    description = models.CharField(max_length=500, default="MLAAS Service Invoice")  # Added this line


    def __str__(self):
        return f"Invoice {self.id} for {self.user.email}"

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    timestamp = models.DateTimeField(auto_now_add=True)
    input_data = models.JSONField()
    result = models.JSONField()
    settlement_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Feedback fields
    is_reasonable = models.BooleanField(null=True, default=None)
    proposed_settlement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    adjustment_rationale = models.TextField(null=True, blank=True)
    needs_review = models.BooleanField(default=False)
    feedback_date = models.DateTimeField(null=True, blank=True)

    is_checked = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Prediction for {self.user.name}: ${self.settlement_value}"
    
## Machine Learning Model
class MLModel(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='ml_models/')
    model_type = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    requires_scaling = models.BooleanField(default=False)
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({self.model_type}) - {status}"
    
    def save(self, *args, **kwargs):
        # If this model is being set as active, deactivate ALL other models
        if self.is_active:
            MLModel.objects.filter(is_active=True).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)