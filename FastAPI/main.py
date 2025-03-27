import pandas as pd
import numpy as np
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Union, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

# Create FastAPI app
app = FastAPI(
    title="Settlement Value Prediction API",
    description="API for predicting settlement values based on claim details",
    version="1.0.0"
)

# Load the serialized model
gbr_model = joblib.load('gbr.pkl')
xgb_model = joblib.load('xgb.pkl')
rf_model = joblib.load('rf.pkl')
# Load the serialized preprocessors
standard_scaler = joblib.load('standard_scaler.pkl')
target_encoder = joblib.load('target_encoder.pkl')
onehot_encoder = joblib.load('onehot_encoder.pkl')
metadata = joblib.load('preprocessing_metadata.pkl')

# Add a dictionary indicating which models require scaling
MODEL_REQUIRES_SCALING = {
    "gbr": False,  # GBR typically works well with unscaled data
    "xgb": True,   # XGBoost often benefits from scaled features
    "rf": False    # Random Forest typically works well with unscaled data
}

# Print the model features
#print("Expected Features in the Model:", gbr_model.feature_names_in_)

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
    
    # Apply target encoding from saved encoders
    for col in metadata['target_encoding_columns']:
        encoder = target_encoder[col]
        # Use default value if category not seen during training
        default = sum(encoder.values()) / len(encoder)
        data_dict[col] = encoder.get(data_dict[col], default)
    
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

def calculate_confidence_percentage(model_input, model_type):
    
    # Get predictions from all models for comparison
    predictions = {
        "gbr": float(gbr_model.predict(model_input)[0]),
        "rf": float(rf_model.predict(model_input)[0])
    }
    
    # For XGBoost, apply scaling if needed
    xgb_input = model_input.copy()
    if MODEL_REQUIRES_SCALING["xgb"] and standard_scaler:
        xgb_input = pd.DataFrame(
            standard_scaler.transform(xgb_input),
            columns=xgb_input.columns,
            index=xgb_input.index
        )
    predictions["xgb"] = float(xgb_model.predict(xgb_input)[0])
    
    # Calculate agreement between models (served as coefficient of variation)
    prediction_values = np.array(list(predictions.values()))
    mean_prediction = np.mean(prediction_values)
    std_prediction = np.std(prediction_values)
    
    # Calculate coefficient of variation (normalized standard deviation)
    cv = (std_prediction / mean_prediction) if mean_prediction > 0 else 0
    
    # Higher agreement (lower CV) = higher confidence
    # Convert to a 0-100 scale where 100 means perfect agreement
    base_confidence = max(0, min(100, 100 * (1 - min(cv, 1.0))))
    
    # Apply model-specific confidence adjustments
    model_confidence_factor = {
        "gbr": 1.0,    # GBR is our baseline model
        "xgb": 0.95,   # XGBoost gets slight penalty due to complexity
        "rf": 0.92     # Random Forest gets slightly higher penalty
    }
    
    # Apply model-specific adjustment
    adjusted_confidence = base_confidence * model_confidence_factor[model_type]
    
    # Return as percentage string
    return f"{adjusted_confidence:.1f}"

@app.get("/health")
async def health_check():
    """Health check endpoint for the API."""
    try:
        # Try to load one of the models to ensure everything is working
        gbr_model
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")

# Endpoint for predictions
@app.post("/predict", response_model=PredictionResponse)
async def predict_settlement(
    request: PredictionRequest,
    model_type: str = "gbr"  # Default to GBR, add query parameter for model selection
):
    try:
        # Validate model type
        if model_type not in ["gbr", "xgb", "rf"]:
            raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}. Must be one of: gbr, xgb, rf")
        
        # Select the right model based on model_type
        if model_type == "gbr":
            model = gbr_model
        elif model_type == "xgb":
            model = xgb_model
        elif model_type == "rf":
            model = rf_model

        # Convert request to dictionary
        input_data = request.dict()
        
        # Preprocess the input data using the saved preprocessors
        preprocessed_data = preprocess_input(input_data)

        # Convert to DataFrame with the correct column order
        input_df = pd.DataFrame([preprocessed_data])

        # Ensure columns match the model's expected features
        expected_features = model.feature_names_in_
        missing_features = set(expected_features) - set(input_df.columns)
        extra_features = set(input_df.columns) - set(expected_features)

        # Create DataFrame with correct columns
        model_input = pd.DataFrame(columns=expected_features)
        for col in expected_features:
            if col in input_df.columns:
                model_input[col] = input_df[col]
            else:
                model_input[col] = 0  # Default value for missing features
        
        # Apply scaling based on model requirements
        if MODEL_REQUIRES_SCALING[model_type] and standard_scaler:
            model_input = pd.DataFrame(
                standard_scaler.transform(model_input),
                columns=model_input.columns,
                index=model_input.index
            )
            print(f"SCALING : Model requires scaling; Applied scaling for {model_type} model")
        else:
            print(f"SCALING : Model doesn't require scaling; Skipped scaling for {model_type} model")

        # Make prediction
        prediction = model.predict(model_input)[0]

        # Calculate confidence score
        confidence_score = calculate_confidence_percentage(model_input, model_type)

        # Return the prediction
        rounded_settlement_value = round(float(prediction), 2)
        return PredictionResponse(settlement_value = rounded_settlement_value,
            message=f"£ {rounded_settlement_value:,.2f}",
            confidence=confidence_score
        )   
    
    except Exception as e:
        # Log the error
        print(f"Error making prediction: {str(e)}")
        import traceback
        traceback.print_exc()  # This will give more detailed error information
        raise HTTPException(status_code=500, detail=f"Prediction ERROR: {str(e)}")


# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add a route to serve the HTML form
@app.get("/form")
async def get_form():
    return FileResponse("static/form.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=True)

