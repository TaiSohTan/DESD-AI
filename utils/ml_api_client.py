import requests, json
from django.conf import settings

## Prediction Endpoint in the FastAPI Server 
def predict(data):
    """Send a prediction request to the FastAPI service"""
    url = f"http://host.docker.internal:8088/predict"
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
    url = f"http://host.docker.internal:8088/health"
    try:
        response = requests.get(url, timeout=5)  # Add timeout
        print(f"settings.FASTAPI_BASE_URL: {settings.FASTAPI_BASE_URL}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"settings.FASTAPI_BASE_URL: {settings.FASTAPI_BASE_URL}")
        print(f"ML API health check failed: {str(e)}")
        return False