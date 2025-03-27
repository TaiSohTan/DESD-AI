from django.shortcuts import render, redirect
# Create your views here.
from django.http import HttpResponse,response,JsonResponse,HttpResponseBadRequest
from .models import Invoice,Role,Prediction, User, MLModel
from utils.pdf_generator import generate_invoice_pdf
# Python standard library
import re
import logging
import stripe
from datetime import timedelta

# Django Library Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

# Django Rest Framework (DRF) Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

# Project imports - Models
from .models import User, Invoice, Role, Prediction
from .permissions import IsFinanceTeam, IsAdminUser

# Project imports - Utilities
from utils.ml_api_client import predict, health
from django.utils import timezone
import re
from utils.pdf_generator import generate_invoice_pdf
from utils.stripe_payment import create_checkout, verify_intent

# Configure logger
logger = logging.getLogger(__name__)

# Imports for AIEngineer Functionality
import os
import joblib
import shutil
from django.contrib import messages
from datetime import datetime, timedelta
from django.core.paginator import Paginator

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

@login_required
def prediction_history(request):
    """View for user's prediction history"""
    # Get the user's predictions
    predictions = Prediction.objects.filter(user=request.user)
    
    return render(request, 'prediction_history.html', {
        'predictions': predictions
    })

@login_required
def prediction_detail(request, prediction_id):
    """View for detailed prediction information"""
    try:
        prediction = Prediction.objects.get(id=prediction_id, user=request.user)
        
        return render(request, 'prediction_detail.html', {
            'prediction': prediction,
            'input_data': prediction.input_data,
            'result': prediction.result
        })
    except Prediction.DoesNotExist:
        messages.error(request, "Prediction not found or you don't have permission to access it.")
        return redirect('prediction_history')

@login_required
def prediction_feedback(request, prediction_id):
    """View for providing feedback on a prediction"""
    try:
        prediction = Prediction.objects.get(id=prediction_id, user=request.user)
        
        # Check if feedback has already been provided
        if prediction.is_reasonable is not None:
            messages.warning(request, "Feedback has already been provided for this prediction.")
            return redirect('prediction_detail', prediction_id=prediction.id)
        
        if request.method == 'POST':
            is_reasonable = request.POST.get('is_reasonable') == 'yes'
            
            prediction.is_reasonable = is_reasonable
            prediction.feedback_date = timezone.now()

            if not is_reasonable:
                proposed_settlement = request.POST.get('proposed_settlement')
                adjustment_rationale = request.POST.get('adjustment_rationale')
                
                if not proposed_settlement or not adjustment_rationale:
                    messages.error(request, "Please provide both a proposed settlement value and rationale.")
                    return render(request, 'prediction_feedback.html', {'prediction': prediction})
                
                prediction.proposed_settlement = float(proposed_settlement)
                prediction.adjustment_rationale = adjustment_rationale
                prediction.needs_review = True
                
                messages.info(request, "Your feedback has been recorded. This case has been flagged for supervisor review.")
            else:
                messages.success(request, "Thank you for confirming the settlement value.")
            
            prediction.save()
            return redirect('prediction_history')
        
        return render(request, 'prediction_feedback.html', {
            'prediction': prediction,
            'input_data': prediction.input_data,
            'result': prediction.result
        })
        
    except Prediction.DoesNotExist:
        messages.error(request, "Prediction not found or you don't have permission to access it.")
        return redirect('prediction_history')

