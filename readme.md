# SINADEF Scrapper

## Qué hace `script.py`
- Lee `sinadef.csv` por chunks para ahorrar RAM.
- Genera `historic.csv` con todos los registros donde `MUERTE_VIOLENTA == HOMICIDIO`.
- Genera `2026.csv` con los homicidios donde `ANIO == 2026`.
- En cada ejecución elimina los CSV de salida previos para evitar duplicados.

## Plan de despliegue en Namecheap Shared (Python 3.6.15)

### 1. Preparar estructura en hosting
1. En cPanel, crea una carpeta del proyecto, por ejemplo `~/sinadef-scrapper/`.
2. Sube `script.py` y `sinadef.csv` a esa carpeta (File Manager o SFTP).

### 2. Crear app Python 3.6.15
1. En cPanel abre `Setup Python App`.
2. Crea una app nueva con versión `Python 3.6.15`.
3. Define `Application root` como `sinadef-scrapper`.
4. Crea/activa el virtualenv que genera cPanel.

### 3. Instalar dependencias compatibles con 3.6.15
1. Abre Terminal en cPanel o conéctate por SSH.
2. Activa el entorno virtual de la app.
3. Instala versiones que sí soportan Python 3.6:

```bash
pip install "numpy==1.19.5" "pandas==1.1.5"
```

Nota: pandas modernos ya no soportan Python 3.6, por eso se fijan esas versiones.

### 4. Probar ejecución manual
Desde la carpeta del proyecto:

```bash
python script.py
```

Verifica que se creen:
- `historic.csv`
- `2026.csv`

### 5. Automatizar ejecución (Cron Jobs)
1. En cPanel abre `Cron Jobs`.
2. Configura la frecuencia (ejemplo diario 2:00 AM).
3. Usa un comando como este (ajustando rutas reales de tu cuenta):

```bash
/home/TU_USUARIO/virtualenv/sinadef-scrapper/3.6/bin/python /home/TU_USUARIO/sinadef-scrapper/script.py >> /home/TU_USUARIO/sinadef-scrapper/cron.log 2>&1
```

### 6. Validación y operación
1. Revisa `cron.log` después del primer disparo.
2. Confirma fecha de modificación y tamaño de `historic.csv` y `2026.csv`.
3. Si `sinadef.csv` se reemplaza periódicamente, el script regenerará ambas salidas en limpio.

## Checklist de compatibilidad (Python 3.6.15)
- `script.py` usa sintaxis compatible con 3.6.
- `pandas==1.1.5` y `numpy==1.19.5` compatibles con 3.6.
- La estrategia por chunks reduce riesgo de memoria en shared hosting.
