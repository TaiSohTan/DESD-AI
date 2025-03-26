"""
URL configuration for desd project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path,include
from api.views import payment_success,payment_cancel
from api.views import home,about,services,pricing,contact
from api.views import login_view,register_view,logout_view,password_reset,refresh_token_view,dashboard
from api.views import user_management,add_user,edit_user,change_user_role,delete_user
from api.views import prediction_form,submit_prediction_feedback,prediction_history,prediction_detail,prediction_feedback
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    # Static Pages
    path('',home,name='home'),
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
    # API URLs
    path('api/', include('api.urls')),
    ## Djoser and JWT Tojen URLs
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    ## Payment Redirects
    path('payment-success/',payment_success,name='payment_success'),
    path('payment-failed/',payment_cancel,name='payment_cancel'),
    ## User Management URLs
    path('user-management/', user_management, name='user_management'),
    path('user-management/add/', add_user, name='add_user'),
    path('user-management/edit/<int:user_id>/', edit_user, name='edit_user'),
    path('user-management/change-role/<int:user_id>/', change_user_role, name='change_user_role'),
    path('user-management/delete/<int:user_id>/', delete_user, name='delete_user'),
    ## Prediction and Feedback URLs
    path('predict/', prediction_form, name='prediction_form'),
    path('predict/feedback/', submit_prediction_feedback, name='submit_prediction_feedback'),
    path('predict/history/', prediction_history, name='prediction_history'),
    path('predict/detail/<int:prediction_id>/', prediction_detail, name='prediction_detail'),
    path('predict/feedback/<int:prediction_id>/', prediction_feedback, name='prediction_feedback'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)