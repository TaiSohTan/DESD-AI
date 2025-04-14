import pandas as pd
import numpy as np
import os
import json
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Union, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sklearn.neighbors import NearestNeighbors
import time
from datetime import datetime
import threading

## Authentication Utility
from auth import get_current_user

# Create FastAPI app
app = FastAPI(
    title="Settlement Value Prediction API",
    description="API for predicting settlement values based on claim details",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

## Add CORS Middleware to allow responses from Django
app.add_middleware(
    CORSMiddleware,
    ## Allow communication with the Django App 
    allow_origins=["http://127.0.0.1:8000"], 
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model management
class ModelManager:
    def __init__(self):
        self.active_model = None
        self.active_model_path = "active_model.pkl"
        self.active_model_metadata_path = "active_model_metadata.json"
        self.last_modified_time = 0
        self.last_file_size = 0
        self.requires_scaling = False  # Default to not scaling
        self.model_lock = threading.RLock()  # Reentrant lock for thread safety
        self.load_model()  # Initial load
    
    def load_model(self):
        """Load the active model if it exists and has been updated"""
        try:
            if not os.path.exists(self.active_model_path):
                print(f"Warning: {self.active_model_path} not found")
                return False
                
            # Check if file has been modified
            current_size = os.path.getsize(self.active_model_path)
            current_mtime = os.path.getmtime(self.active_model_path)
            
            if current_size == self.last_file_size and current_mtime <= self.last_modified_time:
                return True
                
            # File has changed, load the new model
            with self.model_lock:
                print(f"Loading model from {self.active_model_path} (modified at {datetime.fromtimestamp(current_mtime)})")
                self.active_model = joblib.load(self.active_model_path)
                self.last_modified_time = current_mtime
                
                # Load model metadata if available
                if os.path.exists(self.active_model_metadata_path):
                    try:
                        with open(self.active_model_metadata_path, 'r') as f:
                            metadata = json.load(f)
                            self.requires_scaling = metadata.get('requires_scaling', False)
                            print(f"Model requires scaling: {self.requires_scaling}")
                    except Exception as e:
                        print(f"Error loading model metadata: {str(e)}")
                        self.requires_scaling = False
                else:
                    print("No model metadata found, assuming scaling not required")
                    self.requires_scaling = False
                    
                print("Active model loaded successfully")
                return True
                
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return False
    
    def get_model(self):
        """Get the current active model, checking for updates first"""
        # Check if model has been updated
        self.load_model()  
        
        with self.model_lock:
            if self.active_model is None:
                raise ValueError("No active model available")
            return self.active_model
    
    def requires_input_scaling(self):
        """Check if the current model requires input scaling"""
        return self.requires_scaling

# Initialize model manager
model_manager = ModelManager()

# Load the serialized preprocessors
standard_scaler = joblib.load('standard_scaler.pkl')
target_encoder = joblib.load('target_encoder.pkl')
onehot_encoder = joblib.load('onehot_encoder.pkl')
label_encoder = joblib.load('label_encoder.pkl')
metadata = joblib.load('preprocessing_metadata.pkl')

# Load training data reference for distance-based confidence calculation
X_train_reference = joblib.load('X_train.pkl')
print(f"Training reference data loaded successfully: {len(X_train_reference)} samples")

# Define request model with proper validation
class PredictionRequest(BaseModel):
    GeneralRest: float = Field(..., description="General rest value")
    GeneralFixed: float = Field(..., description="General fixed value")
    SpecialEarningsLoss: float = Field(..., description="Special earnings loss value")
    Injury_Prognosis: float = Field(..., description="Injury prognosis in months")
    SpecialTherapy: float = Field(..., description="Special therapy value")
    SpecialAssetDamage: float = Field(..., description="Special asset damage value")
    SpecialFixes: float = Field(..., description="Special fixes value")
    SpecialUsageLoss: float = Field(..., description="Special usage loss value")
    AccidentType: str = Field(..., description="Type of accident")
    SpecialJourneyExpenses: float = Field(..., description="Special journey expenses")
    Days_Between_Accident_And_Claim: float = Field(..., description="Days between accident and claim")
    Vehicle_Age: float = Field(..., description="Vehicle age in years")
    Driver_Age: float = Field(..., description="Driver age in years")
    SpecialLoanerVehicle: float = Field(..., description="Special loaner vehicle value")
    SpecialOverage: float = Field(..., description="Special overage value")
    GeneralUplift: float = Field(..., description="General uplift value")
    Accident_Description: str = Field(..., description="Description of accident")
    Exceptional_Circumstances: bool = Field(..., description="Whether there were exceptional circumstances")
    Minor_Psychological_Injury: bool = Field(..., description="Whether there was minor psychological injury")
    Injury_Description: str = Field(..., description="Description of injury")
    SpecialHealthExpenses: float = Field(..., description="Health-related expenses")
    SpecialAdditionalInjury: float = Field(..., description="Additional injury compensation")
    SpecialMedications: float = Field(..., description="Medication expenses")
    SpecialRehabilitation: float = Field(..., description="Rehabilitation costs")
    SpecialTripCosts: float = Field(..., description="Trip costs")
    Number_of_Passengers: float = Field(..., description="Number of passengers in vehicle")
    Whiplash: bool = Field(..., description="Whether whiplash occurred")
    Police_Report_Filed: bool = Field(..., description="Whether police report was filed")
    Witness_Present: bool = Field(..., description="Whether witnesses were present")
    Gender: str = Field(..., description="Gender of claimant")
    Vehicle_Type: str = Field(..., description="Type of vehicle")
    Weather_Conditions: str = Field(..., description="Weather conditions")
    Dominant_injury: str = Field(..., description="Dominant injury area")

class PredictionResponse(BaseModel):
    settlement_value: float = Field(..., description="Predicted settlement value")
    message: str = Field(..., description="Formatted prediction message")
    confidence: str = Field(..., description="Confidence level of the prediction")
    model_info: Dict[str, Any] = Field(..., description="Information about the model used")
    
# Preprocessing Function
def preprocess_input(input_data):

    # Convert to dictionary
    data_dict = input_data.copy()

    # Create mapping between underscored and spaced field names
    field_mapping = {
        'Accident_Description': 'Accident Description',
        'Injury_Description': 'Injury Description',
        'Dominant_injury': 'Dominant injury',
        'Vehicle_Age': 'Vehicle Age',
        'Driver_Age': 'Driver Age',
        'Number_of_Passengers': 'Number of Passengers',
        'Police_Report_Filed': 'Police Report Filed',
        'Witness_Present': 'Witness Present',
        'Vehicle_Type': 'Vehicle Type',
        'Weather_Conditions': 'Weather Conditions'
    }
    
    # Apply the mapping to create correctly named fields
    for api_field, model_field in field_mapping.items():
        if api_field in data_dict:
            data_dict[model_field] = data_dict[api_field]
            del data_dict[api_field]  # Remove the original field
            print(f"Mapped {api_field} -> {model_field}")
        else:
            print(f"Warning: Missing field: {api_field}")
    
    # Apply target encoding from saved encoders
    target_encoder = {
        'AccidentType': {
            'Other': 805.5464516129032,
            'Other side changed lanes and collided with clt\'s vehicle': 864.7134210526316,
            'Other side changed lanes on a roundabout colliding with clt\'s vehicle': 1075.8030263157896,
            'Other side collided with Clt\'s parked vehicle': 1085.85,
            'Other side drove on wrong side of the road': 1110.7357142857143,
            'Other side opened their door, hitting clt\'s vehicle': 1120.5214141414142,
            'Other side overtook and hit Clt when pulling in': 1130.2614012982053,
            'Other side overtook and pulled in too soon': 1174.067906976744,
            'Other side overtook whilst clt was turning right': 1253.6731707317074,
            'Other side pulled from parked position into the path of clt\'s vehicle': 1268.54,
            'Other side pulled on to roundabout': 1343.5631891891892,
            'Other side pulled out of side road': 1346.378130563798,
            'Other side reversed into Clt\'s vehicle': 1369.659,
            'Other side reversed into clt\'s stationary vehicle': 1373.4739097744362,
            'Other side turned across Clt\'s path': 1388.966582278481,
            'Rear end': 1426.4042424242425,
            'Rear end - 3 car - Clt at front': 1457.1582653061225,
            'Rear end - Clt pushed into next vehicle': 1567.01
        },
        'Accident Description': {
            'Hit a deer on the highway.': 1206.1765262076053,
            'Lost control on a snowy road.': 1214.5150043668123,
            'Rear-ended at a stoplight.': 1216.653168859649,
            'Side collision at an intersection.': 1218.5378302900108,
            'Swerved to avoid another vehicle.': 1235.4431296891746
        },
        'Injury Description': {
            'Concussion and bruised ribs.': 1172.1275582685903,
            'Fractured arm and leg.': 1193.0538951695785,
            'Minor cuts and scrapes.': 1226.5536103896104,
            'Sprained ankle and wrist.': 1244.8258804695838,
            'Whiplash and minor bruises.': 1251.0179418103448
        },
        'Dominant injury': {
            'Arms': 1192.95743993372,
            'Hips': 1218.5957589285713,
            'Legs': 1228.2536333052985,
            'Multiple': 1232.9795407279028
        }
    }
    # Apply target encoding using hardcoded values
    for col in metadata['target_encoding_columns']:
        if col in target_encoder:
            encoder = target_encoder[col]
            # Calculate default for unseen categories
            default = sum(encoder.values()) / len(encoder) if encoder else 0
            # Apply encoding, using default if category not found
            if col in data_dict and data_dict[col] in encoder:
                data_dict[col] = encoder[data_dict[col]]
            else:
                print(f"Warning: Using default encoding for {col}={data_dict.get(col, 'MISSING')}")
                data_dict[col] = default
        else:
            print(f"Warning: No hardcoded encoder for {col}, using original")
            # Fall back to original encoder if available
            if target_encoder and col in target_encoder:
                encoder = target_encoder[col]
                default = sum(encoder.values()) / len(encoder)
                data_dict[col] = encoder.get(data_dict[col], default)

    """
    for col in metadata['target_encoding_columns']:
        encoder = target_encoder[col]
        # Use default value if category not seen during training
        default = sum(encoder.values()) / len(encoder)
        data_dict[col] = encoder.get(data_dict[col], default)
    """
    
    # Apply one-hot encoding from saved encoder
    if metadata['onehot_encoding_columns']:
        # Create DataFrame with just the columns needed for one-hot encoding
        onehot_df = pd.DataFrame({col: [data_dict[col]] for col in metadata['onehot_encoding_columns']})
        # Transform using the loaded encoder
        encoded_array = onehot_encoder.transform(onehot_df)
        # Get feature names
        feature_names = onehot_encoder.get_feature_names_out(metadata['onehot_encoding_columns'])
        # Add encoded features to data_dict
        for i, feature in enumerate(feature_names):
            data_dict[feature] = encoded_array[0, i]
        # Remove original categorical columns
        for col in metadata['onehot_encoding_columns']:
            del data_dict[col]
    
    # Convert boolean features to integers
    for col in metadata['label_encoding_columns']:
        data_dict[col] = int(data_dict[col])
    
    return data_dict

def scale_features(data_dict):
    """Apply standard scaling to all features if required by the model"""
    # Only apply scaling if the model requires it
    if model_manager.requires_input_scaling():
        print("Applying standard scaling to all features")
        
        try:
            # Create DataFrame with columns in the exact order expected by scaler
            expected_features = standard_scaler.feature_names_in_
            scaler_df = pd.DataFrame(columns=expected_features)
            
            # Fill in values from data_dict where feature names match
            for feature in expected_features:
                if feature in data_dict:
                    scaler_df[feature] = [data_dict[feature]]
                else:
                    print(f"Warning: Missing feature for scaler: {feature}")
                    scaler_df[feature] = [0]  # Default value for missing features
            
            # Now apply scaling with columns in the correct order
            scaled_array = standard_scaler.transform(scaler_df)
            
            # Convert back to dict and update original data
            scaled_df = pd.DataFrame(scaled_array, columns=expected_features)
            scaled_dict = scaled_df.iloc[0].to_dict()
            data_dict.update(scaled_dict)
            
            print(f"Successfully scaled {len(expected_features)} features")
        except Exception as e:
            print(f"Warning: Scaling error: {str(e)}")
            print("Continuing with unscaled data")
    else:
        print("Scaling not applied -- not required by model")
        
    return data_dict


def calculate_confidence_percentage(model_input, model_type, n_neighbors=10):

    # Initialize and fit nearest neighbors model
    nn_model = NearestNeighbors(n_neighbors=min(n_neighbors, len(X_train_reference)))
    nn_model.fit(X_train_reference)
    
    # Get distances to nearest neighbors for the single input sample
    distances, _ = nn_model.kneighbors(model_input)
    
    # Get average distance for this sample
    avg_distance = np.mean(distances[0])  # [0] because we have one sample
    
    # Use a simple scaling approach
    median_dist = np.median(distances[0])
    distance_scale = max(median_dist, 0.1)  # Avoid division by zero
    
    # Calculate confidence (higher distance = lower confidence)
    raw_confidence = 100 * np.exp(-avg_distance / distance_scale)
    
    # Clip confidence to 0-100 range
    confidence = max(0, min(100, raw_confidence))
    
    # Add bonus for close neighbors
    close_neighbors = np.sum(distances[0] < distance_scale)
    proximity_bonus = min(5, close_neighbors / 2)
    
    # Final confidence
    final_confidence = min(100, confidence + proximity_bonus)
    
    return f"{final_confidence:.1f}"

@app.get("/health")
async def health_check():
    """Health check endpoint for the API."""
    try:
        # Check if model is available
        model_manager.get_model()
        last_updated = datetime.fromtimestamp(model_manager.last_modified_time).isoformat()
        return {
            "status": "healthy", 
            "model": "active_model.pkl",
            "last_updated": last_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")

# Endpoint for predictions
@app.post("/predict", response_model=PredictionResponse)
async def predict_settlement(
    request: PredictionRequest,
    model_type: str = "active",
    current_user: dict = Depends(get_current_user)  # Add User Dependency
):
    try:
        user_id = current_user.get("user_id")
        
        # Get active model through the model manager
        try:
            model = model_manager.get_model()
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Model not available: {str(e)}")

        # Convert request to dictionary
        input_data = request.dict()
        
        # Print original input data
        print("\n===== ORIGINAL INPUT DATA =====")
        print(json.dumps(input_data, indent=2, default=str))

        # Preprocess the input data using the saved preprocessors
        preprocessed_data = preprocess_input(input_data)

        # Print preprocessed data
        print("\n===== PREPROCESSED DATA =====")
        print(json.dumps(preprocessed_data, indent=2, default=str))

        scaled_preprocessed_data = scale_features(preprocessed_data)

        print("\n===== DATA AFTER SCALING =====")
        print(json.dumps(scaled_preprocessed_data, indent=2, default=str))

        # Create model input directly from scaled data
        expected_features = model.feature_names_in_
        model_input = pd.DataFrame(columns=expected_features)

        # Fill model input from scaled data
        for col in expected_features:
            if col in scaled_preprocessed_data:
                model_input[col] = [scaled_preprocessed_data[col]]
            else:
                print(f"Warning: Missing feature for model: {col}")
                model_input[col] = [0]  # Default value for missing features

        # Log any missing or extra features for debugging
        missing_features = set(expected_features) - set(scaled_preprocessed_data.keys())
        extra_features = set(scaled_preprocessed_data.keys()) - set(expected_features)
        if missing_features:
            print(f"Warning: Features missing for model: {missing_features}")
        if extra_features:
            print(f"Warning: Extra features not used by model: {extra_features}")
        
        # Make prediction
        prediction = model.predict(model_input)[0]

        # Calculate confidence score using distance-based method
        confidence_score = calculate_confidence_percentage(model_input, model_type)

        # Get model info for response
        model_info = {
            "type": getattr(model, "_estimator_type", "unknown"),
            "last_updated": datetime.fromtimestamp(model_manager.last_modified_time).isoformat(),
            "features_count": len(expected_features)
        }

        # Return the prediction
        rounded_settlement_value = round(float(prediction), 2)
        return PredictionResponse(
            settlement_value = rounded_settlement_value,
            message=f"£ {rounded_settlement_value:,.2f}",
            confidence=confidence_score,
            model_info=model_info
        )   
    
    except Exception as e:
        # Log the error
        print(f"Error making prediction: {str(e)}")
        import traceback
        traceback.print_exc()  # This will give more detailed error information
        raise HTTPException(status_code=500, detail=f"Prediction ERROR: {str(e)}")
    
@app.post("/reload-models")
async def reload_models(current_user: dict = Depends(get_current_user)):
    """Force reload the active model"""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["Admin", "AI Engineer"]:
            raise HTTPException(
                status_code=403, detail="Only admins and AI engineers can reload models"
            )
            
        # Force model manager to reload the model
        model_manager.last_modified_time = 0  # Reset last modified time
        success = model_manager.load_model()
        
        if success:
            model_info = {
                "type": getattr(model_manager.active_model, "_estimator_type", "unknown"),
                "last_updated": datetime.fromtimestamp(model_manager.last_modified_time).isoformat()
            }
            return {
                "success": True, 
                "message": "Model reloaded successfully", 
                "model_info": model_info
            }
        else:
            return {
                "success": False, 
                "error": "Failed to reload model"
            }
    except Exception as e:
        print(f"Error reloading models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reloading models: {str(e)}")

@app.post("/update-reference-data")
async def update_reference_data(current_user: dict = Depends(get_current_user)):
    """
    Update the training data reference used for distance-based confidence calculation.
    This should be called after model retraining.
    """
    try:
        # Check admin permissions
        if current_user.get("role") not in ["Admin", "AI Engineer"]:
            raise HTTPException(
                status_code=403, detail="Only admins and AI engineers can update reference data"
            )
            
        # Path to the new reference data
        reference_data_path = "X_train.pkl"
        
        if os.path.exists(reference_data_path):
            try:
                global X_train_reference
                X_train_reference = joblib.load(reference_data_path)
                print(f"Training reference data updated successfully: {len(X_train_reference)} samples loaded")
                return {"success": True, "message": f"Reference data updated: {len(X_train_reference)} samples"}
            except Exception as e:
                print(f"Error updating reference data: {str(e)}")
                return {"success": False, "error": f"Error updating reference data: {str(e)}"}
        else:
            return {"success": False, "error": "Reference data file not found"}
    except Exception as e:
        print(f"Error in update-reference-data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=True, log_level="debug")

# docker-compose build ml_api
# docker-compose up -d ml_api