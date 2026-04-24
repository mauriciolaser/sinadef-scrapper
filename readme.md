# SINADEF Scrapper

## Qué hace `script.py`
- Lee `sinadef.csv` en streaming (fila a fila) para ahorrar RAM.
- Genera `historic.csv` con todos los registros donde `MUERTE_VIOLENTA == HOMICIDIO`.
- Genera `2026.csv` con los homicidios donde `ANIO == 2026`.
- Genera `2026.json` con los homicidios del anio 2026 en formato JSON.
- En cada ejecución elimina los CSV de salida previos para evitar duplicados.
- Limpia bytes `NULL` y detecta cabecera/delimitador de forma robusta.
- Calcula un resumen diario por `FECHA` con homicidios del día más reciente y cambio vs. el día anterior.
- Guarda un estado de la ejecución previa en `summary_state.json` para reportar variaciones de totales entre corridas (pueden subir o bajar).
- Al terminar correctamente, intenta enviar un correo desde `no-reply@incaslop.online` a `mauricio@castrovaldez.com` usando `sendmail`.

## Archivos del proyecto
- `script.py`: procesamiento principal del CSV y envío del resumen por correo.
- `passenger_wsgi.py`: app mínima para que cPanel monte Python App.
- `requirements.txt`: archivo intencionalmente vacío de dependencias externas; el proyecto usa librerías estándar.
- `data.md`: guía explícita de la estructura real de `2026.csv` y tipos de datos esperados.
- `summary_state.json`: estado mínimo de la corrida anterior para calcular variaciones.

## Plan de despliegue en Namecheap Shared (Python 3.6.15)

### 1. Preparar estructura en hosting
1. En cPanel, crea una carpeta del proyecto, por ejemplo `~/sinadef_scrapper/`.
2. Sube `script.py` y `sinadef.csv` a esa carpeta (File Manager o SFTP).

### 2. Crear app Python 3.6.15
1. En cPanel abre `Setup Python App`.
2. Crea una app nueva con versión `Python 3.6.15`.
3. Define `Application root` como `sinadef_scrapper`.
4. Crea/activa el virtualenv que genera cPanel.

### 2.1 Cómo llenar los campos de Setup Python App
Usa estos valores:

1. `Python version`:
`3.6.15`

2. `Application root`:
`sinadef_scrapper` o `sinadef-scrapper` (debe coincidir exactamente con la carpeta real en `/home/TU_USUARIO/`)

3. `Application URL`:
puedes usar una ruta simple como `tudominio.com/sinadef` (solo para que cPanel monte la app; el proceso real corre por cron)

4. `Application startup file`:
`passenger_wsgi.py`

5. `Application Entry point`:
`application`

Archivo requerido para que esto funcione:
- [passenger_wsgi.py](c:\Experimental\sinadef-scrapper\passenger_wsgi.py)

Si aún no lo subiste al hosting, súbelo junto con `script.py`.

### 3. Instalar dependencias compatibles con 3.6.15
1. Abre Terminal en cPanel o conéctate por SSH.
2. Ubica tu usuario y la ruta del virtualenv:

```bash
whoami
ls -la /home/$(whoami)/virtualenv
```

3. Normalmente cPanel crea algo como:
   `/home/vallhzty/virtualenv/sinadef_scrapper/3.6/`

4. Activa el entorno virtual (forma detallada):

```bash
source /home/vallhzty/virtualenv/sinadef_scrapper/3.6/bin/activate
```

5. Verifica que quedó activo:

```bash
echo "$VIRTUAL_ENV"
which python
python --version
```

Debes ver:
- `VIRTUAL_ENV` apuntando al path `.../virtualenv/.../3.6`
- `python` apuntando al `.../bin/python` del virtualenv
- versión `Python 3.6.15`

6. Este proyecto ahora usa solo librerías estándar de Python, así que no requiere instalar paquetes externos.

7. Aun así puedes correr el comando estándar para dejar el entorno consistente:

```bash
pip install -r requirements.txt
```

Ese comando no instalará paquetes adicionales porque [requirements.txt](c:\Code\Experimental\sinadef-scrapper\requirements.txt) no lista dependencias externas.

