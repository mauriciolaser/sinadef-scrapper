import pandas as pd

INPUT_FILE = "sinadef.csv"
OUTPUT_FILE = "export.csv"
CHUNK_SIZE = 200000  # puedes subirlo si tienes RAM suficiente

def procesar():
    first_chunk = True

    for chunk in pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE, dtype=str):
        # Normalizar texto (por seguridad)
        chunk["MUERTE_VIOLENTA"] = chunk["MUERTE_VIOLENTA"].str.strip().str.upper()

        # Filtrar homicidios
        filtered = chunk[chunk["MUERTE_VIOLENTA"] == "HOMICIDIO"]

        if not filtered.empty:
            filtered.to_csv(
                OUTPUT_FILE,
                mode="a",
                index=False,
                header=first_chunk
            )
            first_chunk = False

    print("✔ export.csv generado con homicidios")

if __name__ == "__main__":
    procesar()