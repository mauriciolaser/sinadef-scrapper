# Guía de datos de `2026.csv`

Este archivo describe la estructura real de [2026.csv](c:\Code\Experimental\sinadef-scrapper\2026.csv), que hoy contiene `487` filas y `36` columnas.

## Qué representa el archivo

`2026.csv` contiene registros de muertes violentas filtradas por el script con estas reglas:

- `ANIO == 2026`
- `MUERTE_VIOLENTA == HOMICIDIO`

Cada fila representa un caso individual.

## Reglas generales de tipado

- El archivo viene en CSV con encabezados en mayúsculas.
- Casi todo llega como texto, incluso los números.
- Los campos numéricos deben parsearse de forma explícita si se quieren usar como número.
- Muchos campos pueden venir como `SIN REGISTRO` o `IGNORADO`.
- Las causas médicas (`DEBIDO_CAUSA_*`) son texto libre y pueden variar mucho en redacción.
- Los códigos `CIEX` son texto corto, no siempre presentes.

## Campos principales

| Campo | Tipo sugerido | Qué contiene | Valores o ejemplos reales |
| --- | --- | --- | --- |
| `N` | `string` o `int` | Identificador del registro | `952344`, `952389` |
| `FECHA` | `date-string` (`YYYY-MM-DD`) | Fecha del fallecimiento | `2026-01-27`, `2026-03-24` |
| `ANIO` | `string` o `int` | Año del registro | siempre `2026` en este archivo |
| `MES` | `string` | Mes con cero a la izquierda | `01`, `02`, `03` |
| `MUERTE_VIOLENTA` | `string` | Tipo de muerte violenta | siempre `HOMICIDIO` en este archivo |
| `NECROPSIA` | `string` | Si hubo necropsia | `SI SE REALIZÓ NECROPSIA`, `NO SE REALIZÓ NECROPSIA` |
| `SEXO` | `string` | Sexo reportado | `MASCULINO`, `FEMENINO` |
| `TIEMPO_EDAD` | `string` | Unidad de la edad | siempre `AÑOS` en este archivo |
| `EDAD` | `string` o `int` | Edad de la persona | rango actual observado: `8` a `88` |
| `ESTADO_CIVIL` | `string` | Estado civil | `SOLTERO`, `CASADO`, `DIVORCIADO`, `VIUDO`, `SIN REGISTRO` |
| `NIVEL_DE_INSTRUCCION` | `string` | Nivel educativo | `SECUNDARIA COMPLETA`, `SECUNDARIA INCOMPLETA`, `PRIMARIA COMPLETA`, `IGNORADO` |
| `ETNIA` | `string` | Autoidentificación étnica | `MESTIZO`, `SIN CLASIFICACIÓN`, `QUECHUA`, `AFRO DESCENDIENTE` |

## Ubicación del fallecimiento

| Campo | Tipo sugerido | Qué contiene | Valores o ejemplos reales |
| --- | --- | --- | --- |
| `DEPARTAMENTO_FALLECIMIENTO` | `string` | Departamento donde ocurrió el fallecimiento | `LIMA`, `CALLAO`, `LA LIBERTAD`, `PIURA` |
| `PROVINCIA_FALLECIMIENTO` | `string` | Provincia del fallecimiento | `LIMA`, `CALLAO`, `HUAURA`, `SULLANA` |
| `DISTRITO_FALLECIMIENTO` | `string` | Distrito del fallecimiento | `CALLAO`, `COMAS`, `ATE`, `SAN JUAN DE LURIGANCHO` |
| `TIPO_LUGAR` | `string` | Tipo de lugar donde ocurrió | `VIA PUBLICA`, `EESS`, `OTRO`, `DOMICILIO`, `EN TRANSITO` |
| `INSTITUCION` | `string` | Institución asociada al lugar o atención | `SIN REGISTRO`, `MINSA`, `GOBIERNO REGIONAL`, `ESSALUD` |

Notas útiles:

- `EESS` parece referirse a establecimiento de salud.
- `VIA PUBLICA` y `EESS` son los tipos de lugar más comunes en este corte.

## Datos del domicilio

| Campo | Tipo sugerido | Qué contiene | Valores o ejemplos reales |
| --- | --- | --- | --- |
| `COD_UBIGEO_DOMICILIO` | `string` | Código geográfico del domicilio | `92-33-10-02-07-000` |
| `PAIS_DOMICILIO` | `string` | País del domicilio | `PERU`, `ECUADOR`, `VENEZUELA`, `COLOMBIA` |
| `DEPARTAMENTO_DOMICILIO` | `string` | Departamento del domicilio | `LIMA`, `CALLAO`, `LA LIBERTAD` |
| `PROVINCIA_DOMICILIO` | `string` | Provincia del domicilio | `LIMA`, `CALLAO`, `HUAURA`, `SULLANA` |
| `DISTRITO_DOMICILIO` | `string` | Distrito del domicilio | `CALLAO`, `ATE`, `VENTANILLA`, `TUMBES` |

