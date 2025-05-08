import joblib
import pandas as pd
import numpy as np
import os
from model import WeightedEnsembleHybridModel

class ModelService:
    def __init__(self):
        """Initialize the model service"""
        self.model = None
        self.initialize_model()
    
    def initialize_model(self):
        """Initialize model from individual components only"""
        print("Loading individual model components...")
        try:
            # Load the saved components with proper error handling
            component_paths = {
                'rf_model': 'training_data/rf.pkl',
                'gbr_model': 'training_data/gbr.pkl',
                'blending_model': 'training_data/blending_model.pkl',
                'error_model': 'training_data/error_model.pkl',
                'selected_features': 'training_data/selected_features.pkl'
            }
            
            components = {}
            for name, path in component_paths.items():
                try:
                    components[name] = joblib.load(path)
                    print(f"Successfully loaded {name} from {path}")
                except Exception as e:
                    print(f"Failed to load {name}: {e}")
                    components[name] = None
            
            # Initialize the model with the loaded components
            self.model = WeightedEnsembleHybridModel(
                corr_threshold=0.05,
                rf_model=components['rf_model'],
                gbr_model=components['gbr_model'],
                selected_features=components['selected_features']
            )
            
            # Check if all necessary components are loaded
            if (components['rf_model'] is not None and 
                components['gbr_model'] is not None and 
                components['selected_features'] is not None):
                print("Essential model components loaded successfully")
            else:
                print("WARNING: Some essential components missing, model may not function correctly")
                
                # Try to load training data for fallback
                try:
                    X_train = joblib.load('training_data/X_train.pkl')
                    y_train = joblib.load('training_data/y_train.pkl')
                    self.model._X_train = X_train
                    self.model._y_train = y_train
                    print("Training data loaded for possible fallback training")
                except Exception as e:
                    print(f"Failed to load training data: {e}")
                
        except Exception as e:
            print(f"Failed to initialize model from components: {e}")
            raise RuntimeError(f"Model initialization failed: {e}")
    
    def predict(self, data):
        """Make predictions using the initialized model"""
        if self.model is None:
            self.initialize_model()
            if self.model is None:
                raise RuntimeError("Model initialization failed")
        
        # Handle different input formats
        if isinstance(data, pd.DataFrame):
            input_data = data
        elif isinstance(data, dict):
            input_data = pd.DataFrame([data])
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            input_data = pd.DataFrame(data)
        else:
            input_data = data
            
        # Make prediction
        return self.model.predict(input_data)
    
    def get_model_info(self):
        """Return information about the loaded model"""
        if self.model is None:
            return {"status": "Model not loaded"}
            
        # Count active features if selected_features is available
        feature_count = 0
        if hasattr(self.model, 'selected_features') and self.model.selected_features is not None:
            feature_count = np.sum(self.model.selected_features)
            
        return {
            "model_type": "WeightedEnsembleHybridModel",
            "is_fully_loaded": hasattr(self.model, 'is_fully_loaded') and self.model.is_fully_loaded,
            "feature_count": int(feature_count),
            "components": {
                "rf_model": self.model.rf_model is not None,
                "gbr_model": self.model.gbr_model is not None,
                "blending_model": self.model.blending_model is not None,
                "error_model": self.model.error_model is not None,
                "selected_features": self.model.selected_features is not None
            }
        }

# Create a singleton instance
model_service = ModelService()

# Example usage (can be commented out in production)
if __name__ == "__main__":
    # Test the model with a sample input
    print("\nTesting model with sample input...")
    
    # Sample preprocessed data (same as in your original file)
    preprocessed_data = {
        "General_Rest": 0.0,
        "General_Fixed": 520.0,
        "Special_Earnings_Loss": 0.0,
        "Injury_Prognosis": 6.0,
        "Special_Therapy": 350.0,
        "Special_Asset_Damage": 0.0,
        "Special_Fixes": 0.0,
        "Special_Usage_Loss": 0.0,
        "Accident_Type": 1134.4706,
        "Special_Journey_Expenses": 0.0,
        "Days_Between_Accident_And_Claim": 51.0,
        "Vehicle_Age": 18.0,
        "Driver_Age": 29.0,
        "Special_Loaner_Vehicle": 0.0,
        "Special_Overage": 0.0,
        "General_Uplift": 0.0,
        "Accident_Description": 1193.9175,
        "Exceptional_Circumstances": 0,
        "Minor_Psychological_Injury": 1,
        "Injury_Description": 1229.4915,
        "Special_Health_Expenses": 0.0,
        "Special_Additional_Injury": 0.0,
        "Special_Medications": 0.0,
        "Special_Rehabilitation": 0.0,
        "Special_Trip_Costs": 0.0,
        "Number_Of_Passengers": 1.0,
        "Whiplash": 0,
        "Police_Report_Filed": 0,
        "Witness_Present": 0,
        "Dominant_Injury": 1188.2923,
        "Gender_Female": 0.0,
        "Gender_Male": 1.0,
        "Gender_Other": 0.0,
        "Vehicle_Type_Car": 0.0,
        "Vehicle_Type_Motorcycle": 0.0,
        "Vehicle_Type_Truck": 1.0,
        "Weather_Conditions_Rainy": 0.0,
        "Weather_Conditions_Snowy": 1.0,
        "Weather_Conditions_Sunny": 0.0
    }
    
    # Make a test prediction
    try:
        sample_df = pd.DataFrame([preprocessed_data])
        predictions = model_service.predict(sample_df)
        print(f"Sample prediction result: {predictions[0]}")
        print(f"Model info: {model_service.get_model_info()}")
    except Exception as e:
        print(f"Test prediction failed: {e}")