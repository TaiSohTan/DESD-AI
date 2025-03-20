from django.shortcuts import render
# Create your views here.
from django.http import HttpResponse
from .models import Invoice
from utils.pdf_generator import generate_invoice_pdf
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .permissions import IsFinanceTeam,IsAdminUser
from utils.stripe_payment import create_intent, create_checkout, verify_intent
import stripe
from django.views.decorators.csrf import csrf_exempt
import logging 
logger = logging.getLogger(__name__)


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
    
## Creating a Stripe Payment Session for the Invoices
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
            'error': 'Invoice ID Provided is Not Found'
        }, status=404)

    except Exception as Exp:
        return Response({
            'success': False,
            'error': str(Exp)
        }, status=400)
    
## Checking the Payment Status of an Invoice 
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

        # Update invoice status if payment is successful
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
            'error': 'Invoice ID Provided is Not Found'
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
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
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
                logger.info(f"Invoice {invoice_id} status updated to Paid")
    
    return HttpResponse(status=200)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
## Handles the views if the payment is a success
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
## Handles the views if the payment is a failure
def payment_cancel(request):
    invoice_id = request.GET.get('invoice_id')
    return Response({
        'success': False,
        'message': 'Payment cancelled',
        'invoice_id': invoice_id
    })