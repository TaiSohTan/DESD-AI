import pandas as pd
import numpy as np
import os
import json
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Union, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sklearn.neighbors import NearestNeighbors
import time
from datetime import datetime
import threading

## XAI Service
import fix_warnings  # Fix warning issues for SHAP
from xai_service import ShapExplainer

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
                
            # Force a reload if size or mtime changed
            if current_size != self.last_file_size or current_mtime != self.last_modified_time:
                with self.model_lock:
                    print(f"Loading model from {self.active_model_path} (modified at {datetime.fromtimestamp(current_mtime)})")
                    self.active_model = joblib.load(self.active_model_path)
                    self.last_modified_time = current_mtime
                    self.last_file_size = current_size
                
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
        
        return self.model
    
    def requires_input_scaling(self):
        """Check if the current model requires input scaling"""
        return self.requires_scaling

# Initialize model manager
model_manager = ModelManager()

# Load the serialized preprocessors
numerical_imputer = joblib.load('preprocessor/numerical_imputer.pkl')
categorical_imputer = joblib.load('preprocessor/categorical_imputer.pkl')
onehot_encoder = joblib.load('preprocessor/onehot_encoder.pkl')
label_encoder = joblib.load('preprocessor/label_encoder.pkl')
target_encoder = joblib.load('preprocessor/target_encoder.pkl')
standard_scaler = joblib.load('preprocessor/standard_scaler.pkl')
metadata = joblib.load('preprocessor/preprocessing_metadata.pkl')

# Load training data reference for distance-based confidence calculation
X_train_reference = joblib.load('training_data/X_train.pkl')
print(f"Training reference data loaded successfully: {len(X_train_reference)} samples")

# Define request model with proper validation
class PredictionRequest(BaseModel):
    General_Rest: float = Field(..., description="General rest value")
    General_Fixed: float = Field(..., description="General fixed value")
    Special_Earnings_Loss: float = Field(..., description="Special earnings loss value")
    Injury_Prognosis: float = Field(..., description="Injury prognosis in months")
    Special_Therapy: float = Field(..., description="Special therapy value")
    Special_Asset_Damage: float = Field(..., description="Special asset damage value")
    Special_Fixes: float = Field(..., description="Special fixes value")
    Special_Usage_Loss: float = Field(..., description="Special usage loss value")
    Accident_Type: str = Field(..., description="Type of accident")
    Special_Journey_Expenses: float = Field(..., description="Special journey expenses")
    Days_Between_Accident_And_Claim: float = Field(..., description="Days between accident and claim")
    Vehicle_Age: float = Field(..., description="Vehicle age in years")
    Driver_Age: float = Field(..., description="Driver age in years")
    Special_Loaner_Vehicle: float = Field(..., description="Special loaner vehicle value")
    Special_Overage: float = Field(..., description="Special overage value")
    General_Uplift: float = Field(..., description="General uplift value")
    Accident_Description: str = Field(..., description="Description of accident")
    Exceptional_Circumstances: bool = Field(..., description="Whether there were exceptional circumstances")
    Minor_Psychological_Injury: bool = Field(..., description="Whether there was minor psychological injury")
    Injury_Description: str = Field(..., description="Description of injury")
    Special_Health_Expenses: float = Field(..., description="Health-related expenses")
    Special_Additional_Injury: float = Field(..., description="Additional injury compensation")
    Special_Medications: float = Field(..., description="Medication expenses")
    Special_Rehabilitation: float = Field(..., description="Rehabilitation costs")
    Special_Trip_Costs: float = Field(..., description="Trip costs")
    Number_Of_Passengers: float = Field(..., description="Number of passengers in vehicle")
    Whiplash: bool = Field(..., description="Whether whiplash occurred")
    Police_Report_Filed: bool = Field(..., description="Whether police report was filed")
    Witness_Present: bool = Field(..., description="Whether witnesses were present")
    Gender: str = Field(..., description="Gender of claimant")
    Vehicle_Type: str = Field(..., description="Type of vehicle")
    Weather_Conditions: str = Field(..., description="Weather conditions")
    Dominant_Injury: str = Field(..., description="Dominant injury area")

class PredictionResponse(BaseModel):
    settlement_value: float = Field(..., description="Predicted settlement value")
    message: str = Field(..., description="Formatted prediction message")
    confidence: str = Field(..., description="Confidence level of the prediction")
    model_info: Dict[str, Any] = Field(..., description="Information about the model used")
    explanation: Dict[str, Any] = Field(..., description="SHAP explanation for the prediction")

