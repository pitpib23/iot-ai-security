import csv
import time
import json
import paho.mqtt.client as mqtt
from pathlib import Path

BROKER = "localhost"
PORT = 1883
CSV_PATH = Path(__file__).parent.parent / "data" / "sensor_log.csv"

# Create directory
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

# CSV header
fields = ["timestamp", "client_id", "topic", "payload_size", "temp", "humidity", "message_rate"]

# Create CSV file
with open(CSV_PATH, "w", newline="") as f:
    csv.writer(f).writerow(fields)

print(f"CSV ready: {CSV_PATH}")

def on_message(client, userdata, msg):
    try:
        # Parse JSON payload
        payload_str = msg.payload.decode('utf-8')
        try:
            payload = json.loads(payload_str)
        except:
            payload = {}
        
        # Extract data
        temp = payload.get("temp", 0)
        humidity = payload.get("humidity", 0)
        message_rate = payload.get("message_rate", 0)
        client_id = payload.get("client_id", "unknown")

        # Build row
        row = [
            int(time.time()),
            client_id,
            msg.topic,
            len(msg.payload),
            float(temp),
            float(humidity),
            int(message_rate)
        ]
        
        # Save to CSV
        with open(CSV_PATH, "a", newline="") as f:
            csv.writer(f).writerow(row)
        
        print(f"Logged: {msg.topic[:30]:30s} T={temp:6.1f} H={humidity:5.1f} R={message_rate:3d}")
    
    except Exception as e:
        print(f"Error: {e}")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Connected to {BROKER}:{PORT}")
        client.subscribe("iot/#")
        print("Subscribed to all topics")
    else:
        print(f"Connection failed: {rc}")

# Setup MQTT client
try:
    from paho.mqtt.client import CallbackAPIVersion
    client = mqtt.Client(client_id="collector", callback_api_version=CallbackAPIVersion.VERSION2)
except:
    client = mqtt.Client(client_id="collector")

client.on_connect = on_connect
client.on_message = on_message

# Connect and run
try:
    client.connect(BROKER, PORT, 60)
    print("Collecting data... (Ctrl+C to stop)")
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped")
except Exception as e:
    print(f"Error: {e}")
