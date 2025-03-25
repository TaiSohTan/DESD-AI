from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Invoice, Claim, Feedback  
from utils.pdf_generator import generate_invoice_pdf
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .permissions import IsFinanceTeam, IsAdminUser
from utils.stripe_payment import create_intent, create_checkout, verify_intent
import stripe
from django.views.decorators.csrf import csrf_exempt
import logging 

logger = logging.getLogger(__name__)

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
                logger.info(f"Invoice {invoice_id} not found during webhook processing")
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

def upload_claim(request):
    """
    Handle claim document upload.
    """
    if request.method == 'POST':
        uploaded_file = request.FILES.get('uploaded_file')
        description = request.POST.get('description', '')
        
        if not uploaded_file:
            return render(request, 'claims/upload_claim.html', {
                'error': 'Please select a file to upload.'
            })
        
        try:
            claim = Claim.objects.create(uploaded_file=uploaded_file, description=description)
            
            predicted_value, confidence = predict_claim(claim)
            
            claim.predicted_value = predicted_value
            claim.confidence_level = confidence
            claim.save()
            
            return redirect('show_prediction', claim_id=claim.id)
        except Exception as e:
            return render(request, 'claims/upload_claim.html', {
                'error': 'Error occurred while saving claim: ' + str(e)
            })
    else:
        return render(request, 'claims/upload_claim.html')


def submit_feedback(request, claim_id):
    """
    Handle feedback submission for a specific claim.
    """
    claim = get_object_or_404(Claim, id=claim_id)
    
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback_text', '').strip()
        rating = request.POST.get('rating')
        
        if not feedback_text:
            return render(request, 'claims/submit_feedback.html', {
                'claim': claim,
                'error': 'Feedback content cannot be empty.'
            })
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5.")
        except (ValueError, TypeError):
            return render(request, 'claims/submit_feedback.html', {
                'claim': claim,
                'error': 'Please provide a valid rating (1-5).'
            })
        
        try:
            feedback = Feedback.objects.create(
                claim=claim,
                feedback_text=feedback_text,
                rating=rating
            )
            return render(request, 'claims/feedback_success.html', {
                'feedback': feedback
            })
        except Exception as e:
            return render(request, 'claims/submit_feedback.html', {
                'claim': claim,
                'error': 'Error occurred while saving feedback: ' + str(e)
            })
    else:
        return render(request, 'claims/submit_feedback.html', {
            'claim': claim
        })

def feedback_success(request):
    """
    Provide a separate feedback success page.
    """
    return render(request, 'claims/feedback_success.html')

def show_prediction(request, claim_id):
    claim = get_object_or_404(Claim, id=claim_id)
    return render(request, 'claims/show_prediction.html', {
        'claim': claim
    })

def predict_claim(claim):
    predicted_value = 1000.00
    confidence_level = 85.0
    return predicted_value, confidence_level

def accept_prediction(request, claim_id):
    """
    If the user accepts the prediction,
    redirect them to the initial upload page (or wherever you want).
    """
    if request.method == 'POST':
        claim = get_object_or_404(Claim, id=claim_id)
        return redirect('upload_claim') 

def reject_prediction(request, claim_id):
    """
    If the user rejects the prediction,
    redirect them to the feedback page to submit feedback.
    """
    if request.method == 'POST':
        claim = get_object_or_404(Claim, id=claim_id)
        return redirect('submit_feedback', claim_id=claim_id)