"""   
# Impute missing values function
def feature_imputer(data_dict):
    #Impute missing values in the data using loaded imputers
    # More robust check for missing values
    def is_missing(value):
        return (value is None or 
                pd.isna(value) or 
                value == "" or 
                value == "NONE" or
                (isinstance(value, str) and value.strip() == ""))
    
    missing_fields = {k: v for k, v in data_dict.items() if is_missing(v)}
    
    if not missing_fields:
        print("No missing values detected, skipping imputation")
        return data_dict
    
    print(f"Found {len(missing_fields)} missing fields: {list(missing_fields.keys())}")
    
    try:
        # Separate numerical and categorical features
        numerical_features = []
        categorical_features = []
        
        # Identify feature types based on metadata or infer from data type
        for col in data_dict.keys():
            # Skip features that aren't missing
            if data_dict[col] is not None and not pd.isna(data_dict[col]):
                continue
                
            # Classify feature as numerical or categorical
            if isinstance(data_dict[col], (int, float)) or col in metadata.get('numerical_columns', []):
                numerical_features.append(col)
            else:
                categorical_features.append(col)
        
        # Create dataframes for imputation
        if numerical_features:
            num_df = pd.DataFrame({col: [data_dict.get(col)] for col in numerical_features})
            # Apply numerical imputation
            imputed_num = numerical_imputer.transform(num_df)
            # Update data_dict with imputed values
            for i, col in enumerate(numerical_features):
                data_dict[col] = imputed_num[0, i]
            print(f"Imputed {len(numerical_features)} numerical features")
            
        if categorical_features:
            cat_df = pd.DataFrame({col: [data_dict.get(col)] for col in categorical_features})
            # Apply categorical imputation
            imputed_cat = categorical_imputer.transform(cat_df)
            # Update data_dict with imputed values
            for i, col in enumerate(categorical_features):
                data_dict[col] = imputed_cat[0, i]
            print(f"Imputed {len(categorical_features)} categorical features")
                
    except Exception as e:
        print(f"Warning: Imputation error: {str(e)}")
        print("Continuing with original data")
    
    return data_dict

"""