@login_required
def submit_prediction_feedback(request):
    """Handle submission of feedback on a prediction"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method")
    
    prediction_id = request.POST.get('prediction_id')
    is_reasonable = request.POST.get('is_reasonable') == 'yes'
    
    try:
        prediction = Prediction.objects.get(id=prediction_id, user=request.user)
        
        # Update the prediction with feedback
        prediction.is_reasonable = is_reasonable
        prediction.feedback_date = timezone.now()
        
        if not is_reasonable:
            proposed_settlement = request.POST.get('proposed_settlement')
            adjustment_rationale = request.POST.get('adjustment_rationale')
            
            if not proposed_settlement or not adjustment_rationale:
                messages.error(request, "Please provide both a proposed settlement value and rationale.")
                return redirect('prediction_result', prediction_id=prediction_id)
            
            prediction.proposed_settlement = float(proposed_settlement)
            prediction.adjustment_rationale = adjustment_rationale
            prediction.needs_review = True
            
            messages.info(request, "Your feedback has been recorded. This case has been flagged for supervisor review.")
        else:
            messages.success(request, "Thank you for confirming the settlement value.")
        
        prediction.save()
        
        # Redirect to prediction history
        return redirect('prediction_history')
        
    except Prediction.DoesNotExist:
        messages.error(request, "Prediction not found or you don't have permission to access it.")
        return redirect('dashboard')
    except ValueError:
        messages.error(request, "Invalid proposed settlement value.")
        return redirect('prediction_result', prediction_id=prediction_id)
    except Exception as e:
        messages.error(request, f"Error processing feedback: {str(e)}")
        return redirect('prediction_history')


@login_required
def prediction_form(request):
    """View for the prediction form"""
    # Check if ML service is available
    ml_service_available = health()
    
    if request.method == 'POST':
        # Extract form data and convert to expected format
        input_data = {}
        
        # Process each field in the form - convert strings to appropriate types
        for key, value in request.POST.items():
            if key in ['csrfmiddlewaretoken']:
                continue
                
            # Convert boolean fields
            if value.lower() == 'true':
                input_data[key] = True
            elif value.lower() == 'false':
                input_data[key] = False
            # Convert numeric fields
            elif value and value.replace('.', '', 1).isdigit():
                input_data[key] = float(value)
            else:
                input_data[key] = value
        
        try:
            # Make prediction using client
            prediction_result = predict(input_data)
            
            # Get settlement value from the correct key
            settlement_value = prediction_result.get('settlement_value', 0)
            
            # Automatically save the prediction
            prediction = Prediction(
                user=request.user,
                input_data=input_data,
                result=prediction_result,
                settlement_value=settlement_value
            )
            prediction.save()
            
            # Render the result page with the prediction ID
            return render(request, 'prediction_result.html', {
                'prediction': prediction_result,
                'input_data': input_data,
                'prediction_id': prediction.id
            })
            
        except Exception as e:
            # Log the error
            print(f"Prediction error: {str(e)}")
            
            # Render the form again with an error message
            return render(request, 'prediction_form.html', {
                'error_message': f"Error making prediction: {str(e)}",
                'ml_service_available': False
            })
    
    # Render the initial form
    return render(request, 'prediction_form.html', {
        'ml_service_available': ml_service_available
    })

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
            'model_status': 'Active',  
            'recent_predictions': 145  
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

@login_required
def user_invoices(request):
    """View for displaying the logged-in user's invoices."""
    invoices = Invoice.objects.filter(user=request.user).order_by('-issued_date')
    return render(request, 'user_invoices.html', {'invoices': invoices})

@login_required
def download_invoice_pdf(request, invoice_id):
    """Allow users to download invoice PDF."""
    try:
        # Check if the user is finance team, admin, or the invoice owner
        if request.user.role in [Role.FINANCE_TEAM, Role.ADMIN]:
            # Finance team and admin can download any invoice
            invoice = Invoice.objects.get(id=invoice_id)
        else:
            # Regular users can only download their own invoices
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        
        buffer = generate_invoice_pdf(invoice)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_id}.pdf"'
        return response
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found or you do not have permission to access it.")
        
        # Redirect to the appropriate page based on user role
        if request.user.role in [Role.FINANCE_TEAM, Role.ADMIN]:
            return redirect('finance_invoice_list')
        else:
            return redirect('user_invoices')
    
