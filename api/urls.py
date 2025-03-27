from django.urls import path, include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet, InvoiceViewSet
from .views import download_invoice_pdf, create_payment_session, verify_payment_status,stripe_webhook,payment_success,payment_cancel, model_management, set_model_active, delete_model, review_predictions, aiengineer_prediction_detail

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
    path('model-management/', model_management, name='model_management'),
    path('set-model-active/<int:model_id>/', set_model_active, name='set_model_active'),
    path('delete-model/<int:model_id>/', delete_model, name='delete_model'),
    path('review-predictions/', review_predictions, name='review_predictions'),
    path('aiengineer-prediction-detail/<int:prediction_id>/', aiengineer_prediction_detail, name='aiengineer_prediction_detail')
]