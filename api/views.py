from django.shortcuts import render
# Create your views here.
from django.http import HttpResponse,response,JsonResponse
from .models import Invoice,Role
from utils.pdf_generator import generate_invoice_pdf
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .permissions import IsFinanceTeam,IsAdminUser
from utils.stripe_payment import  create_checkout, verify_intent
import stripe
from django.views.decorators.csrf import csrf_exempt
import logging 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User
import re
logger = logging.getLogger(__name__)

## Rendering the home page
def home(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    return render(request,'home.html')

## Rendering other static HTML Pages
def about(request):
    return render(request,'about.html')

def services(request):
    return render(request,'services.html')

def pricing(request):
    return render(request,'pricing.html')

def contact(request):
    return render(request,'contact.html')

# Registration view function
def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Basic validation
        if not all([name, email, password, confirm_password]):
            return render(request, 'register.html', {'error_message': 'All fields are required'})
        
        if password != confirm_password:
            return render(request, 'register.html', {'error_message': 'Passwords do not match'})
        
        # Check password strength
        if len(password) < 8:
            return render(request, 'register.html', {'error_message': 'Password must be at least 8 characters long'})
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error_message': 'Email is already registered'})
        
        # Create new user
        try:
            user = User.objects.create_user(email=email, name=name, password=password)
            user.save()
            
            # Automatically log in the user
            login(request, user)
            
            # Redirect to home page or display success message
            return redirect('home')
        except Exception as e:
            return render(request, 'register.html', {'error_message': f'Registration error: {str(e)}'})
    
    return render(request, 'register.html')

## Rendering Dashboard
@login_required
def dashboard(request):
    user = request.user
    
    # Base context with user info
    context = {
        'user': user
    }
    
    # Add role-specific context data
    if user.role == 'ADMIN':
        # Add admin-specific data
        context.update({
            'total_users': User.objects.count(),
            'recent_registrations': User.objects.order_by('-date_joined')[:5]
        })
    elif user.role == 'FINANCE_TEAM':
        # Add finance team-specific data
        context.update({
            'pending_invoices': Invoice.objects.filter(status='Pending').count(),
            'recent_payments': Invoice.objects.filter(status='Paid').order_by('-updated_at')[:5]
        })
    elif user.role == 'AI_ENGINEER':
        # Add AI engineer-specific data
        context.update({
            'model_status': 'Active',  # This would come from your ML system
            'recent_predictions': 145  # This would come from your ML system
        })
    else:
        # Add regular user-specific data
        user_invoices = Invoice.objects.filter(user=user)
        context.update({
            'total_predictions': 0,  # Would come from your prediction model
            'invoices': user_invoices
        })
    
    return render(request, 'dashboard.html', context)

# In your login_view function in views.py
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Basic validation
        if not all([email, password]):
            return render(request, 'login.html', {'error_message': 'Email and password are required'})
        
        # Authenticate user
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            # Log in the user
            login(request, user)
            
            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            # Prepare the response
            response = redirect('dashboard')
            
            # Set HttpOnly cookie with the JWT token (for development)
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,   
                secure=False,    # Since Running LocalHost No Need for SSL/TLS
                samesite='Lax',  
                max_age=3600     # 1 hour expiry (Seconds)
            )
            
            # Set refresh token as well
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=False,    
                samesite='Lax',
                max_age=86400    # 1 day expiry
            )
            
            return response
        else:
            return render(request, 'login.html', {'error_message': 'Invalid email or password'})
    
    return render(request, 'login.html')

## Logout View Function
def logout_view(request):
    # Django Logout 
    logout(request)
    
    # Create response object
    response = redirect('home')
    
    # Deleting the cookies
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    
    return response

# Password Reset Mechanism Just use Email and FullName in this case but 
# IRL use email and token based password reset. Security Vulns 
def password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        full_name = request.POST.get('full_name')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Basic validation
        if not all([email, full_name, new_password, confirm_password]):
            return render(request, 'password_reset.html', {
                'error_message': 'All fields are required'
            })
        
        if new_password != confirm_password:
            return render(request, 'password_reset.html', {
                'error_message': 'Passwords do not match'
            })
        
        if len(new_password) < 8:
            return render(request, 'password_reset.html', {
                'error_message': 'Password must be at least 8 characters long'
            })
        
        # Try to find the user
        try:
            user = User.objects.get(email=email)
            
            # Verify full name
            if user.name != full_name:
                return render(request, 'password_reset.html', {
                    'error_message': 'The information you provided does not match our records'
                })
            
            # Reset the password
            user.set_password(new_password)
            user.save()
            
            return render(request, 'password_reset.html', {
                'success_message': 'Your password has been reset successfully. You can now log in with your new password.'
            })
            
        except User.DoesNotExist:
            # For security, don't reveal that the user doesn't exist
            return render(request, 'password_reset.html', {
                'error_message': 'The information you provided does not match our records'
            })
    
    return render(request, 'password_reset.html')

@login_required
def user_management(request):
    """View for the user management page (admin only)"""
    # Check if user is admin
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    # Get all users
    users = User.objects.all().order_by('name')
    
    return render(request, 'user_management.html', {'users': users})

