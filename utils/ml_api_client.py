import requests, json
from django.conf import settings

## Prediction Endpoint in the FastAPI Server 
def predict(data):
    """Send a prediction request to the FastAPI service"""
    url = f"{settings.FASTAPI_BASE_URL}/predict"
    try:
        response = requests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=10  # Add timeout for safety
        )
        response.raise_for_status()
        
        # Print the response for debugging
        print("FastAPI response:", response.json())
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling ML API: {str(e)}")
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