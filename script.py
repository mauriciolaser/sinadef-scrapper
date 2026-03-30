import csv
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from email.message import EmailMessage

INPUT_FILE = "sinadef.csv"
HISTORIC_OUTPUT_FILE = "historic.csv"
OUTPUT_2026_FILE = "2026.csv"
OUTPUT_2026_JSON_FILE = "2026.json"
MAIL_FROM = "no-reply@incaslop.online"
MAIL_TO = "mauricio@castrovaldez.com"
MAIL_SUBJECT = "SINADEF CRON OK - resumen diario"
SENDMAIL_CANDIDATES = (
    "/usr/sbin/sendmail",
    "/usr/lib/sendmail",
    "sendmail",
)


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


def _build_summary(total_rows, total_homicidios, total_homicidios_2026, counts_by_date):
    latest_date = None
    latest_count = 0
    previous_date = None
    previous_count = 0

    if counts_by_date:
        latest_date = max(counts_by_date)
        latest_count = counts_by_date[latest_date]
        previous_date = (
            datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=1)
        ).strftime("%Y-%m-%d")
        previous_count = counts_by_date.get(previous_date, 0)

    return {
        "total_rows": total_rows,
        "total_homicidios": total_homicidios,
        "total_homicidios_2026": total_homicidios_2026,
        "latest_date": latest_date,
        "latest_count": latest_count,
        "previous_date": previous_date,
        "previous_count": previous_count,
        "delta": latest_count - previous_count,
    }


def _format_delta(delta):
    if delta > 0:
        return "+{0}".format(delta)
    return str(delta)


def _build_email_body(summary):
    latest_date = summary["latest_date"] or "sin fecha"
    previous_date = summary["previous_date"] or "sin fecha anterior"

    return "\n".join(
        (
            "El CRON job de SINADEF termino correctamente y regenero los archivos de salida.",
            "Resumen: {0} filas procesadas, {1} homicidios historicos, {2} homicidios en 2026.".format(
                summary["total_rows"],
                summary["total_homicidios"],
                summary["total_homicidios_2026"],
            ),
            "Homicidios del {0}: {1}".format(latest_date, summary["latest_count"]),
            "Cambio vs {0}: {1}".format(
                previous_date,
                _format_delta(summary["delta"]),
            ),
        )
    )


def _sendmail_command():
    for candidate in SENDMAIL_CANDIDATES:
        if os.path.isabs(candidate):
            if os.path.exists(candidate):
                return [candidate, "-t", "-i"]
        else:
            return [candidate, "-t", "-i"]
    raise FileNotFoundError("No se encontro sendmail en el hosting")


def enviar_correo_resumen(summary):
    message = EmailMessage()
    message["Subject"] = MAIL_SUBJECT
    message["From"] = MAIL_FROM
    message["To"] = MAIL_TO
    message["Reply-To"] = MAIL_FROM
    message.set_content(_build_email_body(summary))

    sendmail_command = _sendmail_command()
    process = subprocess.Popen(sendmail_command, stdin=subprocess.PIPE)
    process.communicate(message.as_bytes())
    if process.returncode != 0:
        raise RuntimeError(
            "sendmail termino con codigo de salida {0}".format(process.returncode)
        )
    return message


def procesar():
    # Limpia salidas previas para evitar duplicados entre ejecuciones
    for output_file in (HISTORIC_OUTPUT_FILE, OUTPUT_2026_FILE, OUTPUT_2026_JSON_FILE):
        if os.path.exists(output_file):
            os.remove(output_file)

    total_rows = 0
    total_homicidios = 0
    total_homicidios_2026 = 0
    counts_by_date = {}

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
        idx_fecha = index.get("FECHA")

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
                        if idx_fecha is not None:
                            fecha = (row[idx_fecha] or "").strip()
                            if fecha:
                                counts_by_date[fecha] = counts_by_date.get(fecha, 0) + 1

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

    summary = _build_summary(
        total_rows, total_homicidios, total_homicidios_2026, counts_by_date
    )
    print("OK historic.csv generado con homicidios (todos los anios): {0}".format(total_homicidios))
    print("OK 2026.csv generado con homicidios del anio 2026: {0}".format(total_homicidios_2026))
    print("OK 2026.json generado con homicidios del anio 2026: {0}".format(total_homicidios_2026))
    if summary["latest_date"]:
        print(
            "OK resumen diario: {0} homicidios el {1} ({2} vs {3})".format(
                summary["latest_count"],
                summary["latest_date"],
                _format_delta(summary["delta"]),
                summary["previous_date"],
            )
        )
    else:
        print("OK resumen diario: no se encontraron fechas de homicidios para reportar")
    return summary

if __name__ == "__main__":
    result = procesar()
    try:
        email_message = enviar_correo_resumen(result)
        print("OK correo enviado a {0} desde {1}".format(MAIL_TO, MAIL_FROM))
        print(email_message.get_content().rstrip())
    except Exception as exc:
        print(
            "WARNING el CRON job termino, pero fallo el envio del correo: {0}".format(
                exc
            ),
            file=sys.stderr,
        )
        traceback.print_exc()
