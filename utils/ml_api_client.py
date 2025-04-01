import requests, json
from django.conf import settings

## Prediction Endpoint in the FastAPI Server 
def predict(data, request = None):
    """Send a prediction request to the FastAPI service"""
    url = f"{settings.FASTAPI_BASE_URL}/predict"

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
        
        # Print the response for debugging
        print("FastAPI response:", response.json())
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling ML API: {str(e)}")
        if response.status_code == 401:
            raise Exception("Authentication to ML Service has Failed Please Login again")
        raise Exception(f"Failed to communicate with ML service: {str(e)}")

def health():
    """Health check endpoint in the FastAPI Server"""
    url = f"{settings.FASTAPI_BASE_URL}/health"
    try:
        response = requests.get(url, timeout=5)  # Add timeout
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"ML API health check failed: {str(e)}")
        return False