# Preprocessing Function
def preprocess_input(input_data):

    # Convert to dictionary
    data_dict = input_data.copy()
    
    # Apply target encoding from saved encoders
    target_encoder = {
        'Accident_Type': {
            'Other': 1354.6189,
            'Other side changed lanes and collided with clt\'s vehicle': 1349.6307,
            'Other side changed lanes on a roundabout colliding with clt\'s vehicle': 1256.6905,
            'Other side collided with Clt\'s parked vehicle': 937.6631,
            'Other side drove on wrong side of the road': 1461.9966,
            'Other side opened their door, hitting clt\'s vehicle': 1195.0091,
            'Other side overtook and hit Clt when pulling in': 1245.4420,
            'Other side overtook and pulled in too soon': 1212.0400,
            'Other side pulled from parked position into the path of clt\'s vehicle': 1241.0428,
            'Other side pulled on to roundabout': 1374.8878,
            'Other side pulled out of side road': 1396.4024,
            'Other side reversed into Clt\'s vehicle': 1041.0907,
            'Other side reversed into clt\'s stationary vehicle': 855.6197,
            'Other side turned across Clt\'s path': 1391.3469,
            'Rear end': 1134.4706,
            'Rear end - 3 car - Clt at front': 1089.9695,
            'Rear end - Clt pushed into next vehicle': 1352.1676
        },
        'Accident_Description': {
            'Hit a deer on the highway.': 1214.8173,
            'Lost control on a snowy road.': 1208.4735,
            'Rear-ended at a stoplight.': 1193.9175,
            'Side collision at an intersection.': 1243.8671,
            'Swerved to avoid another vehicle.': 1223.9544
        },
        'Injury_Description': {
            'Concussion and bruised ribs.': 1171.8660,
            'Fractured arm and leg.': 1229.4915,
            'Minor cuts and scrapes.': 1254.8799,
            'Sprained ankle and wrist.': 1261.8119,
            'Whiplash and minor bruises.': 1164.7442
        },
        'Dominant_Injury': {
            'Arms': 1221.5548,
            'Hips': 1232.9304,
            'Legs': 1223.1914,
            'Multiple': 1188.2923
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


# Feature Scaling Function
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

# Confindence Score Function
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
    raw_confidence = 100 * np.exp(-0.5 * (avg_distance) / distance_scale)
    
    # Clip confidence to 0-100 range
    confidence = max(0, min(100, raw_confidence))
    
    # Add bonus for close neighbors
    close_neighbors = np.sum(distances[0] < distance_scale)
    proximity_bonus = min(5, close_neighbors / 2)
    
    # Final confidence
    final_confidence = min(100, confidence + proximity_bonus)
    
    return f"{final_confidence:.1f}"

def calculate_model_specific_confidence(model, model_input):
    """Calculate confidence based on the specific type of model with penalty for aggressive predictions"""
    model_type = type(model).__name__
    
    if hasattr(model, 'estimators_'):
        # Check if estimators are actual model objects
        if hasattr(model.estimators_[0], 'predict'):
            # Original code for ensemble models
            predictions = []
            for estimator in model.estimators_:
                pred = estimator.predict(model_input)[0]
                predictions.append(pred)
                
            # Calculate statistical dispersion metrics
            mean_pred = np.mean(predictions)
            std_dev = np.std(predictions)
            
            # Normalize by the prediction magnitude
            coefficient_of_variation = std_dev / max(abs(mean_pred), 1.0)
            
            # MODIFICATION 1: Add penalty for predictions above reasonable threshold
            # Assuming avg settlement in training data is around 1200 based on your target encodings
            avg_settlement = 1200
            high_settlement_threshold = 2 * avg_settlement  # 2400 pounds
            
            magnitude_penalty = 0
            if mean_pred > high_settlement_threshold:
                # Proportional penalty: 5% reduction per 1000 pounds above threshold
                magnitude_penalty = 5 * (mean_pred - high_settlement_threshold) / 1000
                print(f"Applied magnitude penalty of {magnitude_penalty:.1f}% for high prediction (£{mean_pred:.2f})")
            
            # MODIFICATION 2: Increase coefficient in exponential to be more sensitive to variation
            sensitivity = 4.0  # Increased from 3.0 to be more sensitive to variation
            
            # Calculate base confidence (without magnitude penalty)
            base_confidence = 100 * np.exp(-sensitivity * coefficient_of_variation)
            
            # Apply magnitude penalty
            ensemble_confidence = base_confidence * (1 - (magnitude_penalty / 100))
            
            # Also calculate KNN-based confidence
            knn_confidence = float(calculate_confidence_percentage(model_input, "active"))
            
            # Compare both methods and use the higher confidence
            if ensemble_confidence > knn_confidence:
                print(f"Using ensemble confidence: {ensemble_confidence:.1f}% (KNN: {knn_confidence:.1f}%)")
                confidence = ensemble_confidence
            else:
                print(f"Using KNN confidence: {knn_confidence:.1f}% (Ensemble: {ensemble_confidence:.1f}%)")
                confidence = knn_confidence
            
            print(f"Final confidence for {model_type}: {confidence:.1f}% (CV: {coefficient_of_variation:.3f})")
            return f"{min(100, max(0, confidence)):.1f}"
        else:
            # Fall back to KNN approach for models with non-model estimators
            print(f"Model {model_type} has estimators but they're not predictors. Using KNN confidence.")
            return calculate_confidence_percentage(model_input, "active")
    else:
        # For non-ensemble models, just use the KNN approach
        print(f"Model {model_type} is not an ensemble. Using KNN confidence.")
        return calculate_confidence_percentage(model_input, "active")

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

            explainer = ShapExplainer(
                model=model,
                feature_names=model.feature_names_in_ 
            )
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Model not available: {str(e)}")

        # Convert request to dictionary
        input_data = request.dict()
        
        # Print original input data
        print("\n===== ORIGINAL INPUT DATA =====")
        print(json.dumps(input_data, indent=2, default=str))

        #imputed_data = feature_imputer(input_data)

        # Preprocess the input data using the saved preprocessors
        preprocessed_data = preprocess_input(input_data)

        # Print preprocessed data
        print("\n===== PREPROCESSED DATA =====")
        print(json.dumps(preprocessed_data, indent=2, default=str))

        scaled_preprocessed_data = scale_features(preprocessed_data)

        if model_manager.requires_input_scaling():
            print("\n===== DATA AFTER SCALING =====")
            print(json.dumps(scaled_preprocessed_data, indent=2, default=str))
        else:
            print("\n===== NO SCALING REQUIRED FOR THIS MODEL =====")

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
        confidence_score = calculate_model_specific_confidence(model,model_input)
        
        # Print prediction results as debug message
        print("\n===== PREDICTION RESULTS =====")
        print(f"Predicted settlement value: £ {float(prediction):,.2f} (Confidence: {confidence_score}%)")

        ##### XAI SHAP EXPLANATION #####
        # Generate explanation 
        explanation = None
        try:
            explanation = explainer.generate_explanation(model_input)
        except Exception as e:
            print(f"Error generating explanation: {str(e)}") # Don't fail the whole request if explanation fails
            # Use a default empty explanation structure or None
            explanation = {
                "feature_importance_plot": "",
                "waterfall_plot": "",
                "top_features": [],
                "base_value": 0.0,
                "shap_values": []
            }
                    
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
            model_info=model_info,
            explanation=explanation
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
        reference_data_path = "training_data/X_train.pkl"
        
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