@login_required
def add_user(request):
    """Add a new user (admin only)"""
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        
        # Validate input
        if not all([name, email, password, role]):
            messages.error(request, "All fields are required.")
            return redirect('user_management')
        
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('user_management')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect('user_management')
        
        # Create user
        try:
            user = User.objects.create_user(email=email, name=name, password=password, role=role)
            user.save()
            messages.success(request, f"User {name} created successfully.")
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
        
        return redirect('user_management')
    
    return redirect('user_management')

@login_required
def edit_user(request, user_id):
    """Edit a user (admin only)"""
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    user_to_edit = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        
        # Validate input
        if not all([name, email]):
            messages.error(request, "Name and email are required.")
            return redirect('user_management')
        
        # Check if email exists and belongs to another user
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect('user_management')
        
        # Update user
        try:
            user_to_edit.name = name
            user_to_edit.email = email
            user_to_edit.save()
            messages.success(request, f"User {name} updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating user: {str(e)}")
        
        return redirect('user_management')
    
    return redirect('user_management')

@login_required
def change_user_role(request, user_id):
    """Change a user's role (admin only)"""
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    user_to_change = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        role = request.POST.get('role')
        
        # Validate input
        if not role:
            messages.error(request, "Role is required.")
            return redirect('user_management')
        
        # Don't allow changing the last admin
        if user_to_change.role == Role.ADMIN and role != Role.ADMIN:
            admin_count = User.objects.filter(role=Role.ADMIN).count()
            if admin_count <= 1:
                messages.error(request, "Cannot change the role of the last admin.")
                return redirect('user_management')
        
        # Update user role
        try:
            user_to_change.role = role
            user_to_change.save()
            messages.success(request, f"Role for {user_to_change.name} changed to {role} successfully.")
        except Exception as e:
            messages.error(request, f"Error changing role: {str(e)}")
        
        return redirect('user_management')
    
    return redirect('user_management')

@login_required
def delete_user(request, user_id):
    """Delete a user (admin only)"""
    if request.user.role != Role.ADMIN:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    user_to_delete = get_object_or_404(User, id=user_id)
    
    # Don't allow deleting yourself
    if user_to_delete.id == request.user.id:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_management')
    
    # Don't allow deleting the last admin
    if user_to_delete.role == Role.ADMIN:
        admin_count = User.objects.filter(role=Role.ADMIN).count()
        if admin_count <= 1:
            messages.error(request, "Cannot delete the last admin.")
            return redirect('user_management')
    
    if request.method == 'POST':
        try:
            name = user_to_delete.name
            user_to_delete.delete()
            messages.success(request, f"User {name} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting user: {str(e)}")
        
        return redirect('user_management')
    
    return redirect('user_management')

## Download PDF Invoice 
def download_invoice_pdf(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        buffer = generate_invoice_pdf(invoice)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_id}.pdf"'
        return response
    except Invoice.DoesNotExist:
        return HttpResponse("Invoice not found.", status=404)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_session(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        domain_url = request.build_absolute_uri('/').rstrip('/')
        checkout_session = create_checkout(invoice, domain_url)
        if checkout_session:
            invoice.payment_url = checkout_session.url
            invoice.stripe_payment_intent_id = checkout_session.payment_intent
            invoice.save()
            return Response({
                'success': True,
                'checkout_url': checkout_session.url
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to create payment session'
            }, status=400)
    except Invoice.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invoice ID provided is not found'
        }, status=404)
    except Exception as Exp:
        return Response({
            'success': False,
            'error': str(Exp)
        }, status=400)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment_status(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        if not invoice.stripe_payment_intent_id:
            return Response({
                'success': True,
                'status': 'Not Initiated',
                'invoice_status': invoice.status
            })
        
        payment_status = verify_intent(invoice.stripe_payment_intent_id)
        if payment_status == 'succeeded' and invoice.status == 'Pending':
            invoice.status = 'Paid'
            invoice.save()
        return Response({
            'success': True,
            'status': payment_status,
            'invoice_status': invoice.status
        })
    except Invoice.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invoice ID provided is not found'
        }, status=404)
    except Exception as Exp:
        return Response({
            'success': False,
            'error': str(Exp)
        }, status=400)
    
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        invoice_id = payment_intent['metadata'].get('invoice_id')
        if invoice_id:
            try:
                invoice = Invoice.objects.get(id=invoice_id)
                invoice.status = 'Paid'
                invoice.save()
                logger.info(f"Invoice {invoice_id} status updated to Paid")
            except Invoice.DoesNotExist:
                logger.info(f"Invoice {invoice_id} status not updated to Paid")
    
    return HttpResponse(status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_success(request):
    session_id = request.GET.get('session_id')
    invoice_id = request.GET.get('invoice_id')
    return Response({
        'success': True,
        'message': 'Payment successful',
        'session_id': session_id,
        'invoice_id': invoice_id
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_cancel(request):
    invoice_id = request.GET.get('invoice_id')
    return Response({
        'success': False,
        'message': 'Payment cancelled',
        'invoice_id': invoice_id
    })

## Handles Refresh Token Views
def refresh_token_view(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        return JsonResponse({'error': 'Refresh token not found'}, status=401)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        response = JsonResponse({'success': True})
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,  # Environment-aware
            samesite='Lax',
            max_age=3600
        )
        
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=401)
