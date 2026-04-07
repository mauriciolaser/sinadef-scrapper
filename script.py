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
SUMMARY_STATE_FILE = "summary_state.json"
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


def _format_total_with_delta(current_value, delta_value):
    if delta_value is None:
        return "{0} (sin base previa)".format(current_value)
    return "{0} ({1})".format(current_value, _format_delta(delta_value))


def _safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def _load_previous_state():
    if not os.path.exists(SUMMARY_STATE_FILE):
        return {}
    try:
        with open(SUMMARY_STATE_FILE, "r", encoding="utf-8") as state_file:
            data = json.load(state_file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_current_state(summary):
    data = {
        "saved_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_rows": summary["total_rows"],
        "total_homicidios": summary["total_homicidios"],
        "total_homicidios_2026": summary["total_homicidios_2026"],
        "today": summary["today"],
        "today_count": summary["today_count"],
        "yesterday": summary["yesterday"],
        "yesterday_count": summary["yesterday_count"],
        "latest_date": summary["latest_date"],
        "latest_count": summary["latest_count"],
    }
    with open(SUMMARY_STATE_FILE, "w", encoding="utf-8") as state_file:
        json.dump(data, state_file, ensure_ascii=False, indent=2)


def _build_email_body(summary):
    today = summary["today"]
    yesterday = summary["yesterday"]
    total_hist = _format_total_with_delta(
        summary["total_homicidios"], summary["delta_total_homicidios"]
    )
    total_2026 = _format_total_with_delta(
        summary["total_homicidios_2026"], summary["delta_total_homicidios_2026"]
    )
    total_rows = _format_total_with_delta(summary["total_rows"], summary["delta_total_rows"])

    return "\n".join(
        (
            "El CRON job de SINADEF termino correctamente y regenero los archivos de salida.",
            "Resumen total:",
            "- Filas procesadas: {0}".format(total_rows),
            "- Homicidios historicos: {0}".format(total_hist),
            "- Homicidios 2026: {0}".format(total_2026),
            "Resumen diario:",
            "- Homicidios de hoy ({0}): {1}".format(today, summary["today_count"]),
            "- Homicidios de ayer ({0}): {1}".format(yesterday, summary["yesterday_count"]),
            "- Variacion hoy vs ayer: {0}".format(_format_delta(summary["today_vs_yesterday_delta"])),
            "Ultima fecha con data en el archivo: {0} ({1} homicidios)".format(
                summary["latest_date"] or "sin fecha",
                summary["latest_count"],
            ),
        )
    )


def _build_email_html(summary):
    today = summary["today"]
    yesterday = summary["yesterday"]
    total_hist = _format_total_with_delta(
        summary["total_homicidios"], summary["delta_total_homicidios"]
    )
    total_2026 = _format_total_with_delta(
        summary["total_homicidios_2026"], summary["delta_total_homicidios_2026"]
    )
    total_rows = _format_total_with_delta(summary["total_rows"], summary["delta_total_rows"])
    latest_date = summary["latest_date"] or "sin fecha"
    latest_count = summary["latest_count"]
    today_vs_yesterday_delta = _format_delta(summary["today_vs_yesterday_delta"])

    return """\
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SINADEF CRON OK</title>
</head>
<body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fb;padding:16px 8px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:720px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="background:#0f172a;color:#ffffff;padding:18px 20px;">
              <div style="font-size:18px;font-weight:700;line-height:1.3;">SINADEF - Resumen Diario</div>
              <div style="font-size:13px;opacity:0.9;margin-top:4px;">El CRON termino correctamente y regenero los archivos de salida.</div>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 20px 6px 20px;">
              <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:10px;">Resumen total</div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 20px 10px 20px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Filas procesadas</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{total_rows}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Homicidios historicos</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{total_hist}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Homicidios 2026</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{total_2026}</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 20px 6px 20px;">
              <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:10px;">Resumen diario</div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 20px 12px 20px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Homicidios de hoy ({today})</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{today_count}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Homicidios de ayer ({yesterday})</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{yesterday_count}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Variacion hoy vs ayer</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{today_vs_yesterday_delta}</td>
                </tr>
                <tr>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;color:#4b5563;">Ultima fecha con data</td>
                  <td style="padding:10px 12px;border:1px solid #e5e7eb;font-size:13px;font-weight:700;color:#111827;">{latest_date} ({latest_count})</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:10px 20px 18px 20px;font-size:12px;color:#6b7280;">
              Este correo se genero automaticamente por el CRON de SINADEF.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""".format(
        total_rows=total_rows,
        total_hist=total_hist,
        total_2026=total_2026,
        today=today,
        today_count=summary["today_count"],
        yesterday=yesterday,
        yesterday_count=summary["yesterday_count"],
        today_vs_yesterday_delta=today_vs_yesterday_delta,
        latest_date=latest_date,
        latest_count=latest_count,
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
    plain_body = _build_email_body(summary)
    html_body = _build_email_html(summary)

    message = EmailMessage()
    message["Subject"] = MAIL_SUBJECT
    message["From"] = MAIL_FROM
    message["To"] = MAIL_TO
    message["Reply-To"] = MAIL_FROM
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")

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
    previous_state = _load_previous_state()
    previous_total_rows = _safe_int(previous_state.get("total_rows"))
    previous_total_homicidios = _safe_int(previous_state.get("total_homicidios"))
    previous_total_homicidios_2026 = _safe_int(previous_state.get("total_homicidios_2026"))

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today_count = counts_by_date.get(today, 0)
    yesterday_count = counts_by_date.get(yesterday, 0)

    summary["today"] = today
    summary["yesterday"] = yesterday
    summary["today_count"] = today_count
    summary["yesterday_count"] = yesterday_count
    summary["today_vs_yesterday_delta"] = today_count - yesterday_count
    summary["delta_total_rows"] = (
        None if previous_total_rows is None else total_rows - previous_total_rows
    )
    summary["delta_total_homicidios"] = (
        None
        if previous_total_homicidios is None
        else total_homicidios - previous_total_homicidios
    )
    summary["delta_total_homicidios_2026"] = (
        None
        if previous_total_homicidios_2026 is None
        else total_homicidios_2026 - previous_total_homicidios_2026
    )

    _save_current_state(summary)

    print("OK historic.csv generado con homicidios (todos los anios): {0}".format(total_homicidios))
    print("OK 2026.csv generado con homicidios del anio 2026: {0}".format(total_homicidios_2026))
    print("OK 2026.json generado con homicidios del anio 2026: {0}".format(total_homicidios_2026))
    print(
        "OK comparativa historico: {0}".format(
            _format_total_with_delta(
                summary["total_homicidios"], summary["delta_total_homicidios"]
            )
        )
    )
    print(
        "OK comparativa 2026: {0}".format(
            _format_total_with_delta(
                summary["total_homicidios_2026"], summary["delta_total_homicidios_2026"]
            )
        )
    )
    print(
        "OK hoy ({0}): {1} | ayer ({2}): {3} | delta: {4}".format(
            summary["today"],
            summary["today_count"],
            summary["yesterday"],
            summary["yesterday_count"],
            _format_delta(summary["today_vs_yesterday_delta"]),
        )
    )
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
        plain_part = next(
            (p for p in email_message.walk() if p.get_content_type() == "text/plain"),
            None,
        )
        if plain_part is not None:
            print(plain_part.get_payload(decode=True).decode("utf-8", errors="replace").rstrip())
    except Exception as exc:
        print(
            "WARNING el CRON job termino, pero fallo el envio del correo: {0}".format(
                exc
            ),
            file=sys.stderr,
        )
        traceback.print_exc()
