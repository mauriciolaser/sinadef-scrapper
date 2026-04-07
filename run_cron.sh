#!/usr/bin/env bash
# run_cron.sh — Descarga diaria del CSV de SINADEF y procesamiento de homicidios
#
# RESILIENCIA DE LA DESCARGA
# ──────────────────────────
# El archivo fuente pesa ~600MB y se descarga desde un servidor del MINSA que
# no soporta rangos HTTP (Accept-Ranges). Esto causaba exit code 33 de curl
# cuando quedaba un archivo temporal de una ejecucion anterior y se intentaba
# reanudar con --continue-at -.
#
# Soluciones implementadas:
#
#   1. Lockfile con PID (cron.lock)
#      Evita que dos instancias corran simultaneamente. Si el cron del dia
#      anterior sigue corriendo cuando arranca el siguiente, el nuevo aborta
#      limpiamente sin disparar la alarma de error. Si el proceso ya murio
#      (crash, reinicio del servidor), el lock obsoleto se detecta via
#      kill -0 <PID> y se limpia automaticamente.
#
#   2. Loop de reintentos manuales (DOWNLOAD_MAX_ATTEMPTS=5)
#      Reemplaza el --retry nativo de curl, que solo reintenta errores de
#      conexion y no cubre casos como --speed-limit. El loop bash reintenta
#      ante cualquier fallo de curl o archivo demasiado pequeno. Entre cada
#      intento espera DOWNLOAD_RETRY_WAIT=120 segundos. Cada intento borra
#      el archivo temporal antes de empezar (evita el exit 33).
#
#   3. Validacion de tamano dentro del loop
#      curl puede retornar exit 0 si el servidor responde con una pagina de
#      error HTML (HTTP 200 con contenido invalido). Se verifica que el
#      archivo descargado supere MIN_FILE_BYTES antes de considerarlo valido.
#
#   4. Sin --continue-at -
#      Eliminado porque el servidor MINSA no soporta rangos. Su presencia
#      causaba el exit 33 que disparaba falsas alarmas de fallo.
#
# VARIABLES DE ENTORNO (todas tienen valor por defecto)
# ──────────────────────────────────────────────────────
#   PROJECT_DIR          Directorio raiz del proyecto
#   VENV_ACTIVATE        Path al activate del virtualenv Python
#   DOWNLOAD_URL         URL del CSV de SINADEF
#   TMP_FILE             Archivo temporal durante la descarga
#   TARGET_FILE          CSV de produccion (reemplazado atomicamente via mv)
#   LOG_FILE             Log de ejecucion
#   LOCK_FILE            Lockfile con PID del proceso en curso
#   MAIL_FROM            Remitente del correo de error
#   MAIL_TO              Destinatario del correo de error
#   MAIL_SUBJECT_ERROR   Asunto del correo de error
#   MIN_FILE_BYTES       Tamano minimo aceptable del CSV descargado (bytes)
#   DOWNLOAD_MAX_ATTEMPTS Numero maximo de intentos de descarga
#   DOWNLOAD_RETRY_WAIT  Segundos de espera entre intentos de descarga
#
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/vallhzty/sinadef_scrapper}"
VENV_ACTIVATE="${VENV_ACTIVATE:-/home/vallhzty/virtualenv/sinadef_scrapper/3.6/bin/activate}"
DOWNLOAD_URL="${DOWNLOAD_URL:-https://files.minsa.gob.pe/s/a6Hmynsenb7Px2y/download}"
TMP_FILE="${TMP_FILE:-$PROJECT_DIR/sinadef.tmp.csv}"
TARGET_FILE="${TARGET_FILE:-$PROJECT_DIR/sinadef.csv}"
LOG_FILE="${LOG_FILE:-$PROJECT_DIR/cron.log}"
LOCK_FILE="${LOCK_FILE:-$PROJECT_DIR/cron.lock}"
MAIL_FROM="${MAIL_FROM:-no-reply@incaslop.online}"
MAIL_TO="${MAIL_TO:-mauricio@castrovaldez.com}"
MAIL_SUBJECT_ERROR="${MAIL_SUBJECT_ERROR:-SINADEF CRON ERROR}"
MIN_FILE_BYTES="${MIN_FILE_BYTES:-1000000}"
DOWNLOAD_MAX_ATTEMPTS="${DOWNLOAD_MAX_ATTEMPTS:-5}"
DOWNLOAD_RETRY_WAIT="${DOWNLOAD_RETRY_WAIT:-120}"

CURRENT_STAGE="init"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

send_failure_email() {
  local exit_code="$1"
  local host_name
  host_name="$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "unknown-host")"
  local sendmail_cmd=""

  if [ -x "/usr/sbin/sendmail" ]; then
    sendmail_cmd="/usr/sbin/sendmail"
  elif [ -x "/usr/lib/sendmail" ]; then
    sendmail_cmd="/usr/lib/sendmail"
  elif command -v sendmail >/dev/null 2>&1; then
    sendmail_cmd="sendmail"
  fi

  if [ -z "$sendmail_cmd" ]; then
    echo "[WARN] $(timestamp) No se encontro sendmail para reportar error" >&2
    return 0
  fi

  {
    echo "Subject: ${MAIL_SUBJECT_ERROR} (exit ${exit_code})"
    echo "From: ${MAIL_FROM}"
    echo "To: ${MAIL_TO}"
    echo "Reply-To: ${MAIL_FROM}"
    echo
    echo "El CRON de SINADEF fallo."
    echo
    echo "Fecha UTC: $(timestamp)"
    echo "Host: ${host_name}"
    echo "Stage: ${CURRENT_STAGE}"
    echo "Exit code: ${exit_code}"
    echo "Project dir: ${PROJECT_DIR}"
    echo "Download URL: ${DOWNLOAD_URL}"
    if [ -f "$LOG_FILE" ]; then
      echo
      echo "Ultimas lineas de ${LOG_FILE}:"
      tail -n 80 "$LOG_FILE" 2>/dev/null || true
    fi
  } | "$sendmail_cmd" -t -i >/dev/null 2>&1 || true
}

