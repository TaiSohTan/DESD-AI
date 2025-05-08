import joblib
import numpy as np
import os
import json
from datetime import datetime
import pandas as pd
import traceback

class WeightedEnsembleModel:
    """
    A model that combines predictions from two component models using weighted averaging.
    """
    def __init__(self, model1, model2, weights):
        self.model1 = model1  # Simplified model with feature selection
        self.model2 = model2  # Hybrid model with error correction
        self.weights = weights  # Weights for ensemble averaging
        
        # Copy feature names from first model for compatibility with SHAP
        if hasattr(model1, 'feature_names_in_'):
            self.feature_names_in_ = model1.feature_names_in_
        
        # Set estimator type for compatibility with sklearn
        self._estimator_type = "regressor"
    
    def predict(self, X):
        """Make predictions using the weighted ensemble approach."""
        try:
            # Get predictions from each component model
            preds1 = self.model1.predict(X)
            preds2 = self.model2.predict(X)
            
            # Apply weights to combine the predictions
            ensemble_preds = self.weights[0] * preds1 + self.weights[1] * preds2
            
            return ensemble_preds
        except Exception as e:
            print(f"Error in ensemble prediction: {str(e)}")
            traceback.print_exc()
            # If ensemble fails, fallback to model1
            return self.model1.predict(X)

def create_ensemble_model(
    simplified_model_path="models/simplified_model.pkl",
    hybrid_model_path="models/hybrid_model.pkl",
    weights=None,
    save_path="active_model.pkl",
    metadata_path="active_model_metadata.json"
):
    """
    Create the weighted ensemble model by loading component models.
    
    Args:
        simplified_model_path: Path to the simplified model
        hybrid_model_path: Path to the hybrid model
        weights: List/array of two weights, or None to use default
        save_path: Path where the ensemble model will be saved
        metadata_path: Path where the metadata JSON will be saved
    """
    try:
        # Check if component models exist
        if not os.path.exists(simplified_model_path):
            print(f"Error: Simplified model not found at {simplified_model_path}")
            return None
            
        if not os.path.exists(hybrid_model_path):
            print(f"Error: Hybrid model not found at {hybrid_model_path}")
            return None
        
        # Set default weights if not provided - from your notebook results
        if weights is None:
            weights = np.array([0.45, 0.55])  # Based on best weights found
        
        # Load the component models
        print("Loading component models...")
        simplified_model = joblib.load(simplified_model_path)
        hybrid_model = joblib.load(hybrid_model_path)
        
        # Create the ensemble model
        ensemble_model = WeightedEnsembleModel(
            model1=simplified_model,
            model2=hybrid_model,
            weights=weights
        )
        
        # Save the ensemble model as the active model
        print(f"Saving ensemble model to {save_path}...")
        joblib.dump(ensemble_model, save_path)
        
        # Create and save metadata
        metadata = {
            "model_type": "weighted_ensemble",
            "component_models": [
                os.path.basename(simplified_model_path),
                os.path.basename(hybrid_model_path)
            ],
            "weights": weights.tolist(),
            "requires_scaling": True,  # Models require scaling
            "created_at": datetime.now().isoformat()
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("Ensemble model created and saved successfully")
        return ensemble_model
        
    except Exception as e:
        print(f"Error creating ensemble model: {str(e)}")
        traceback.print_exc()
        return None

# This function would be called by admin tools or deployment scripts
def deploy_ensemble_model():
    """
    Deploy the weighted ensemble model as the active model.
    This function should be called during initial setup or when models are updated.
    """
    print("Deploying weighted ensemble hybrid model...")
    
    # Create and save the ensemble model
    ensemble_model = create_ensemble_model(
        simplified_model_path="models/simplified_model.pkl",
        hybrid_model_path="models/hybrid_model.pkl",
        weights=[0.45, 0.55],  # Optimal weights from your notebook
        save_path="active_model.pkl",
        metadata_path="active_model_metadata.json"
    )
    
    if ensemble_model is not None:
        print("Deployment successful!")
        return True
    else:
        print("Deployment failed!")
        return False

# For direct execution of this script
if __name__ == "__main__":
    deploy_ensemble_model()