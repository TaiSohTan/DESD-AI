from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet, InvoiceViewSet
from .views import download_invoice_pdf, create_payment_session, verify_payment_status,stripe_webhook,payment_success,payment_cancel

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
]