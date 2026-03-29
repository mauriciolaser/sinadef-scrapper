import pandas as pd
import os

INPUT_FILE = "sinadef.csv"
HISTORIC_OUTPUT_FILE = "historic.csv"
OUTPUT_2026_FILE = "2026.csv"
CHUNK_SIZE = 200000  # puedes subirlo si tienes RAM suficiente

def procesar():
    first_historic_chunk = True
    first_2026_chunk = True

    # Limpia salidas previas para evitar duplicados entre ejecuciones
    for output_file in (HISTORIC_OUTPUT_FILE, OUTPUT_2026_FILE):
        if os.path.exists(output_file):
            os.remove(output_file)

    for chunk in pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE, dtype=str):
        # Normalizar texto (por seguridad)
        chunk["MUERTE_VIOLENTA"] = chunk["MUERTE_VIOLENTA"].str.strip().str.upper()
        chunk["ANIO"] = chunk["ANIO"].str.strip()

        # Filtrar homicidios
        homicidios = chunk[chunk["MUERTE_VIOLENTA"] == "HOMICIDIO"]

        if not homicidios.empty:
            homicidios.to_csv(
                HISTORIC_OUTPUT_FILE,
                mode="a",
                index=False,
                header=first_historic_chunk
            )
            first_historic_chunk = False

            # Export adicional: solo homicidios del año 2026
            homicidios_2026 = homicidios[homicidios["ANIO"] == "2026"]
            if not homicidios_2026.empty:
                homicidios_2026.to_csv(
                    OUTPUT_2026_FILE,
                    mode="a",
                    index=False,
                    header=first_2026_chunk
                )
                first_2026_chunk = False

    print("OK historic.csv generado con homicidios (todos los anios)")
    print("OK 2026.csv generado con homicidios del anio 2026")

if __name__ == "__main__":
    procesar()