on_error() {
  local exit_code="$?"
  echo "[ERROR] $(timestamp) fallo en etapa '${CURRENT_STAGE}' con codigo ${exit_code}" >&2
  send_failure_email "$exit_code"
  exit "$exit_code"
}

trap on_error ERR

echo "[INFO] $(timestamp) inicio de ejecucion"

# ── Lockfile: evita instancias simultaneas ────────────────────────────────────
CURRENT_STAGE="acquire_lock"
if [ -e "$LOCK_FILE" ]; then
  lock_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  # Si el PID registrado ya no existe, el lock es obsoleto — lo limpiamos
  if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
    echo "[ERROR] $(timestamp) ya hay una instancia corriendo (PID ${lock_pid}), abortando" >&2
    # No disparar on_error: no es un fallo del cron, es una colision esperada
    exit 1
  else
    echo "[WARN] $(timestamp) lock obsoleto encontrado (PID ${lock_pid:-desconocido}), limpiando" >&2
    rm -f "$LOCK_FILE"
  fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# ── Activar entorno ───────────────────────────────────────────────────────────
CURRENT_STAGE="activate_venv"
source "$VENV_ACTIVATE"

CURRENT_STAGE="cd_project"
cd "$PROJECT_DIR"

# ── Descarga con reintentos manuales ─────────────────────────────────────────
CURRENT_STAGE="download_csv"
download_attempt=0
download_ok=false

while [ "$download_attempt" -lt "$DOWNLOAD_MAX_ATTEMPTS" ]; do
  download_attempt=$((download_attempt + 1))
  echo "[INFO] $(timestamp) descarga intento ${download_attempt}/${DOWNLOAD_MAX_ATTEMPTS}" >&2

  rm -f "$TMP_FILE"

  curl_exit=0
  curl -fL \
    --connect-timeout 90 \
    --max-time 21600 \
    --speed-time 300 \
    --speed-limit 1024 \
    "$DOWNLOAD_URL" \
    -o "$TMP_FILE" || curl_exit=$?

  if [ "$curl_exit" -eq 0 ]; then
    # Verificar que el archivo tiene contenido real (no una pagina de error HTML)
    tmp_size_bytes="$(wc -c < "$TMP_FILE" 2>/dev/null || echo 0)"
    if [ "$tmp_size_bytes" -ge "$MIN_FILE_BYTES" ]; then
      download_ok=true
      break
    else
      echo "[WARN] $(timestamp) descarga completa pero archivo muy pequeno (${tmp_size_bytes} bytes), reintentando" >&2
    fi
  else
    echo "[WARN] $(timestamp) curl fallo con codigo ${curl_exit} en intento ${download_attempt}/${DOWNLOAD_MAX_ATTEMPTS}" >&2
  fi

  rm -f "$TMP_FILE"

  if [ "$download_attempt" -lt "$DOWNLOAD_MAX_ATTEMPTS" ]; then
    echo "[INFO] $(timestamp) esperando ${DOWNLOAD_RETRY_WAIT}s antes del siguiente intento" >&2
    sleep "$DOWNLOAD_RETRY_WAIT"
  fi
done

if [ "$download_ok" != "true" ]; then
  echo "[ERROR] $(timestamp) descarga fallo tras ${DOWNLOAD_MAX_ATTEMPTS} intentos" >&2
  false
fi

# ── Validar contenido del CSV ─────────────────────────────────────────────────
CURRENT_STAGE="validate_csv_size"
tmp_size_bytes="$(wc -c < "$TMP_FILE")"
if [ "$tmp_size_bytes" -lt "$MIN_FILE_BYTES" ]; then
  echo "[ERROR] $(timestamp) tamano invalido (${tmp_size_bytes} bytes) para ${TMP_FILE}" >&2
  false
fi

CURRENT_STAGE="validate_csv_header"
header_sample="$(head -n 5 "$TMP_FILE" | tr '[:lower:]' '[:upper:]')"
if ! echo "$header_sample" | grep -q "MUERTE_VIOLENTA"; then
  echo "[ERROR] $(timestamp) cabecera invalida: falta MUERTE_VIOLENTA" >&2
  false
fi
if ! echo "$header_sample" | grep -q "ANIO"; then
  echo "[ERROR] $(timestamp) cabecera invalida: falta ANIO" >&2
  false
fi

# ── Reemplazar CSV de produccion ──────────────────────────────────────────────
CURRENT_STAGE="swap_csv"
mv -f "$TMP_FILE" "$TARGET_FILE"

# ── Ejecutar procesamiento ────────────────────────────────────────────────────
CURRENT_STAGE="run_python"
python -u script.py

CURRENT_STAGE="done"
echo "[INFO] $(timestamp) ejecucion finalizada correctamente"
