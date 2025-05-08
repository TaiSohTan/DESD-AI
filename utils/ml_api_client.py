import requests, json
import time
from django.conf import settings
from django.utils import timezone

# Import APIMetrics if available (in Django context), otherwise provide a no-op implementation
try:
    from api.models import APIMetrics
    has_api_metrics = True
except ImportError:
    has_api_metrics = False
    print("APIMetrics model not available in this context")

class MLApiClient:
    """Client class for interacting with the ML API service"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or settings.FASTAPI_BASE_URL
    
    def _log_api_metrics(self, endpoint, start_time, status_code, error=False):
        """Log API metrics if we're running in Django context"""
        if not has_api_metrics:
            return
            
        try:
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            APIMetrics.objects.create(
                endpoint=endpoint,
                response_time=response_time,
                status_code=status_code,
                error=error,
                timestamp=timezone.now()
            )
        except Exception as e:
            # Don't let metrics tracking failure affect the response
            print(f"Error recording API metrics: {str(e)}")
    
    def predict(self, data, request=None):
        """Send a prediction request to the FastAPI service"""
        url = f"{self.base_url}/predict"
        endpoint = "/api/predict"  # Log endpoint from client's perspective
        start_time = time.time()

        ## Initialize the Content Type 
        headers = {"Content-Type": "application/json"}

        ## Add authentication token if request is provided 
        if request and request.COOKIES.get("access_token"):
            headers['Authorization'] = f"Bearer {request.COOKIES.get('access_token')}"
        try:
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=10  # Add timeout for safety
            )
            response.raise_for_status()
            
            # Get response data
            response_data = response.json()
            
            # Log metrics for successful request
            self._log_api_metrics(endpoint, start_time, response.status_code)
            
            # Print the response for debugging
            print("FastAPI response:", response_data)

            # Parse the confidence value as float (removing % if present)
            if 'confidence' in response_data:
                confidence_str = response_data['confidence']
                if isinstance(confidence_str, str):
                    confidence_str = confidence_str.strip('%')
                response_data['confidence'] = float(confidence_str)

            # Make sure explanation data is properly formatted if it exists
            if 'explanation' in response_data and response_data['explanation']:
                # The explanation data is already parsed JSON from the FastAPI response
                print("Explanation data received")
            
            return response_data
        except requests.exceptions.RequestException as e:
            # Log metrics for failed request
            status_code = e.response.status_code if hasattr(e, 'response') else 500
            self._log_api_metrics(endpoint, start_time, status_code, error=True)
            
            print(f"Error calling ML API: {str(e)}")
            if hasattr(e, 'response') and e.response.status_code == 401:
                raise Exception("Authentication to ML Service has Failed Please Login again")
            raise Exception(f"Failed to communicate with ML service: {str(e)}")

    def health(self):
        """Health check endpoint in the FastAPI Server"""
        url = f"{self.base_url}/health"
        endpoint = "/api/health"  # Log endpoint from client's perspective
        start_time = time.time()
        
        try:
            response = requests.get(url, timeout=5)  # Add timeout
            
            # Log metrics
            self._log_api_metrics(endpoint, start_time, response.status_code)
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            # Log metrics for failed request
            self._log_api_metrics(endpoint, start_time, 500, error=True)
            
            print(f"ML API health check failed: {str(e)}")
            return False

    def reload_models(self, request=None):
        """Tell the FastAPI service to reload the active model"""
        url = f"{self.base_url}/reload-models"
        endpoint = "/api/reload-models"  # Log endpoint from client's perspective
        start_time = time.time()
        
        headers = {"Content-Type": "application/json"}
        
        if request and request.COOKIES.get("access_token"):
            headers['Authorization'] = f"Bearer {request.COOKIES.get('access_token')}"
        
        try:
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Log metrics for successful request
            self._log_api_metrics(endpoint, start_time, response.status_code)
            
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log metrics for failed request
            status_code = e.response.status_code if hasattr(e, 'response') else 500
            self._log_api_metrics(endpoint, start_time, status_code, error=True)
            
            print(f"Error reloading FastAPI models: {str(e)}")
            return {"success": False, "error": str(e)}

# For backward compatibility, keeping the standalone functions
def predict(data, request = None):
    """Legacy function that uses the MLApiClient class"""
    client = MLApiClient()
    return client.predict(data, request)

def health():
    """Legacy function that uses the MLApiClient class"""
    client = MLApiClient()
    return client.health()

def reload_models(request=None):
    """Legacy function that uses the MLApiClient class"""
    client = MLApiClient()
    return client.reload_models(request)