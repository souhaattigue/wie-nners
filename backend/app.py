import re
from datetime import datetime
import requests
import time

# Set these to your project values
WOKWI_API_URL = "https://wokwi.com/projects/378657378646048769"
WOKWI_API_TOKEN = "wok_6qmKRUFiLHSGJzK8lo7PYDJNBHopCKkAbaac6fff"

number_re = re.compile(r'(-?\d+(?:\.\d+)?)')

def try_extract_number(s):
    m = number_re.search(s)
    if not m:
        return None
    v = m.group(1)
    return float(v) if '.' in v else int(v)

def parse_console_text_for_vars(text):
    # Look for obvious labels printed by your MicroPython code.
    # Adjust the label patterns if your printed lines are different.
    res = {}
    lines = text.splitlines()
    for ln in reversed(lines[-20:]):  # check last 20 lines for recent values
        if 'temperaturexet' in ln or 'temperaturexet' in ln.lower():
            val = try_extract_number(ln)
            if val is not None:
                res['temperaturexet'] = val
        if 'temperature' in ln and 'temperaturexet' not in ln:
            val = try_extract_number(ln)
            if val is not None:
                res['temperature'] = val
        if 'humidity' in ln:
            val = try_extract_number(ln)
            if val is not None:
                res['humidity'] = val
        if 'light' in ln or 'ldr' in ln.lower():
            val = try_extract_number(ln)
            if val is not None:
                res['light'] = val
        # catch generic numeric prints (if your code prints single numbers)
        # as a last resort map first numeric to temperaturexet if missing
    return res

def read_sensor_data_from_wokwi():
    headers = {
        'Authorization': f'Bearer {WOKWI_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(WOKWI_API_URL, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"❌ Connection error to Wokwi: {e}")
        return None

    if resp.status_code != 200:
        print(f"❌ Error fetching data from Wokwi: {resp.status_code} {resp.text[:200]}")
        return None

    # Try JSON parsing first
    try:
        payload = resp.json()
    except ValueError:
        payload = None

    parsed = {}
    if isinstance(payload, dict):
        # Common patterns: payload may contain keys directly or be nested
        # Try direct keys:
        for k in ('temperature', 'humidity', 'light', 'temperaturexet',
                  'Relay', 'Relay1', 'relayAir', 'pump_status', 'motor_status'):
            if k in payload:
                parsed[k] = payload.get(k)
        # Some APIs wrap values inside `data` or `payload`
        for container in ('data', 'payload', 'result'):
            if container in payload and isinstance(payload[container], dict):
                for k in ('temperature', 'humidity', 'light', 'temperaturexet'):
                    if k in payload[container]:
                        parsed[k] = payload[container][k]
        # If we found useful keys, return them mapped to your preferred names
        if parsed:
            return {
                "temperature_celsius": parsed.get('temperature'),
                "humidity_percentage": parsed.get('humidity'),
                "light_percentage": parsed.get('light'),
                "temperaturexet_raw": parsed.get('temperaturexet'),
                "relay_1": parsed.get('Relay') or parsed.get('Relay1'),
                "relay_air": parsed.get('relayAir') or parsed.get('relay_air'),
                "timestamp": datetime.now().isoformat()
            }

    # Fallback: parse textual console output (some Wokwi endpoints return console logs)
    text = resp.text
    fallback = parse_console_text_for_vars(text)
    if fallback:
        return {
            "temperature_celsius": fallback.get('temperature'),
            "humidity_percentage": fallback.get('humidity'),
            "light_percentage": fallback.get('light'),
            "temperaturexet_raw": fallback.get('temperaturexet'),
            "timestamp": datetime.now().isoformat()
        }

    print("❌ No recognizable sensor data found in Wokwi response.")
    return None


if __name__ == "__main__":
    # Simple poller to test the Wokwi fetch function.
    # Update WOKWI_API_URL and WOKWI_API_TOKEN above before running.
    print("Polling Wokwi for sensor data (Ctrl+C to stop)...")
    try:
        while True:
            data = read_sensor_data_from_wokwi()
            print("Wokwi ->", data)
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopped by user.")