## Clasificación del certificado y seguro

| Campo | Tipo sugerido | Qué contiene | Valores o ejemplos reales |
| --- | --- | --- | --- |
| `TIPO_CDEF` | `string` | Tipo de certificado de defunción | `CDEF GRAL EN LINEA`, `CDEF GRAL MANUAL` |
| `TIPO_SEGURO` | `string` | Tipo de seguro reportado | `SIS`, `IGNORADO`, `ESSALUD`, `USUARIO`, `SANIDAD PNP`, `OTROS` |

## Bloque de causas de muerte

El archivo tiene hasta 6 niveles de causa, y cada nivel viene en pareja:

- `DEBIDO_CAUSA_A` + `CAUSA_A_CIEX`
- `DEBIDO_CAUSA_B` + `CAUSA_B_CIEX`
- `DEBIDO_CAUSA_C` + `CAUSA_C_CIEX`
- `DEBIDO_CAUSA_D` + `CAUSA_D_CIEX`
- `DEBIDO_CAUSA_E` + `CAUSA_E_CIEX`
- `DEBIDO_CAUSA_F` + `CAUSA_F_CIEX`

### Tipado recomendado

- `DEBIDO_CAUSA_*`: `string`
- `CAUSA_*_CIEX`: `string`

### Qué pueden mostrar

| Campo | Tipo sugerido | Qué contiene | Ejemplos reales |
| --- | --- | --- | --- |
| `DEBIDO_CAUSA_A` | `string` | Causa principal o inmediata reportada | `SHOCK HIPOVOLEMICO`, `LACERACIÓN ENCEFÁLICA` |
| `CAUSA_A_CIEX` | `string` | Código CIEX de la causa A | `R571`, `S272`, `SIN REGISTRO` |
| `DEBIDO_CAUSA_B` | `string` | Causa adicional o intermedia | `LACERACION PULMONAR`, `HERIDA PENETRANTE POR PROYECTIL DE ARMA DE FUEGO EN CABEZA` |
| `CAUSA_B_CIEX` | `string` | Código CIEX de la causa B | `S318`, `S254`, `SIN REGISTRO` |
| `DEBIDO_CAUSA_C` | `string` | Causa adicional o mecanismo relacionado | `DISPARO DE ARMA CORTA`, `AGRESION POR TERCERO CON ARMA BLANCA`, `SIN REGISTRO` |
| `CAUSA_C_CIEX` | `string` | Código CIEX de la causa C | `X950`, `W268`, `SIN REGISTRO` |
| `DEBIDO_CAUSA_D` | `string` | Causa adicional de menor frecuencia | `AGRESION CON DISPARO DE ARMA DE FUEGO`, `SIN REGISTRO` |
| `CAUSA_D_CIEX` | `string` | Código CIEX de la causa D | `X959`, `W349`, `SIN REGISTRO` |
| `DEBIDO_CAUSA_E` | `string` | Causa adicional rara | `ESTADO DE PUTREFACCION MODERADA`, `SIN REGISTRO` |
| `CAUSA_E_CIEX` | `string` | Código CIEX de la causa E | casi siempre `SIN REGISTRO` |
| `DEBIDO_CAUSA_F` | `string` | Último nivel de causa | casi siempre `SIN REGISTRO` |
| `CAUSA_F_CIEX` | `string` | Código CIEX de la causa F | casi siempre `SIN REGISTRO` |

## Valores frecuentes observados en este corte

- `SEXO`: predominan `MASCULINO` sobre `FEMENINO`.
- `TIPO_CDEF`: casi todos los casos son `CDEF GRAL EN LINEA`.
- `TIPO_SEGURO`: predominan `SIS` e `IGNORADO`.
- `TIPO_LUGAR`: predominan `VIA PUBLICA` y `EESS`.
- `INSTITUCION`: muy frecuente `SIN REGISTRO`.
- `NECROPSIA`: casi todos los registros indican `SI SE REALIZÓ NECROPSIA`.
- `DEPARTAMENTO_FALLECIMIENTO`: `LIMA` concentra la mayor cantidad de casos en este archivo.

## Recomendaciones para usar esta data

- Parsear `FECHA` como fecha real antes de hacer agregaciones diarias.
- Parsear `EDAD` como entero solo si el valor viene limpio.
- Tratar `SIN REGISTRO` e `IGNORADO` como categorías explícitas, no como nulos automáticos.
- No asumir que las columnas `CAUSA_*_CIEX` siempre tienen código válido.
- No asumir que las causas médicas tienen vocabulario normalizado; son texto libre.
- Si se hacen dashboards o métricas, conviene agrupar ubicación, perfil demográfico y causa en bloques separados.
