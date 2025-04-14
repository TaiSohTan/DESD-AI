from django.urls import path
from django.conf.urls.static import static
from django.conf import settings

from .views import (
    # Static page views
    home, about, services, pricing, contact,
    
    # Authentication views
    login_view, register_view, logout_view, password_reset, refresh_token_view, dashboard, user_profile, account_settings,
    
    # User management views
    user_management, add_user, edit_user, change_user_role, delete_user,
    
    # Prediction and feedback views
    prediction_form, submit_prediction_feedback, prediction_history, prediction_detail, prediction_feedback,
    
    # Model management views
    model_management, set_model_active, delete_model,
    
    # AI Engineer views
    review_predictions, aiengineer_prediction_detail,
    
    # User invoice views
    user_invoices, download_invoice_pdf, create_payment_session, invoice_detail, stripe_webhook,
    
    # Finance team invoice views
    finance_invoice_list, finance_invoice_create, finance_invoice_detail, finance_invoice_edit, 
    finance_invoice_delete, finance_invoice_verify_payment,
    
    # Payment views
    payment_success_view, payment_cancel_view,
    
    # Admin analytics views
    admin_analytics, log_api_metrics, export_analytics_data,
)

# Group URLs by functional area for better organization
urlpatterns = [
    # Static Pages
    path('', home, name='home'),
    path('about/', about, name='about'),
    path('services/', services, name='services'),
    path('pricing/', pricing, name='pricing'),
    path('contact/', contact, name='contact'),
    
    # Authentication URLs
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('reset-password/', password_reset, name='password_reset'),
    path('refresh-token/', refresh_token_view, name='refresh_token'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', user_profile, name='user_profile'),
    path('settings/', account_settings, name='account_settings'),
    
    # User Management URLs
    path('user-management/', user_management, name='user_management'),
    path('user-management/add/', add_user, name='add_user'),
    path('user-management/edit/<int:user_id>/', edit_user, name='edit_user'),
    path('user-management/change-role/<int:user_id>/', change_user_role, name='change_user_role'),
    path('user-management/delete/<int:user_id>/', delete_user, name='delete_user'),
    
    # Prediction and Feedback URLs
    path('predict/', prediction_form, name='prediction_form'),
    path('predict/feedback/', submit_prediction_feedback, name='submit_prediction_feedback'),
    path('predict/history/', prediction_history, name='prediction_history'),
    path('predict/detail/<int:prediction_id>/', prediction_detail, name='prediction_detail'),
    path('predict/feedback/<int:prediction_id>/', prediction_feedback, name='prediction_feedback'),
    
    # Model Management URLs
    path('model-management/', model_management, name='model_management'),
    path('set-model-active/<int:model_id>/', set_model_active, name='set_model_active'),
    path('delete-model/<int:model_id>/', delete_model, name='delete_model'),
    
    # AI Engineer URLs
    path('review-predictions/', review_predictions, name='review_predictions'),
    path('aiengineer-prediction-detail/<int:prediction_id>/', aiengineer_prediction_detail, 
         name='aiengineer_prediction_detail'),
    
    # User Invoice URLs
    path('user/invoices/', user_invoices, name='user_invoices'),
    path('user/invoices/<int:invoice_id>/', invoice_detail, name='invoice_detail'),
    path('user/invoices/<int:invoice_id>/download/', download_invoice_pdf, name='download_invoice_pdf'),
    path('user/invoices/<int:invoice_id>/pay/', create_payment_session, name='create_payment_session'),
    
    # Payment URLs
    path('user/payment/success/', payment_success_view, name='payment_success_view'),
    path('user/payment/cancel/', payment_cancel_view, name='payment_cancel_view'),
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),
    
    # Finance Team Invoice Management
    path('finance/invoices/', finance_invoice_list, name='finance_invoice_list'),
    path('finance/invoices/create/', finance_invoice_create, name='finance_invoice_create'),
    path('finance/invoices/<int:invoice_id>/', finance_invoice_detail, name='finance_invoice_detail'),
    path('finance/invoices/<int:invoice_id>/edit/', finance_invoice_edit, name='finance_invoice_edit'),
    path('finance/invoices/<int:invoice_id>/delete/', finance_invoice_delete, name='finance_invoice_delete'),
    path('finance/invoices/<int:invoice_id>/verify-payment/', finance_invoice_verify_payment, 
         name='finance_invoice_verify_payment'),
         
    # Admin Analytics URLs - Changed from 'admin/analytics/' to 'analytics/' to avoid conflict
    path('analytics/', admin_analytics, name='admin_analytics'),
    path('analytics/export/', export_analytics_data, name='export_analytics_data'),
    path('api/log-metrics/', log_api_metrics, name='log_api_metrics'),
]