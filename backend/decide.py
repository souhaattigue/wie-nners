import pandas as pd
import joblib
import numpy as np  # <-- Added this import for saving

# --- 1. Define Column Names ---
# This list MUST be in the exact order of the columns in your DATA.txt file
column_names = [
    'Culture',
    'Saison',
    'Temperature_Air_°C',
    'Temperature_Sol_°C',
    'Humidite_Air_%',
    'Humidite_Sol_%',
    'Capteur_Humidite_Sol_ADC'
]
for culture in ['tomatoe', 'onions', 'mint']:  # Example cultures
    # --- 2. Define Filenames ---
    model_filename = "ml.pkl"
    data_filename = "DATA"+culture+".txt"
    output_filename = "output"+culture+".txt"  # <-- Your new output file

    try:
        # --- 3. Load the Trained Model ---
        loaded_pipeline = joblib.load(model_filename)
        print(f"Successfully loaded model from '{model_filename}'")
        
        # --- 4. Load the New Data ---
        new_data = pd.read_csv(data_filename, header=None, names=column_names)
        print(f"\nLoaded {new_data.shape[0]} new data points from '{data_filename}'.")
        
        # --- 5. Make Predictions ---
        # This creates a numpy array (e.g., [0, 1, 0, 1])
        predictions = loaded_pipeline.predict(new_data)
        
        print("\n--- PREDICTIONS (0 = NO, 1 = YES) ---")
        print(predictions)

        # --- 6. Write Predictions to File --- (This is the new part)
        # We use np.savetxt to save the 'predictions' array to a text file.
        # fmt='%d' saves the numbers as integers (0 or 1), one on each line.
        np.savetxt(output_filename, predictions, fmt='%d')
        
        print(f"\nSuccessfully wrote predictions to '{output_filename}'.")

    except FileNotFoundError as e:
        print(f"ERROR: File not found.")
        print(f"Details: {e}")
        print("Please make sure 'ml.pkl' and 'DATA.txt' are in the same directory.")
    except Exception as e:
        print(f"An error occurred: {e}")