## Creating a Stripe Payment Session for the Invoices
@login_required
def create_payment_session(request, invoice_id):
    """Redirect the logged-in user to the Stripe payment page for their unpaid invoice."""
    try:
        # Restrict access to the logged-in user's invoices
        invoice = Invoice.objects.get(id=invoice_id, user=request.user, status='Pending')
        domain_url = request.build_absolute_uri('/').rstrip('/')
        checkout_session = create_checkout(invoice, domain_url)

        if checkout_session:
            # Update the invoice with payment details - FIXED ACCESS METHODS
            invoice.payment_url = checkout_session.url
            # The payment_intent is retrievable from the session's attributes
            invoice.stripe_payment_intent_id = checkout_session.payment_intent
            invoice.save()
            
            # Add debug log to confirm values are saved
            print(f"Saved payment details: URL={invoice.payment_url}, Intent ID={invoice.stripe_payment_intent_id}")

            # Redirect the user to the Stripe payment page
            return redirect(checkout_session.url)
        else:
            messages.error(request, "Failed to create payment session. Please try again.")
            return redirect('user_invoices')

    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found or you do not have permission to access it.")
        return redirect('user_invoices')

    except Exception as exp:
        # Add detailed debugging information
        print(f"Payment session error: {str(exp)}")
        print(f"Payment session error type: {type(exp)}")
        if hasattr(exp, 'json_body'):
            print(f"Stripe error details: {exp.json_body}")
        messages.error(request, f"An error occurred: {str(exp)}")
        return redirect('user_invoices')

@login_required
def payment_success_view(request):
    """Handle successful payments and update invoice status."""
    session_id = request.GET.get('session_id')
    invoice_id = request.GET.get('invoice_id')
    
    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        
        # If no payment intent ID but we have a session ID, try to get the payment intent from the session
        if not invoice.stripe_payment_intent_id and session_id:
            try:
                # Retrieve the session to get the payment intent
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_intent:
                    invoice.stripe_payment_intent_id = session.payment_intent
                    invoice.save()
                    print(f"Retrieved payment intent {invoice.stripe_payment_intent_id} from session {session_id}")
            except Exception as e:
                print(f"Error retrieving session: {str(e)}")
        
        # Verify payment status and update invoice
        if invoice.stripe_payment_intent_id:
            payment_status = verify_intent(invoice.stripe_payment_intent_id)
            print(f"Payment status: {payment_status} for intent {invoice.stripe_payment_intent_id}")
            
            if payment_status == 'succeeded' and invoice.status == 'Pending':
                invoice.status = 'Paid'
                invoice.save()
                messages.success(request, "Payment successful! Your invoice has been marked as paid.")
            elif payment_status == 'succeeded':
                messages.info(request, "Payment was successful. This invoice was already marked as paid.")
            else:
                messages.warning(request, f"Payment status: {payment_status}. Please contact support if you believe this is an error.")
        else:
            messages.warning(request, "No payment was found for this invoice. Please try again or contact support.")
        
        return redirect('user_invoices')
    
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found or you do not have permission to access it.")
        return redirect('user_invoices')
@login_required
def payment_cancel_view(request):
    """Handle cancelled payments."""
    invoice_id = request.GET.get('invoice_id')
    
    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        messages.warning(request, "Payment was cancelled. Your invoice remains unpaid.")
        return redirect('user_invoices')
    
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found or you do not have permission to access it.")
        return redirect('user_invoices')

@login_required
def invoice_detail(request, invoice_id):
    """View for displaying the details of a single invoice."""
    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        
        # If there's a payment intent, check its status
        if invoice.stripe_payment_intent_id and invoice.status == 'Pending':
            payment_status = verify_intent(invoice.stripe_payment_intent_id)
            
            if payment_status == 'succeeded':
                invoice.status = 'Paid'
                invoice.save()
                messages.success(request, "Good news! Your payment has been confirmed.")
        
        return render(request, 'invoice_detail.html', {'invoice': invoice})
    
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found or you do not have permission to access it.")
        return redirect('user_invoices')

