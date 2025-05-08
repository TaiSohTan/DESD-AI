import numpy as np
import warnings

# Monkey patch np.bool to maintain compatibility with SHAP
if not hasattr(np, 'bool'):
    print("== XAI DEBUG MSG == Adding np.bool compatibility for SHAP")
    np.bool = bool
    

    # Suppress the deprecation warning
    warnings.filterwarnings('ignore', category=DeprecationWarning, message='`np.bool` is a deprecated alias')

# Suppress IPython warning
warnings.filterwarnings('ignore', message='IPython could not be loaded')

# Fix deprecated np.int
if not hasattr(np, 'int'):
    np.int = int

# Fix other potential deprecations
if not hasattr(np, 'bool'):
    np.bool = bool
if not hasattr(np, 'float'):
    np.float = float
if not hasattr(np, 'complex'):
    np.complex = complex
if not hasattr(np, 'object'):
    np.object = object
if not hasattr(np, 'str'):
    np.str = str
if not hasattr(np, 'long'):
    np.long = int

print("NumPy compatibility patches applied for SHAP library")