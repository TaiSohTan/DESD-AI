import stripe
from django.conf import settings
from django.urls import reverse
from api.models import Invoice 

## Private Stripe API Key
stripe.api_key = settings.STRIPE_SECRET_KEY

## Create a Stripe Payment Intent for the Invoice 
def create_intent(Invoice):
    try:    
        amount = int(Invoice.amount * 100)
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='gbp',
            metadata={'invoice_id' : Invoice.id ,
                      'invoice_user_email' : Invoice.user.email
                      },
            description=f'Invoice {Invoice.id} for {Invoice.user.email}',
            automatic_payment_methods= True 
        )
        return {
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id
        }
    except Exception as Exp:
        print(f"Error Occured When Creating Payment Intent: str{Exp}")
        return None
    
## Create a Stripe Checkout Session for the Payment 
def create_checkout(Invoice, domain_urls):
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'gbp',
                        'product_data': {
                            'name': f'Invoice {Invoice.id}',
                        },
                        'unit_amount': int(Invoice.amount * 100),
                    },
                    'quantity': 1,
                },
            ],
        metadata={'invoice_id' : Invoice.id },
        mode='payment',
        success_url = domain_urls + f'/payment-success?session_id={{CHECKOUT_SESSION_ID}}&invoice_id={Invoice.id}',
        cancel_url = domain_urls + f'/payment-cancelled?invoice_id={Invoice.id}',
        )
        return checkout_session
    except Exception as Exp:
        print(f"Error Occured When Trying to Create Checkout Session: str{Exp}")
        return None 
    
## Verify the Payment Intent Status 
def verify_intent(payment_intent_id):
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return intent.status
    except Exception as exp:
        print(f"Error Occured When Trying to Verify Payment Intent: str{exp}")
        return None
