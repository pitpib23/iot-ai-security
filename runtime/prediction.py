import joblib
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = BASE_DIR / "model" / "anomaly_model.pkl"
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

FEATURES = ["temp", "humidity", "message_rate"]


model = joblib.load(MODEL_PATH)
print(f"Model loaded: {MODEL_PATH}")

def predict(df):
    """Predict anomalies: 0=normal, 1=anomaly"""
    
    if df is None or len(df) == 0:
        raise ValueError("Empty DataFrame")
    
    missing = [col for col in FEATURES if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    # Extract features
    X = df[FEATURES].copy()
    
    # Fill NaN
    X = X.fillna(0)
    
    # Make predictions
    preds = model.predict(X)
    
    # Create result DataFrame - CRITICAL FIX HERE
    df_result = df.copy()
    
    # Map predictions and use .values to avoid index mismatch
    mapped_values = pd.Series(preds).map({1: 0, -1: 1}).values
    
    # Assign using .loc to ensure proper alignment
    df_result.loc[:, "anomaly"] = mapped_values.astype(int)
    
    # Alternative fix: reset index before assignment
    # df_result = df_result.reset_index(drop=True)
    # df_result["anomaly"] = pd.Series(preds).map({1: 0, -1: 1}).astype(int)
    
    return df_result

# Test
if __name__ == "__main__":
    test_df = pd.DataFrame({
        "temp": [27.5, 90.0, 25.1, 120.5],
        "humidity": [55.0, 10.0, 60.0, 15.2],
        "message_rate": [5, 180, 4, 150]
    })
    
    result = predict(test_df)
    print("\nTest Results:")
    print(result)
    print(f"\nNormal: {(result['anomaly']==0).sum()}, Anomaly: {(result['anomaly']==1).sum()}")