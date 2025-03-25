from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet, InvoiceViewSet
from .views import download_invoice_pdf, create_payment_session, verify_payment_status,stripe_webhook,payment_success,payment_cancel
from django.urls import path
from .views import upload_claim, submit_feedback, feedback_success
from .views import upload_claim, show_prediction
from .views import (
    upload_claim, submit_feedback, feedback_success, show_prediction,
    accept_prediction, reject_prediction
)

# Register the UserViewSet with a router
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'invoices', InvoiceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('invoices/<int:invoice_id>/download/', download_invoice_pdf, name='download_invoice_pdf'),
    path('invoices/<int:invoice_id>/payment-session/', create_payment_session, name='create_payment_session'),
    path('invoices/<int:invoice_id>/payment-status/', verify_payment_status, name='verify_payment_status'),
    path('stripe-webhook/', stripe_webhook, name='stripe_webhook'),
    path('upload_claim/', upload_claim, name='upload_claim'),
    path('submit_feedback/<int:claim_id>/', submit_feedback, name='submit_feedback'),
    path('feedback_success/', feedback_success, name='feedback_success'),
    path('upload_claim/', upload_claim, name='upload_claim'),
    path('show_prediction/<int:claim_id>/', show_prediction, name='show_prediction'),
    path('accept_prediction/<int:claim_id>/', accept_prediction, name='accept_prediction'),
    path('reject_prediction/<int:claim_id>/', reject_prediction, name='reject_prediction'),
]