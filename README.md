# Sistema experto de recomendación de espacios — 

El sistema recibe una actividad y recomienda espacios según lo que se necesita.
Compara la cantidad de personas, el horario, los equipos, la accesibilidad,
la privacidad y el permiso para mover mesas y sillas.


```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run interfaz.py
```

## Archivos

| Archivo | Para qué sirve |
| --- | --- |
| `cargar_datos.py` | Lee y valida los CSV; une franjas libres contiguas |
| `motor.py` | Hechos, 24 reglas, conclusiones y traza de Experta |
| `interfaz.py` | Formulario y resultados de Streamlit |
| `app.py` | Entrada alternativa a la misma pantalla, útil para la entrega y Cloud |
| `demostracion.py` | 12 ejemplos reproducibles |
| `requerimientos.txt` | Bibliotecas con versiones fijadas |
| `datos/espacios.csv` | Características simuladas de los espacios |
| `datos/horarios.csv` | Franjas libres simuladas |

## Qué guarda cada CSV

`datos/espacios.csv` contiene los 10 espacios: seis aulas, tres salas y un auditorio.

| Columna | Qué significa | Ejemplo |
| --- | --- | --- |
| `id_espacio` | Código único | A101 |
| `nombre` | Nombre que aparece en la pantalla | Aula 101 |
| `tipo` | Aula, sala o auditorio | aula |
| `piso` | Número de piso; 0 es planta baja | 1 |
| `capacidad` | Cantidad máxima de personas | 30 |
| `reconfigurable` | Se permite mover mesas y sillas | si |
| `pantalla` | Tiene TV para mostrar contenido | si |
| `camara` | Tiene cámara declarada | no |
| `amplificacion_voz` | Tiene un sistema para que se escuche a quien habla | no |
| `wifi` | Tiene WiFi; en este ejemplo es `si` en todo el edificio | si |
| `ruta_accesible` | Hay una ruta accesible confirmada | si / no / desconocida |
| `privacidad` | Nivel declarado del espacio | baja / media / alta |
| `origen` | Procedencia de los datos | simulado |



`datos/horarios.csv` contiene 25 **franjas libres**, con estas columnas:

| Columna | Ejemplo |
| --- | --- |
| `id_espacio` | A101 |
| `fecha` | 2026-10-22 |
| `hora_inicio` | 08:00 |
| `hora_fin` | 12:00 |
| `origen` | simulado |


## Cómo decide

- **Obligatorio:** si falta, se descarta el espacio. No se compensa con preferencias.
- **Preferido:** si falta, se agrega una observación y el espacio sigue siendo viable.
- **Sin pedirlo:** no agrega una condición a la búsqueda.

La actividad se escribe libremente, por ejemplo “Clase”, “Examen” o “Reunión de equipo”.
Es una descripción: no agrega equipos ni condiciones automáticamente.

La privacidad se interpreta como mínimo: alta cumple un pedido de media; baja no.
Si se pide accesibilidad, la ruta debe estar confirmada: `desconocida` no alcanza.

Los resultados pueden ser:

| Resultado | Qué significa |
| --- | --- |
| RECOMENDADA | Cumple lo obligatorio y no tiene observaciones |
| COMPATIBLE CON OBSERVACIONES | Cumple lo obligatorio, pero faltan preferencias o sobra mucha capacidad |
| DESCARTADA | Falla al menos una condición obligatoria |


## Reglas 


| Reglas | Qué comprueban |
| --- | --- |
| R01 y R02 | Si alcanzan los lugares |
| R03 y R04 | Si una franja libre cubre toda la actividad |
| R05 y R06 | Si están todos los equipos obligatorios |
| R07, R08 y R09 | Si no se pide acceso, si está confirmado o si no está confirmado |
| R10 y R11 | Si alcanza la privacidad mínima |
| R12 y R13 | Si se necesita mover mesas y sillas, si está permitido |
| R14 y R15 | Si se cumplen juntas las seis comprobaciones obligatorias |
| R16 y R17 | Cuántos lugares sobran y si superan el 50 % de exceso |
| R18 | Aviso por exceso de capacidad en un espacio viable |
| R19 y R20 | Si se cumple cada preferencia; si no, avisan sin descartar |
| R21 | Cuántas preferencias se cumplieron |
| R22 | Clasificación como descartada |
| R23 | Clasificación como compatible con observaciones |
| R24 | Clasificación como recomendada |

Los tres niveles de encadenamiento se ven así:

1. De los datos se deducen **comprobaciones**: por ejemplo, R01 confirma capacidad.
2. De las seis comprobaciones se deduce la **preselección**: R14 confirma que cumple todo.
3. De la preselección, el ajuste de capacidad, las preferencias y los avisos se deduce
   la **clasificación final**: por ejemplo, R24 la clasifica como recomendada.

Cada activación se guarda en la traza con el número de regla, el espacio y el motivo.
La pantalla permite consultar los hechos iniciales, los deducidos y las reglas en
orden de ejecución. Cada búsqueda usa un motor nuevo.

## Probar sin abrir la pantalla

```powershell
.\.venv\Scripts\python.exe cargar_datos.py
.\.venv\Scripts\python.exe demostracion.py
```

El primer comando debe informar 10 espacios y 25 franjas. El segundo ejecuta los
12 ejemplos de esta versión, con lo esperado y lo obtenido. Debe terminar con
`Resultado: 12 de 12 ejemplos correctos.` y `Reglas del motor: 24`.

Para ver también las reglas activadas en cada ejemplo:

```powershell
.\.venv\Scripts\python.exe demostracion.py --detalle
```


