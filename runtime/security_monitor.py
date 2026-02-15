import time
import json
import pandas as pd
import paho.mqtt.client as mqtt
from pathlib import Path
from datetime import datetime

try:
    from prediction import predict
except ImportError:
    print("Cannot import prediction.py")
    exit(1)

BROKER = "localhost"
PORT = 1883
CSV_PATH = Path(__file__).parent.parent / "data" / "sensor_log.csv"

# Setup MQTT
try:
    from paho.mqtt.client import CallbackAPIVersion
    client = mqtt.Client(client_id="monitor", callback_api_version=CallbackAPIVersion.VERSION2)
except:
    client = mqtt.Client(client_id="monitor")

try:
    client.connect(BROKER, PORT, 60)
    print(f"Connected to {BROKER}:{PORT}")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

print(f"Reading: {CSV_PATH}")
print("Monitoring started...\n")

last_processed_index = -1
iteration = 0

try:
    while True:
        iteration += 1
        
        # Check CSV exists
        if not CSV_PATH.exists():
            if iteration % 10 == 1:
                print("Waiting for CSV...")
            time.sleep(2)
            continue
        
        # Read CSV
        try:
            df = pd.read_csv(CSV_PATH)
        except Exception as e:
            if iteration % 10 == 1:
                print(f"Error reading CSV: {e}")
            time.sleep(2)
            continue
        
        # Check if there are new rows
        total_rows = len(df)
        
        if total_rows == 0:
            if iteration % 10 == 1:
                print("CSV is empty")
            time.sleep(2)
            continue
        
        # Get only NEW rows
        new_rows_start = last_processed_index + 1
        
        if new_rows_start >= total_rows:
            if iteration % 10 == 1:
                print(f"No new data (processed up to row {last_processed_index})")
            time.sleep(2)
            continue
        
        # Get new data
        new_df = df.iloc[new_rows_start:].copy()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing rows {new_rows_start} to {total_rows-1} ({len(new_df)} new rows)")
        
        # Check columns
        required = ["temp", "humidity", "message_rate"]
        missing = [col for col in required if col not in new_df.columns]
        
        if missing:
            print(f"ERROR: Missing columns: {missing}")
            time.sleep(2)
            continue
        
        # Show data range
        print(f"   Data range: T=[{new_df['temp'].min():.1f}-{new_df['temp'].max():.1f}] "
              f"H=[{new_df['humidity'].min():.1f}-{new_df['humidity'].max():.1f}] "
              f"R=[{new_df['message_rate'].min()}-{new_df['message_rate'].max()}]")
        
        # Predict
        try:
            result = predict(new_df)
            
            # Check if anomaly column exists
            if 'anomaly' not in result.columns:
                print("ERROR: predict() did not return 'anomaly' column!")
                print(f"Returned columns: {list(result.columns)}")
                time.sleep(2)
                continue
            
            # Count results
            normal_count = int((result['anomaly'] == 0).sum())
            anomaly_count = int((result['anomaly'] == 1).sum())
            
            print(f"   Predictions: {normal_count} normal, {anomaly_count} anomaly")
            
        except Exception as e:
            print(f"ERROR in prediction: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(2)
            continue
        
        # Separate normal and anomalies
        anomalies = result[result["anomaly"] == 1]
        normals = result[result["anomaly"] == 0]
        
        # Send NORMAL data
        if len(normals) > 0:
            for idx, row in normals.iterrows():
                normal_data = {
                    "time": int(row["timestamp"]),
                    "client": str(row.get("client_id", "unknown")),
                    "topic": str(row.get("topic", "unknown")),
                    "temp": float(row["temp"]),
                    "humidity": float(row["humidity"]),
                    "rate": int(row["message_rate"]),
                    "status": "normal"
                }
                client.publish('security/alert', json.dumps(normal_data))
                    
        # Send ANOMALY alerts
        if len(anomalies) > 0:
            print(f"\n*** ALERT: {len(anomalies)} anomalies detected! ***")
            
            for idx, row in anomalies.iterrows():
                alert = {
                    "time": int(row["timestamp"]),
                    "client": str(row.get("client_id", "unknown")),
                    "topic": str(row.get("topic", "unknown")),
                    "temp": float(row["temp"]),
                    "humidity": float(row["humidity"]),
                    "rate": int(row["message_rate"]),
                    "status": "anomaly"
                }
                client.publish("security/alert", json.dumps(alert))
                print(f"      Alert: T={alert['temp']:.1f} H={alert['humidity']:.1f} R={alert['rate']} | {alert['client']}")
            print()
        
        # Update last processed index
        last_processed_index = total_rows - 1
        
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped")
    client.disconnect()
except Exception as e:
    print(f"\nUnexpected error: {e}")
    import traceback
    traceback.print_exc()
    client.disconnect()
