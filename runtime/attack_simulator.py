import time
import random
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# ================== MQTT CONFIG ==================
BROKER = "localhost"
PORT = 1883

# ================== NORMAL DEVICES ==================
NORMAL_CLIENTS = [
    "sensor_temp_01",
    "sensor_humid_01",
    "sensor_pressure_01",
    "plc_line1",
    "plc_line2",
    "edge_gateway_01"
]

NORMAL_TOPICS = [
    "iot/factory/line1/sensor01/temp",
    "iot/factory/line1/sensor01/humidity",
    "iot/factory/line2/sensor02/temp",
    "iot/factory/line2/sensor02/humidity"
]

# ================== ATTACKERS ==================
ATTACK_CLIENTS = [
    "mqtt_explorer",
    "mosquitto_pub",
    "port_scanner",
    "unknown_client",
    "legacy_client",
    "fake_temp_sensor",
    "fake_humidity_node",
    "esp8266_node",
    "esp32_gateway"
]

# intent patterns
ATTACK_TOPIC_INTENTS = [
    "iot/system/#",
    "iot/factory/#",
    "iot/debug/#",
    "iot/system/network/reset",
    "iot/system/restart",
    "iot/factory/line2/plc01/override",
    "iot/factory/config/backup"
]

# real topics
REAL_SYSTEM_TOPICS = [
    "iot/system/restart",
    "iot/system/network/reset",
    "iot/system/shutdown",
    "iot/system/update"
]

REAL_FACTORY_TOPICS = [
    "iot/factory/line1/plc01/override",
    "iot/factory/line2/plc01/override",
    "iot/factory/line1/hmi01/control",
    "iot/factory/logs"
]

REAL_DEBUG_TOPICS = [
    "iot/debug/test",
    "iot/debug/raw",
    "iot/debug/memory"
]

# ================== PAYLOAD GENERATORS ==================
def normal_payload(client_id, topic):
    return {
        "client_id": client_id,  # เพิ่ม client_id
        "topic": topic,           # เพิ่ม topic
        "temp": round(random.uniform(20, 35), 2),
        "humidity": round(random.uniform(40, 70), 2),
        "message_rate": random.randint(1, 10),
        "timestamp": datetime.now().isoformat()
    }

def attack_payload(client_id, topic):
    attack_type = random.choice([
        "high_temp",
        "low_humidity",
        "burst",
        "mixed"
    ])

    base_payload = {
        "client_id": client_id,  # เพิ่ม client_id
        "topic": topic,           # เพิ่ม topic
        "timestamp": datetime.now().isoformat(),
        "attack_type": attack_type
    }

    if attack_type == "high_temp":
        base_payload.update({
            "temp": round(random.uniform(90, 150), 2),
            "humidity": round(random.uniform(40, 70), 2),
            "message_rate": random.randint(30, 80)
        })

    elif attack_type == "low_humidity":
        base_payload.update({
            "temp": round(random.uniform(80, 120), 2),
            "humidity": round(random.uniform(5, 20), 2),
            "message_rate": random.randint(20, 60)
        })

    elif attack_type == "burst":
        base_payload.update({
            "temp": round(random.uniform(80, 140), 2),
            "humidity": round(random.uniform(10, 30), 2),
            "message_rate": random.randint(100, 200)
        })

    else:  # mixed
        base_payload.update({
            "temp": round(random.uniform(70, 130), 2),
            "humidity": round(random.uniform(10, 90), 2),
            "message_rate": random.randint(40, 150)
        })

    return base_payload

# ================== TOPIC RESOLVER ==================
def resolve_attack_topic(intent):
    if intent == "iot/system/#":
        return random.choice(REAL_SYSTEM_TOPICS)

    if intent == "iot/factory/#":
        return random.choice(REAL_FACTORY_TOPICS)

    if intent == "iot/debug/#":
        return random.choice(REAL_DEBUG_TOPICS)

    return intent

# ================== MQTT CLIENT ==================
try:
    from paho.mqtt.client import CallbackAPIVersion
    client = mqtt.Client(
        client_id="iot-attack-simulator",
        callback_api_version=CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv311
    )
except:
    client = mqtt.Client(
        client_id="iot-attack-simulator",
        protocol=mqtt.MQTTv311
    )

client.connect(BROKER, PORT, 60)

print("[+] Attack simulator started")

# ================== MAIN LOOP ==================
iteration = 0

try:
    while True:
        iteration += 1
        is_attack = random.random() < 0.10  # 10% attack

        if not is_attack:
            # ==================== NORMAL TRAFFIC ====================
            client_id = random.choice(NORMAL_CLIENTS)
            topic = random.choice(NORMAL_TOPICS)
            payload = normal_payload(client_id, topic)  # ส่ง client_id และ topic

            print(f"[{iteration:04d}] NORMAL | {client_id:20s} | T={payload['temp']:6.2f} H={payload['humidity']:5.2f} R={payload['message_rate']:3d}")
            
            client.publish(topic, json.dumps(payload))
            time.sleep(random.uniform(1.0, 2.0))

        else:
            # ==================== ATTACK TRAFFIC ====================
            client_id = random.choice(ATTACK_CLIENTS)
            intent = random.choice(ATTACK_TOPIC_INTENTS)
            topic = resolve_attack_topic(intent)
            payload = attack_payload(client_id, topic)  # ส่ง client_id และ topic

            # burst behavior
            burst_count = random.randint(3, 15) if payload["message_rate"] > 80 else 1

            attack_type = payload.get('attack_type', 'unknown')
            
            if burst_count > 1:
                print(f"[{iteration:04d}] ATTACK | {client_id:20s} | T={payload['temp']:6.2f} H={payload['humidity']:5.2f} R={payload['message_rate']:3d} | {attack_type:12s} | Burst={burst_count}")
                
                for i in range(burst_count):
                    client.publish(topic, json.dumps(payload))
                    print(f"          └─ Burst {i+1}/{burst_count} sent")
                    time.sleep(random.uniform(0.05, 0.3))
            else:
                print(f"[{iteration:04d}] ATTACK | {client_id:20s} | T={payload['temp']:6.2f} H={payload['humidity']:5.2f} R={payload['message_rate']:3d} | {attack_type:12s}")
                client.publish(topic, json.dumps(payload))

except KeyboardInterrupt:
    print("\n[!] Keyboard interrupt detected")
    print("[+] Stopping attack simulator...")
    client.disconnect()
    print("[+] Disconnected from broker")
    print(f"[+] Total iterations: {iteration}")
    print("[+] Simulator stopped successfully")

except Exception as e:
    print(f"\n[ERROR] Unexpected error: {e}")
    client.disconnect()
    print("[+] Disconnected from broker")