@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks for automatic payment status updates."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Extract invoice_id from metadata
        invoice_id = session.get('metadata', {}).get('invoice_id')
        if invoice_id:
            try:
                invoice = Invoice.objects.get(id=invoice_id)
                
                # Update the invoice status
                if invoice.status == 'Pending':
                    invoice.status = 'Paid'
                    invoice.save()
                    print(f"Invoice #{invoice_id} marked as paid via webhook")
            except Invoice.DoesNotExist:
                print(f"Invoice #{invoice_id} not found")
    
    # Return a response to acknowledge receipt of the event
    return HttpResponse(status=200)

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

@login_required
def finance_invoice_list(request):
    """View for finance team to list all invoices"""
    # Check permissions
    if request.user.role not in [Role.FINANCE_TEAM, Role.ADMIN]:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    
    # Get filters from request
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Start with all invoices
    invoices = Invoice.objects.all().order_by('-issued_date')
    
    # Apply filters
    if search_query:
        invoices = invoices.filter(
            Q(id__icontains=search_query) | 
            Q(user__email__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(invoices, 10)  # Show 10 invoices per page
    
    try:
        invoices = paginator.page(page)
    except PageNotAnInteger:
        invoices = paginator.page(1)
    except EmptyPage:
        invoices = paginator.page(paginator.num_pages)
    
    return render(request, 'invoice_list.html', {
        'invoices': invoices
    })

@login_required
def finance_invoice_create(request):
    """View for finance team to create a new invoice"""
    # Check permissions
    if request.user.role not in [Role.FINANCE_TEAM, Role.ADMIN]:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    
    # Get all users for the dropdown
    users = User.objects.all().order_by('email')
    
    if request.method == 'POST':
        # Process form data
        try:
            user_id = request.POST.get('user')
            description = request.POST.get('description', f'MLAAS Service Invoice')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            status = request.POST.get('status')
            
            # Validate required fields
            if not all([user_id, amount, due_date, status]):
                messages.error(request, "All fields are required.")
                return render(request, 'finance/invoice_form.html', {'users': users})
            
            # Create invoice
            invoice = Invoice(
                user_id=user_id,
                description=description,
                amount=amount,
                due_date=due_date,
                status=status
            )
            invoice.save()
            
            messages.success(request, f"Invoice #{invoice.id} created successfully.")
            return redirect('finance_invoice_detail', invoice_id=invoice.id)
            
        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")
    
    # Default due date (30 days from now)
    default_due_date = (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
    
    return render(request, 'invoice_form.html', {
        'users': users,
        'default_due_date': default_due_date
    })

@login_required
def finance_invoice_edit(request, invoice_id):
    """View for finance team to edit an existing invoice"""
    # Check permissions
    if request.user.role not in [Role.FINANCE_TEAM, Role.ADMIN]:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Get all users for the dropdown
        users = User.objects.all().order_by('email')
        
        if request.method == 'POST':
            # Process form data
            try:
                invoice.user_id = request.POST.get('user')
                invoice.description = request.POST.get('description', f'MLAAS Service Invoice')
                invoice.amount = request.POST.get('amount')
                invoice.due_date = request.POST.get('due_date')
                invoice.status = request.POST.get('status')
                
                # Validate required fields
                if not all([invoice.user_id, invoice.amount, invoice.due_date, invoice.status]):
                    messages.error(request, "All fields are required.")
                    # Add default_due_date for template
                    default_due_date = (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
                    return render(request, 'invoice_form.html', {
                        'invoice': invoice, 
                        'users': users,
                        'default_due_date': default_due_date
                    })
                
                invoice.save()
                
                messages.success(request, f"Invoice #{invoice.id} updated successfully.")
                return redirect('finance_invoice_detail', invoice_id=invoice.id)
                
            except Exception as e:
                messages.error(request, f"Error updating invoice: {str(e)}")
        
        # Add default_due_date for GET requests as well
        default_due_date = (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
        return render(request, 'invoice_form.html', {
            'invoice': invoice,
            'users': users,
            'default_due_date': default_due_date
        })
        
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect('finance_invoice_list')

@login_required
def finance_invoice_detail(request, invoice_id):
    """View for finance team to view invoice details"""
    # Check permissions
    if request.user.role not in [Role.FINANCE_TEAM, Role.ADMIN]:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        return render(request, 'invoice_findetail.html', {'invoice': invoice})
        
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect('finance_invoice_list')

@login_required
def finance_invoice_delete(request, invoice_id):
    """View for finance team to delete an invoice"""
    # Check permissions
    if request.user.role not in [Role.FINANCE_TEAM, Role.ADMIN]:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        invoice_id = invoice.id  # Save ID for the success message
        invoice.delete()
        
        messages.success(request, f"Invoice #{invoice_id} deleted successfully.")
        return redirect('finance_invoice_list')
        
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect('finance_invoice_list')

@login_required
def finance_invoice_verify_payment(request, invoice_id):
    """View for finance team to verify payment status"""
    # Check permissions
    if request.user.role not in [Role.FINANCE_TEAM, Role.ADMIN]:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Check if there's a payment intent
        if not invoice.stripe_payment_intent_id:
            messages.warning(request, "No payment has been initiated for this invoice.")
            return redirect('finance_invoice_detail', invoice_id=invoice.id)
        
        # Verify payment status
        payment_status = verify_intent(invoice.stripe_payment_intent_id)
        
        if payment_status == 'succeeded' and invoice.status == 'Pending':
            invoice.status = 'Paid'
            invoice.save()
            messages.success(request, "Payment verified and invoice marked as paid.")
        elif payment_status == 'succeeded':
            messages.info(request, "Payment has been verified. Invoice is already marked as paid.")
        else:
            messages.warning(request, f"Payment status: {payment_status}. Invoice remains pending.")
        
        return redirect('finance_invoice_detail', invoice_id=invoice.id)
        
    except Invoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect('finance_invoice_list')
    
## View for ML Model Management (AI ENGINEERS)
@login_required
def model_management(request):
    """View for AI Engineers to manage ML models"""
    # Check if user is AI Engineer
    if request.user.role != 'AI Engineer' and request.user.role != 'Admin':
        messages.error(request, "Access denied. AI Engineer privileges required.")
        return redirect('dashboard')
    
    # Handle form submission for model upload
    if request.method == 'POST':
        model_file = request.FILES.get('model_file')
        model_name = request.POST.get('model_name')
        model_type = request.POST.get('model_type')
        description = request.POST.get('description', '')
        set_active = request.POST.get('set_active') == 'on'
        
        # Validate required fields
        if not all([model_file, model_name, model_type]):
            messages.error(request, "Please provide all required fields: model file, name, and type.")
            return redirect('model_management')
        
        # Validate file is .pkl
        if not model_file.name.endswith('.pkl'):
            messages.error(request, "Only .pkl files are allowed.")
            return redirect('model_management')
        
        # Save model with provided info
        model = MLModel(
            name=model_name,
            model_type=model_type,
            description=description,
            file=model_file,
            uploaded_by=request.user,
            is_active=set_active
        )
        model.save()
        
        # If set as active, copy to FastAPI directory
        if set_active:
            try:
                # Generate destination filename
                dest_filename = f"active_model.pkl"
                
                # Get source path
                src_path = model.file.path
                
                # Define FastAPI directory path
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                fastapi_dir = os.path.join(base_dir, 'fastapi')
                
                # Create the directory if it doesn't exist
                if not os.path.exists(fastapi_dir):
                    os.makedirs(fastapi_dir)
                
                # Set destination path
                dest_path = os.path.join(fastapi_dir, dest_filename)
                
                # Copy the file
                shutil.copy2(src_path, dest_path)
                
                messages.success(request, f"Model '{model_name}' uploaded and set as active. FastAPI service will use this model for predictions.")
            except Exception as e:
                messages.warning(request, f"Model uploaded but failed to copy to FastAPI directory: {str(e)}")
        else:
            messages.success(request, f"Model '{model_name}' uploaded successfully.")
        
        return redirect('model_management')
    
    # Get all models grouped by type
    models = MLModel.objects.all().order_by('-uploaded_at')
    active_model = models.filter(is_active=True).first()

    # Check file existence for each model in both possible locations
    for model in models:
        try:
            # Path from Django model
            django_path = model.file.path
            
            # Alternative path in FastAPI directory
            filename = os.path.basename(model.file.name)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fastapi_media_path = os.path.join(base_dir, 'FastAPI', 'media', 'ml_models', filename)
            
            # Check both possible locations
            if os.path.exists(django_path) or os.path.exists(fastapi_media_path):
                model.file_exists = True
                # Debug print to see which path exists
                if os.path.exists(django_path):
                    print(f"File found in Django path: {django_path}")
                if os.path.exists(fastapi_media_path):
                    print(f"File found in FastAPI path: {fastapi_media_path}")
            else:
                model.file_exists = False
                print(f"File not found in either location:")
                print(f"Django path (checked): {django_path}")
                print(f"FastAPI path (checked): {fastapi_media_path}")
        except Exception as e:
            print(f"Error checking file existence: {str(e)}")
            model.file_exists = False
    
    return render(request, 'model_management.html', {
        'models': models,
        'active_model': active_model
    })

# Function to set a model as active
@login_required
def set_model_active(request, model_id):
    """AJAX view to set a model as active"""
    if request.user.role != 'AI Engineer' and request.user.role != 'Admin':
        return JsonResponse({"success": False, "error": "Permission denied"})
    
    try:
        # Get the model to activate
        model = MLModel.objects.get(id=model_id)
        
        # Deactivate all other models (this is handled in the save method)
        model.is_active = True
        model.save()
        
        # Copy model file to FastAPI directory with a generic name
        try:
            dest_filename = f"active_model.pkl"
            
            # Get source path
            src_path = model.file.path
            
            # Define FastAPI directory path
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fastapi_dir = os.path.join(base_dir, 'FastAPI')
            
            # Create the directory if it doesn't exist
            if not os.path.exists(fastapi_dir):
                os.makedirs(fastapi_dir)
            
            # Set destination path
            dest_path = os.path.join(fastapi_dir, dest_filename)
            
            # Copy the file
            shutil.copy2(src_path, dest_path)
            
            return JsonResponse({
                "success": True, 
                "message": f"Model {model.name} is now active for all predictions"
            })
        except Exception as e:
            return JsonResponse({
                "success": False, 
                "error": f"Failed to copy model file: {str(e)}"
            })
        
    except MLModel.DoesNotExist:
        return JsonResponse({"success": False, "error": "Model not found"})
    except Exception as e:
        error_msg = f"General error: {str(e)}, type: {type(e).__name__}"
        print(error_msg)
        return JsonResponse({"success": False, "error": str(e)})
    
# Function to delete an uploaded ml model
@login_required
def delete_model(request, model_id):
    """AJAX view to delete a model"""
    if request.user.role != 'AI Engineer' and request.user.role != 'Admin':
        return JsonResponse({"success": False, "error": "Permission denied"})
    
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Invalid request method"})
    
    try:
        # Get the model to delete
        model = MLModel.objects.get(id=model_id)
        
        # Don't allow deleting active models
        if model.is_active:
            return JsonResponse({
                "success": False, 
                "error": "Cannot delete an active model. Make another model active first."
            })
        
        # Get the file path before deleting the model
        file_path = model.file.path
        
        # Store name for the response message
        model_name = model.name
        
        # Delete the model from the database
        model.delete()
        
        # Remove the file from the filesystem if it exists
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File deleted: {file_path}")
            else:
                print(f"File not found: {file_path}")
        except Exception as file_error:
            print(f"Error deleting file: {str(file_error)}")
            # We still return success since the DB record was deleted
            return JsonResponse({
                "success": True, 
                "message": f"Model {model_name} was deleted from database but the file could not be removed: {str(file_error)}"
            })
        
        return JsonResponse({
            "success": True, 
            "message": f"Model {model_name} deleted successfully"
        })
        
    except MLModel.DoesNotExist:
        return JsonResponse({"success": False, "error": "Model not found"})
    except Exception as e:
        error_msg = f"Error deleting model: {str(e)}"
        print(error_msg)
        return JsonResponse({"success": False, "error": error_msg})

# View for AI Engineers to review all user prediction history
@login_required
def review_predictions(request):
    """View for AI Engineers to review all user predictions"""
    # Check if user is AI Engineer or Admin
    if request.user.role != 'AI Engineer' and request.user.role != 'Admin':
        messages.error(request, "Access denied. AI Engineer privileges required.")
        return redirect('dashboard')
    
    # Handle marking prediction as checked
    if request.method == 'POST' and 'prediction_id' in request.POST:
        prediction_id = request.POST.get('prediction_id')
        try:
            prediction = Prediction.objects.get(id=prediction_id)
            
            # Toggle the checked status
            prediction.is_checked = not prediction.is_checked
            
            # If we're checking it, also clear the needs_review flag
            if prediction.is_checked and prediction.needs_review:
                prediction.needs_review = False
                
            prediction.save()
            
            if prediction.is_checked:
                messages.success(request, f"Prediction #{prediction_id} marked as checked.")
            else:
                messages.info(request, f"Prediction #{prediction_id} unmarked.")
            
            return redirect('review_predictions')
        except Prediction.DoesNotExist:
            messages.error(request, "Prediction not found.")
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    
    # Get all predictions, ordered by newest first
    predictions = Prediction.objects.all().select_related('user').order_by('-timestamp')
    
    # Apply filters
    if status_filter == 'checked':
        predictions = predictions.filter(is_checked=True)
    elif status_filter == 'unchecked':
        predictions = predictions.filter(is_checked=False)
    elif status_filter == 'disputed':
        predictions = predictions.filter(is_reasonable=False)
    
    # Pagination
    paginator = Paginator(predictions, 20)  # Show 20 predictions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'review_predictions.html', {
        'page_obj': page_obj,
        'total_predictions': predictions.count(),
        'checked_count': predictions.filter(is_checked=True).count(),
        'unchecked_count': predictions.filter(is_checked=False).count(),
        'disputed_count': predictions.filter(is_reasonable=False).count(),
        'status_filter': status_filter,
    })

@login_required
def aiengineer_prediction_detail(request, prediction_id):
    """View for AI Engineers to see detailed prediction information"""
    # Check if user is AI Engineer or Admin
    if request.user.role != 'AI Engineer' and request.user.role != 'Admin':
        messages.error(request, "Access denied. AI Engineer privileges required.")
        return redirect('dashboard')
    
    try:
        prediction = Prediction.objects.get(id=prediction_id)
        
        # Handle marking prediction as checked
        if request.method == 'POST' and 'mark_checked' in request.POST:
            prediction.is_checked = True
            if prediction.needs_review:
                prediction.needs_review = False
            prediction.save()
            messages.success(request, f"Prediction #{prediction_id} marked as checked.")
            return redirect('aiengineer_prediction_detail', prediction_id=prediction_id)
        
        return render(request, 'aiengineer_prediction_detail.html', {
            'prediction': prediction,
            'input_data': prediction.input_data,
            'result': prediction.result,
            'user': prediction.user  # Pass user info to template
        })
    except Prediction.DoesNotExist:
        messages.error(request, "Prediction not found.")
        return redirect('review_predictions')