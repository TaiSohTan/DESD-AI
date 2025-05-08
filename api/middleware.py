## This file is dedicated to the middleware functionality for the Cookies carrying the User Auth Token 
from django.utils.functional import SimpleLazyObject
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AnonymousUser
import time
from django.utils import timezone
from api.models import APIMetrics

def get_user_from_token(request):
    ## Get the user from the JWT token in the cookie.
    token = request.COOKIES.get('access_token')
    if not token:
        return AnonymousUser()
    
    ## Add the token to the Authorization header
    request.META['HTTP_AUTHORIZATION'] = f"Bearer {token}"
    
    auth = JWTAuthentication()
    try:
        validated_token = auth.get_validated_token(token)
        user = auth.get_user(validated_token)
        return user
    except Exception:
        return AnonymousUser()

class JWTCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_user_from_token(request))
        return self.get_response(request)

class APIMetricsMiddleware:
    """Middleware to automatically track API metrics for all requests."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Determine if this is an API request worth tracking
        should_track = (
            request.path.startswith('/api/') or  # Standard API endpoints
            request.path.startswith('/predict/') or  # Prediction endpoints
            request.path.startswith('/analytics/') or  # Analytics endpoints
            request.path.startswith('/finance/') or  # Finance endpoints
            request.path.startswith('/model-management/') or  # Model management
            request.path.startswith('/user-management/')  # User management
        )
        
        # Skip static files, admin pages, and other non-API resources
        skip_types = ['.css', '.js', '.ico', '.png', '.jpg', '.svg', 'favicon']
        if any(skip_type in request.path for skip_type in skip_types):
            should_track = False
            
        if should_track:
            # Record the start time
            start_time = time.time()
            
            # Process the request
            response = self.get_response(request)
            
            # Calculate response time in milliseconds
            response_time = (time.time() - start_time) * 1000
            
            # Record the metrics
            try:
                APIMetrics.objects.create(
                    endpoint=request.path,
                    response_time=response_time,
                    status_code=response.status_code,
                    error=response.status_code >= 400,
                    timestamp=timezone.now()
                )
                print(f"Recorded metrics for {request.path}: {response_time}ms, status {response.status_code}")
            except Exception as e:
                # Don't let metrics tracking failure affect the response
                print(f"Error recording API metrics: {str(e)}")
                
            return response
        else:
            # For non-API requests, just pass through
            return self.get_response(request)