import shap
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import base64
from io import BytesIO
import joblib
import pandas as pd

class ShapExplainer:
    def __init__(self, model=None, feature_names=None):
        """Initialize the SHAP explainer with a model"""
        print("== XAI DEBUG MSG == Initializing ShapExplainer")
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        if model is not None:
            print(f"== XAI DEBUG MSG == Model of type {type(model)} provided at initialization")
        if feature_names is not None:
            print(f"== XAI DEBUG MSG == {len(feature_names)} feature names provided: {feature_names[:3]}...")
        
    def set_model(self, model):
        """Set or update the model to explain"""
        print(f"== XAI DEBUG MSG == Setting model of type: {type(model)}")
        self.model = model
        self.explainer = None  # Reset explainer when model changes
        print("== XAI DEBUG MSG == Explainer reset")
    
    def _ensure_explainer(self):
        """Make sure the explainer is initialized with the appropriate type"""

        print("== XAI DEBUG MSG == Ensuring explainer is initialized")
        if self.explainer is None:
            if self.model is None:
                print("== XAI DEBUG MSG == ERROR: Model has not been set for the explainer")
                raise ValueError("Model has not been set for the explainer")
            
            print(f"== XAI DEBUG MSG == Creating explainer for model type: {type(self.model)}")
            try:
                # Detect model type
                model_type = type(self.model).__name__
                print(f"== XAI DEBUG MSG == Detected model class: {model_type}")
                
                # Trees: RandomForest, GradientBoosting, XGBoost, etc.
                if any(tree_name in model_type.lower() for tree_name in ["randomrorestregressor", "xgbregressor", "gradientboostingregressor", "tree", "forest", "gbm", "xgboost", "lgbm", "catboost", "gradientboosting"]):
                    print("== XAI DEBUG MSG == Using TreeExplainer for tree-based model")
                    self.explainer = shap.TreeExplainer(self.model)
                
                # Deep learning models
                elif any(dl_name in model_type.lower() for dl_name in ["keras", "tensorflow", "torch", "sequential", "nn", "dnn"]):
                    print("== XAI DEBUG MSG == Using DeepExplainer for neural network model")
                    # Would need background data for this
                    background = self.X_train[:100] if hasattr(self, 'X_train') else None
                    if background is None:
                        print("== XAI DEBUG MSG == No background data for DeepExplainer, falling back to KernelExplainer")
                        self.explainer = shap.KernelExplainer(self.model.predict, background_data)
                    else:
                        self.explainer = shap.DeepExplainer(self.model, background)
                
                # Linear models
                elif any(linear_name in model_type.lower() for linear_name in ["linear", "logistic", "regression", "lasso", "ridge"]):
                    print("== XAI DEBUG MSG == Using LinearExplainer for linear model")
                    # Would need background data for this
                    background = self.X_train[:100] if hasattr(self, 'X_train') else None
                    if background is None:
                        print("== XAI DEBUG MSG == No background data for LinearExplainer, falling back to KernelExplainer")
                        self.explainer = shap.KernelExplainer(self.model.predict, background_data)
                    else:
                        self.explainer = shap.LinearExplainer(self.model, background)
                
                # Fallback for any model type
                else:
                    print("== XAI DEBUG MSG == Using KernelExplainer as fallback for unknown model type")
                    # Would need some background data here
                    background_data = input_data if 'input_data' in locals() else None
                    if background_data is None and hasattr(self, 'X_train'):
                        background_data = self.X_train[:100]
                    if background_data is None:
                        print("== XAI DEBUG MSG == ERROR: No background data available for KernelExplainer")
                        raise ValueError("Background data required for KernelExplainer")
                    
                    # Use model.predict for regression, model.predict_proba for classification
                    if hasattr(self.model, "predict_proba"):
                        prediction_function = self.model.predict_proba
                    else:
                        prediction_function = self.model.predict
                    
                    self.explainer = shap.KernelExplainer(prediction_function, background_data)
                
                print(f"== XAI DEBUG MSG == Explainer created successfully with expected_value: {self.explainer.expected_value}")
            except Exception as e:
                print(f"== XAI DEBUG MSG == ERROR creating explainer: {str(e)}")
                raise
        else:
            print("== XAI DEBUG MSG == Explainer already exists, reusing")
    
    def generate_explanation(self, input_data):
        """Generate SHAP explanation for a prediction"""
        print("== XAI DEBUG MSG == Generating explanation")
        print(f"== XAI DEBUG MSG == Input data type: {type(input_data)}")
        if hasattr(input_data, "shape"):
            print(f"== XAI DEBUG MSG == Input data shape: {input_data.shape}")
        
        try:
            self._ensure_explainer()
            
            # Convert input data to DataFrame if it's not already
            if not isinstance(input_data, pd.DataFrame):
                print("== XAI DEBUG MSG == Converting input data to DataFrame")
                input_data = pd.DataFrame([input_data], columns=self.feature_names)
                print(f"== XAI DEBUG MSG == Converted data shape: {input_data.shape}")
                
            # Calculate SHAP values
            print("== XAI DEBUG MSG == Calculating SHAP values")
            shap_values = self.explainer.shap_values(input_data)
            print(f"== XAI DEBUG MSG == SHAP values type: {type(shap_values)}")
            
            # If shap_values is a list (for multi-output models), use the first element
            if isinstance(shap_values, list):
                print(f"== XAI DEBUG MSG == SHAP values is a list with {len(shap_values)} elements")
                shap_values = shap_values[0]
            
            print(f"== XAI DEBUG MSG == Final SHAP values shape: {shap_values.shape}")
            
            # Create feature importance plot
            print("== XAI DEBUG MSG == Creating feature importance plot")
            plt.figure(figsize=(10, 6))
            try:
                shap.summary_plot(
                    shap_values, 
                    input_data,
                    feature_names=self.feature_names,
                    plot_type="bar",
                    show=False
                )
                print("== XAI DEBUG MSG == Summary plot created successfully")
            except Exception as e:
                print(f"== XAI DEBUG MSG == Error creating summary plot: {str(e)}")
                raise
            
            # Save plot to a base64 string for embedding in HTML
            print("== XAI DEBUG MSG == Saving feature importance plot to base64")
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close()
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            print(f"== XAI DEBUG MSG == Feature importance plot saved, base64 length: {len(img_str)}")
            
            # Create waterfall plot for the specific prediction
            print("== XAI DEBUG MSG == Creating waterfall plot")
            plt.figure(figsize=(10, 8))
            try:
                print(f"== XAI DEBUG MSG == Expected value: {self.explainer.expected_value}")
                print(f"== XAI DEBUG MSG == First instance SHAP values shape: {shap_values[0].shape if hasattr(shap_values[0], 'shape') else 'scalar'}")
                
                expected_value_scalar = self.explainer.expected_value
                if isinstance(expected_value_scalar, np.ndarray):
                    expected_value_scalar = expected_value_scalar[0]  # Extract the scalar from the array

                print(f"== XAI DEBUG MSG == Using scalar expected value: {expected_value_scalar}")

                # Get the number of features
                num_features = len(self.feature_names)
                print(f"== XAI DEBUG MSG == Showing all {num_features} features in waterfall plot")

                # Create SHAP explanation object
                explanation = shap.Explanation(
                    values=shap_values[0], 
                    base_values=expected_value_scalar,
                    data=input_data.iloc[0],
                    feature_names=self.feature_names
                )
                
                # Set max_display to the total number of features to show all
                shap.plots.waterfall(
                    explanation,
                    max_display=num_features,  # Show all features
                    show=False
                )
                
                print("== XAI DEBUG MSG == Waterfall plot created successfully")
            except Exception as e:
                print(f"== XAI DEBUG MSG == Error creating waterfall plot: {str(e)}")
                raise
            
            # Save waterfall plot to base64
            print("== XAI DEBUG MSG == Saving waterfall plot to base64")
            waterfall_buf = BytesIO()
            plt.savefig(waterfall_buf, format='png', bbox_inches='tight', dpi=100)
            plt.close()
            waterfall_buf.seek(0)
            waterfall_img = base64.b64encode(waterfall_buf.read()).decode('utf-8')
            print(f"== XAI DEBUG MSG == Waterfall plot saved, base64 length: {len(waterfall_img)}")
            
            # Get top features
            print("== XAI DEBUG MSG == Calculating feature importance")
            feature_importance = {}
            for i, name in enumerate(self.feature_names):
                feature_importance[name] = abs(shap_values[0][i])
            
            # Get the top features and normalize their importance values to percentages
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"== XAI DEBUG MSG == Top 5 features: {[f[0] for f in top_features]}")

            # Calculate maximum importance for normalization
            max_importance = top_features[0][1] if top_features else 1.0

            # Normalize to percentages (0-100 scale)
            normalized_top_features = [
                {"name": feature[0], "importance": min(100, (feature[1] / max_importance) * 100)} 
                for feature in top_features
            ]

            print(f"== XAI DEBUG MSG == Top 5 features with normalized importance values:")
            for feature in normalized_top_features:
                print(f"== XAI DEBUG MSG ==   {feature['name']}: {feature['importance']:.2f}%")
            
            expected_value = self.explainer.expected_value
            if isinstance(expected_value, np.ndarray):
                print(f"== XAI DEBUG MSG == Expected value is array with shape {expected_value.shape}, using first element")
                expected_value = float(expected_value[0])
            else:
                expected_value = float(expected_value)
                
            # Add additional detailed debug information
            print("\n== XAI DEBUG MSG == DETAILED EXPLANATION OUTPUT ====================")
            
            # Print base value
            print(f"== XAI DEBUG MSG == Base value: {expected_value:.4f}")
            
            # Print full SHAP values with feature names
            print("\n== XAI DEBUG MSG == Full SHAP values for this prediction:")
            for i, (feature, value) in enumerate(zip(self.feature_names, shap_values[0])):
                direction = "INCREASES" if value > 0 else "DECREASES"
                print(f"== XAI DEBUG MSG ==   {feature}: {value:.6f} - {direction} prediction by {abs(value):.6f}")
            
            # Print the most impactful positive and negative features
            positive_impacts = [(name, val) for name, val in zip(self.feature_names, shap_values[0]) if val > 0]
            negative_impacts = [(name, val) for name, val in zip(self.feature_names, shap_values[0]) if val < 0]
            
            positive_impacts.sort(key=lambda x: x[1], reverse=True)
            negative_impacts.sort(key=lambda x: x[1])
            
            print("\n== XAI DEBUG MSG == Top 5 features INCREASING prediction:")
            for i, (feature, value) in enumerate(positive_impacts[:5]):
                if i < len(positive_impacts):
                    print(f"== XAI DEBUG MSG ==   {i+1}. {feature}: +{value:.6f}")
            
            print("\n== XAI DEBUG MSG == Top 5 features DECREASING prediction:")
            for i, (feature, value) in enumerate(negative_impacts[:5]):
                if i < len(negative_impacts):
                    print(f"== XAI DEBUG MSG ==   {i+1}. {feature}: {value:.6f}")
            
            # Print a plain-language summary
            print("\n== XAI DEBUG MSG == Plain language explanation:")
            print(f"== XAI DEBUG MSG == The base value (average prediction) is {expected_value:.2f}")
            
            total_impact = sum(shap_values[0])
            print(f"== XAI DEBUG MSG == The total impact of all features moves the prediction by {total_impact:.2f}")
            print(f"== XAI DEBUG MSG == Final prediction: {expected_value + total_impact:.2f}")
            
            # Top 3 factors summary
            top_factors = sorted(zip(self.feature_names, shap_values[0]), key=lambda x: abs(x[1]), reverse=True)[:3]
            print("\n== XAI DEBUG MSG == Top 3 factors explained:")
            for feature, value in top_factors:
                if value > 0:
                    print(f"== XAI DEBUG MSG ==   {feature} increases the prediction by {value:.2f}")
                else:
                    print(f"== XAI DEBUG MSG ==   {feature} decreases the prediction by {abs(value):.2f}")
            
            print("== XAI DEBUG MSG == END DETAILED EXPLANATION =====================")

            # Add these lines before returning the explanation dictionary
            positive_features = [
                {"name": feature, "impact": f"+{value:.2f}", "importance": value} 
                for feature, value in zip(self.feature_names, shap_values[0]) 
                if value > 0
            ]
            positive_features.sort(key=lambda x: x["importance"], reverse=True)

            negative_features = [
                {"name": feature, "impact": f"{value:.2f}", "importance": value} 
                for feature, value in zip(self.feature_names, shap_values[0]) 
                if value < 0
            ]
            negative_features.sort(key=lambda x: x["importance"])
                
            print("== XAI DEBUG MSG == Returning explanation data")
            return {
                "feature_importance_plot": img_str,
                "waterfall_plot": waterfall_img,
                "top_features": normalized_top_features,
                "positive_features": positive_features[:5],  # Top 5 positive
                "negative_features": negative_features[:5],  # Top 5 negative
                "base_value": expected_value,
                "shap_values": shap_values[0].tolist()
            }
            
        except Exception as e:
            print(f"== XAI DEBUG MSG == CRITICAL ERROR in generate_explanation: {str(e)}")
            import traceback
            print(f"== XAI DEBUG MSG == Traceback: {traceback.format_exc()}")
            raise