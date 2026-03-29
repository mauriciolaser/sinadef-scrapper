import csv
import json
import os

INPUT_FILE = "sinadef.csv"
HISTORIC_OUTPUT_FILE = "historic.csv"
OUTPUT_2026_FILE = "2026.csv"
OUTPUT_2026_JSON_FILE = "2026.json"


def _build_index(header_row):
    index = {}
    for i, name in enumerate(header_row):
        key = (name or "").strip().upper()
        index[key] = i
    return index


def _parse_line(line, delimiter):
    return next(csv.reader([line], delimiter=delimiter))


def _find_header(cleaned_iter):
    required = ("MUERTE_VIOLENTA", "ANIO")
    for line in cleaned_iter:
        if not line.strip():
            continue
        for delimiter in (",", ";"):
            try:
                cols = _parse_line(line, delimiter)
            except Exception:
                continue
            index = _build_index(cols)
            if required[0] in index and required[1] in index:
                return cols, delimiter, index
    return None, None, None


def _row_to_obj(header, row):
    obj = {}
    for i, key in enumerate(header):
        value = row[i] if i < len(row) else ""
        obj[key] = value
    return obj

def procesar():
    # Limpia salidas previas para evitar duplicados entre ejecuciones
    for output_file in (HISTORIC_OUTPUT_FILE, OUTPUT_2026_FILE, OUTPUT_2026_JSON_FILE):
        if os.path.exists(output_file):
            os.remove(output_file)

    total_rows = 0
    total_homicidios = 0
    total_homicidios_2026 = 0

    # Lee en binario y limpia bytes nulos para evitar:
    # _csv.Error: line contains NULL byte
    with open(INPUT_FILE, "rb") as src:
        cleaned_lines = (
            line.replace(b"\x00", b"").decode("utf-8-sig", errors="replace")
            for line in src
        )
        header, delimiter, index = _find_header(cleaned_lines)
        if not header:
            raise ValueError(
                "No se encontro cabecera valida (MUERTE_VIOLENTA, ANIO) en sinadef.csv"
            )

        idx_mv = index["MUERTE_VIOLENTA"]
        idx_anio = index["ANIO"]

        with open(HISTORIC_OUTPUT_FILE, "w", newline="", encoding="utf-8") as out_hist:
            with open(OUTPUT_2026_FILE, "w", newline="", encoding="utf-8") as out_2026:
                with open(OUTPUT_2026_JSON_FILE, "w", encoding="utf-8") as out_2026_json:
                    writer_hist = csv.writer(out_hist)
                    writer_2026 = csv.writer(out_2026)
                    writer_hist.writerow(header)
                    writer_2026.writerow(header)

                    out_2026_json.write("[")
                    first_json_item = True

                    reader = csv.reader(cleaned_lines, delimiter=delimiter)
                    for row in reader:
                        total_rows += 1

                        # Evita fallos por filas truncadas o con columnas faltantes.
                        if len(row) < len(header):
                            row.extend([""] * (len(header) - len(row)))
                        elif len(row) > len(header):
                            row = row[:len(header)]

                        muerte_violenta = (row[idx_mv] or "").strip().upper()
                        if muerte_violenta != "HOMICIDIO":
                            continue

                        writer_hist.writerow(row)
                        total_homicidios += 1

                        if (row[idx_anio] or "").strip() == "2026":
                            writer_2026.writerow(row)
                            total_homicidios_2026 += 1

                            if not first_json_item:
                                out_2026_json.write(",")
                            obj = _row_to_obj(header, row)
                            out_2026_json.write(json.dumps(obj, ensure_ascii=False))
                            first_json_item = False

                        if total_rows % 500000 == 0:
                            print("Procesadas {0} filas...".format(total_rows))

                    out_2026_json.write("]")

    print("OK historic.csv generado con homicidios (todos los anios): {0}".format(total_homicidios))
    print("OK 2026.csv generado con homicidios del anio 2026: {0}".format(total_homicidios_2026))
    print("OK 2026.json generado con homicidios del anio 2026: {0}".format(total_homicidios_2026))

if __name__ == "__main__":
    procesar()