8. Sal del entorno cuando termines:

```bash
deactivate
```

### 4. Probar ejecución manual
Desde la carpeta del proyecto:

```bash
python script.py
```

Verifica que se creen:
- `historic.csv`
- `2026.csv`
- `2026.json`

Y revisa en consola:
- resumen de homicidios procesados
- fecha más reciente detectada
- cambio respecto al día anterior
- estado del envío del correo

### 5. Automatizar ejecución (Cron Jobs)
1. En cPanel abre `Cron Jobs`.
2. Sube también `run_cron.sh` al proyecto y marca permisos ejecutables en hosting:

```bash
chmod +x /home/vallhzty/sinadef_scrapper/run_cron.sh
```

3. Configura la frecuencia (ejemplo diario 2:00 AM).
4. Usa este comando:

```bash
/bin/bash -lc '/home/TU_USUARIO/sinadef_scrapper/run_cron.sh' >> /home/TU_USUARIO/sinadef_scrapper/cron.log 2>&1
```

Qué hace `run_cron.sh`:
- Activa el virtualenv de Python 3.6.15.
- Descarga con `curl` en modo robusto para archivos grandes (`--retry`, `--continue-at -`, `--max-time` amplio).
- Reanuda una descarga parcial si quedó `sinadef.tmp.csv` de un intento fallido.
- Valida tamaño mínimo y cabecera del CSV antes de reemplazar `sinadef.csv`.
- Ejecuta `script.py` para regenerar `historic.csv`, `2026.csv` y `2026.json`.
- Si falla cualquier etapa, envía correo de error a `mauricio@castrovaldez.com` con etapa y código de salida.

### 5.1 Recomendaciones por tamaño (600 MB aprox)
1. Programa el cron en horario de baja carga (madrugada).
2. Asegura espacio libre antes de correr: al menos 2.5 GB.
3. Considera que durante la ejecución conviven:
- `sinadef.tmp.csv` (~600 MB)
- `sinadef.csv` (~600 MB)
- `historic.csv` y `2026.csv` (salidas)
4. Si el hosting es justo de disco, elimina `sinadef.csv` viejo antes de descargar:

```bash
rm -f sinadef.csv
```

Esto reduce pico de uso, pero deja una ventana sin archivo si la descarga falla.

### 6. Validación y operación
1. Revisa `cron.log` después del primer disparo.
2. Confirma fecha de modificación y tamaño de `historic.csv`, `2026.csv` y `2026.json`.
3. Confirma que el correo llegue a `mauricio@castrovaldez.com`.
4. Si el correo no sale, revisa si el hosting expone `sendmail` y si permite usar `no-reply@incaslop.online` como remitente.
5. Si `sinadef.csv` se reemplaza periódicamente, el script regenerará las salidas en limpio.

## Notificación por correo

Cuando el script termina correctamente:

- arma un resumen corto del CRON job
- reporta homicidios históricos y homicidios 2026 con variación vs la corrida anterior (ejemplo `13087 (+2)` o `13087 (-2)`)
- reporta homicidios de hoy y de ayer según fecha calendario del servidor
- reporta variación hoy vs ayer
- reporta también la última fecha con data disponible en el CSV
- intenta enviar ese resumen por correo usando `sendmail`

Importante:

- si `script.py` termina bien, envía correo de resumen (éxito)
- si falla cualquier etapa del CRON (descarga, validación, reemplazo o ejecución), `run_cron.sh` envía correo de error
- si falla el correo, el CRON mantiene el registro del error en `cron.log`
- el remitente configurado es `no-reply@incaslop.online`
- el destinatario configurado es `mauricio@castrovaldez.com`

## Guía de datos

La estructura del archivo generado `2026.csv` está documentada en [data.md](c:\Code\Experimental\sinadef-scrapper\data.md).

Ahí encontrarás:

- columnas principales
- tipos sugeridos
- ejemplos reales del dataset
- notas para parseo y análisis

## Checklist de compatibilidad (Python 3.6.15)
- `script.py` usa sintaxis compatible con 3.6.
- No depende de `pandas` ni `numpy`.
- El procesamiento es streaming fila a fila (muy bajo consumo de RAM para archivos grandes).
