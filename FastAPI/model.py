import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import HuberRegressor

class WeightedEnsembleHybridModel(BaseEstimator, RegressorMixin):
    def __init__(self, corr_threshold=0.05, rf_model=None, gbr_model=None, 
                 blending_model=None, selected_features=None):
        print("Initializing simplified ensemble model")
        
        self.corr_threshold = corr_threshold
        
        # Base models - use provided or create defaults
        self.rf_model = rf_model if rf_model is not None else RandomForestRegressor(
            n_estimators=200, max_depth=10, random_state=42)
        
        self.gbr_model = gbr_model if gbr_model is not None else GradientBoostingRegressor(
            learning_rate=0.05, n_estimators=200, random_state=42)
        
        # Blending model
        self.blending_model = HuberRegressor(epsilon=1.35)
        
        # No separate error model in simplified version
        self.error_model = None
        
        # Keep selected_features for compatibility
        self.selected_features = selected_features
        
        # For compatibility with existing service code
        self.is_fully_loaded = (rf_model is not None and 
                               gbr_model is not None and 
                               blending_model is not None and 
                               selected_features is not None)
        
        # Store training data for potential fallback
        self._X_train = None
        self._y_train = None
    
    def _select_features(self, X, y):
        """Select features with correlation above threshold"""
        print(f"Selecting features with correlation threshold: {self.corr_threshold}")
        n_features = X.shape[1]
        correlations = np.zeros(n_features)
        
        for i in range(n_features):
            correlations[i] = np.corrcoef(X[:, i], y)[0, 1]
        
        # Keep features with absolute correlation >= threshold
        self.selected_features = np.abs(correlations) >= self.corr_threshold
        selected_count = np.sum(self.selected_features)
        print(f"Selected {selected_count} out of {n_features} features")
        
        return X[:, self.selected_features]
    
    def fit(self, X, y):
        """Fit the simplified ensemble model to training data"""
        print("Training simplified ensemble model")
        
        # Store training data for fallback
        self._X_train = np.array(X) if not isinstance(X, np.ndarray) else X
        self._y_train = np.array(y) if not isinstance(y, np.ndarray) else y
        
        # 1. Feature selection
        X_selected = self._select_features(self._X_train, self._y_train)
        
        # 2. Train base models
        print("Training base models...")
        self.rf_model.fit(X_selected, self._y_train)
        self.gbr_model.fit(X_selected, self._y_train)
        
        # 3. Generate model predictions
        rf_preds = self.rf_model.predict(X_selected)
        gbr_preds = self.gbr_model.predict(X_selected)
        
        # 4. Create meta-features (simplified: just the base predictions)
        meta_features = np.column_stack([rf_preds, gbr_preds])
        
        # 5. Train blending model
        print("Training blending model...")
        self.blending_model.fit(meta_features, self._y_train)
        
        # Model is now loaded
        self.is_fully_loaded = True
        print("Model training completed")
        
        return self
    
    def predict(self, X):
        """Generate predictions from the simplified ensemble model"""
        # For compatibility with existing code
        if hasattr(self, '_ensure_model_ready'):
            self._ensure_model_ready(X)
        
        # Convert to numpy arrays if needed
        X_array = np.array(X) if not isinstance(X, np.ndarray) else X
        
        # Check if model is fitted
        if self.selected_features is None:
            raise ValueError("Model not fitted. Call fit() before predict().")
        
        # 1. Select features
        X_selected = X_array[:, self.selected_features]
        
        # 2. Generate base model predictions
        rf_preds = self.rf_model.predict(X_selected)
        gbr_preds = self.gbr_model.predict(X_selected)
        
        # 3. Create meta-features (simplified version)
        meta_features = np.column_stack([rf_preds, gbr_preds])
        
        # 4. Apply blending model for final predictions
        final_preds = self.blending_model.predict(meta_features)
        
        return final_preds
    
    # Add this method for compatibility with existing code
    def _ensure_model_ready(self, X):
        """Simplified model readiness check"""
        if self.selected_features is None:
            if self._X_train is not None and self._y_train is not None:
                print("Training fallback model...")
                self.fit(self._X_train, self._y_train)
            else:
                raise ValueError("Model not fitted and no training data available")