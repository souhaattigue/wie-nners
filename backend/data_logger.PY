import re
import json
import csv
import os
from datetime import datetime
import requests
import time

# --- CONFIGURATION ---
# NOTE: set this to the Wokwi API endpoint for your project. Typical forms:
#  - JSON/console output: https://wokwi.com/api/projects/<PROJECT_ID>/console
#  - or: https://wokwi.com/api/projects/<PROJECT_ID>/data
# Replace <PROJECT_ID> and set WOKWI_API_TOKEN from your Wokwi account settings.
WOKWI_API_URL = "https://wokwi.com/projects/378657378646048769"  # <-- update to API endpoint
WOKWI_API_TOKEN = "wok_6qmKRUFiLHSGJzK8lo7PYDJNBHopCKkAbaac6fff"
LOG_FILE = "wokwi_sensor_log.csv"
# ---------------------

number_re = re.compile(r'(-?\d+(?:\.\d+)?)')

def try_extract_number(s):
    """Tente d'extraire le premier nombre d'une chaîne."""
    m = number_re.search(s)
    if not m:
        return None
    v = m.group(1)
    return float(v) if '.' in v else int(v)

def parse_console_text_for_vars(text):
    """Fallback: analyse textuelle si la lecture JSON échoue."""
    res = {}
    lines = text.splitlines()
    for ln in reversed(lines[-20:]): 
        # Utiliser des noms de variables clairs dans le MicroPython pour une meilleure détection
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
    return res

def read_sensor_data_from_wokwi():
    """Récupère et analyse l'état du projet Wokwi."""
    headers = {
        'Authorization': f'Bearer {WOKWI_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        resp = requests.get(WOKWI_API_URL, headers=headers, timeout=10)
    except requests.RequestException as e:
        # Correction de l'UnicodeEncodeError en évitant les emojis
        print(f"[ERROR] Connection error to Wokwi: {e}")
        return None

    if resp.status_code != 200:
        print(f"[ERROR] Error fetching data from Wokwi: {resp.status_code} {resp.text[:200]}")
        return None
    
    # Tentative 1: Lecture JSON (méthode préférée et la plus fiable)
    try:
        # Recherche du dernier objet JSON complet dans la réponse texte
        last_json_match = re.search(r'\{.*?\}', resp.text, re.DOTALL | re.MULTILINE)
        if last_json_match:
            json_text = last_json_match.group(0)
            payload = json.loads(json_text)

            if isinstance(payload, dict):
                # Mappage flexible: essaye plusieurs clés possibles
                temp = payload.get('temperature') or payload.get('temperature_dht') or payload.get('temp')
                hum = payload.get('humidity') or payload.get('hum')
                lightp = payload.get('light') or payload.get('light_percent') or payload.get('light_percentage')
                temp_ntc = payload.get('temperaturexet') or payload.get('temp_ntc_raw') or payload.get('temp_ntc')

                return {
                    "temperature_celsius": temp,
                    "humidity_percentage": hum,
                    "light_percentage": lightp,
                    "temperaturexet_raw": temp_ntc,
                    "timestamp": datetime.now().isoformat()
                }

    except json.JSONDecodeError:
        # Si le JSON échoue, on conservera resp.text pour debug plus bas
        pass

    # Tentative 2: Fallback textuel (si la lecture JSON échoue)
    text = resp.text
    fallback = parse_console_text_for_vars(text)
    if fallback:
        # Retourne les données trouvées par l'analyse textuelle
        return {
            "temperature_celsius": fallback.get('temperature'),
            "humidity_percentage": fallback.get('humidity'),
            "light_percentage": fallback.get('light'),
            "temperaturexet_raw": fallback.get('temperaturexet'),
            "timestamp": datetime.now().isoformat()
        }

    # Message d'erreur final – imprime une portion de la réponse pour faciliter le debug
    snippet = resp.text[:400].replace('\n', ' ').strip()
    print(f"[X] No recognizable sensor data found in Wokwi response. Snippet: {snippet}")
    return None

def log_data_to_csv(data):
    """Écrit les données reçues dans un fichier CSV."""
    
    # Définition des champs du CSV (colonnes)
    fieldnames = [
        "timestamp", 
        "temperature_celsius", 
        "humidity_percentage", 
        "light_percentage", 
        "temperaturexet_raw"
    ]
    
    # Vérifie si le fichier existe pour décider si nous devons écrire l'en-tête (header)
    file_exists = os.path.exists(LOG_FILE)
    
    # Ouvre le fichier en mode 'a' (append/ajouter)
    with open(LOG_FILE, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Écrit l'en-tête si le fichier vient d'être créé
        if not file_exists:
            writer.writeheader()
        
        # Écrit la ligne de données
        # On ne garde que les clés définies dans fieldnames pour éviter les erreurs
        log_entry = {k: data.get(k) for k in fieldnames}
        writer.writerow(log_entry)
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Data logged to {LOG_FILE}")

def season(timestamp_str):
    """Détermine la saison en fonction du mois."""
    dt = datetime.fromisoformat(timestamp_str)
    month = dt.month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"

if __name__ == "__main__":
    print(f"Polling Wokwi for sensor data and logging to {LOG_FILE} (Ctrl+C to stop)...")
    
    try:
        while True:
            data = read_sensor_data_from_wokwi()
            
            if data and all(data.get(k) is not None for k in ["temperature_celsius", "humidity_percentage"]):
                # Si les données essentielles sont présentes, on les enregistre
                log_data_to_csv(data)
            else:
                # Si les données ne sont pas complètes ou la lecture a échoué
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Data retrieval failed, skipping log entry.")
            
            # If we have valid data, log and write the output files; otherwise skip
            if data and all(data.get(k) is not None for k in ["temperature_celsius", "humidity_percentage", "timestamp"]):
                # Write crop files (safe defaults if keys missing)
                try:
                    files = {
                        "outputmint.txt": "mint",
                        "outputonions.txt": "onions",
                        "outputtomatoe.txt": "tomatoe"
                    }

                    for filename, crop_name in files.items():
                        try:
                            with open(filename, "w", encoding="utf-8") as f:
                                temp_val = data.get('temperature_celsius', '')
                                hum_val = data.get('humidity_percentage', '')
                                ts = data.get('timestamp')
                                season_str = season(ts) if ts else ''

                                f.write(f"{crop_name}\n")                             # 1. Crop name
                                f.write(f"{season_str}\n")                              # 2. Season
                                f.write(f"{temp_val}\n")                                # 3. Temperature (1st)
                                f.write(f"{temp_val}\n")                                # 4. Temperature (2nd)
                                f.write(f"{hum_val}\n")                                 # 5. Humidity (1st)
                                f.write(f"{hum_val}\n")                                 # 6. Humidity (2nd)
                                f.write("1250\n")                                      # 7. Fixed value
                        except Exception as e:
                            print(f"[ERROR] Could not write {filename}: {e}")
                except Exception as e:
                    print(f"[ERROR] Writing output files failed: {e}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Skipping crop file write because data was incomplete.")

            time.sleep(10) # Attendre 10 secondes entre chaque requête

    except KeyboardInterrupt:
        print("\nStopped by user. Data logging complete.")
