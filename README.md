# AURA · Recomendador experto de aulas y espacios

Sistema experto con **Experta y Streamlit** que recomienda espacios según sus características y las reservas ficticias ya registradas, y explica sus decisiones. **No crea, modifica ni cancela reservas, ni bloquea horarios.**

Desarrollado por el **Grupo B · Análisis de Datos II · Segundo cuatrimestre de 2026**.
## Integrantes
Gustavo Sebastian Cristiano
Jose Pereira
Micaela Gomez
Jose Garibaldi
José Aníbal Alejandro Franco

## Ejecutar

Desde la carpeta del proyecto, en PowerShell, con Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run interfaz.py
```
###  Probar el sistema en línea

Si querés ver el sistema experto funcionando directamente desde el navegador, podés acceder al siguiente enlace:

👉 [**Abrir Sistema Experto de Recomendación de Aulas**](https://sistema-experto-aulas-faxmlqqxgzsfkxcvutn45h.streamlit.app/)



## Archivos

| Archivo | Para qué sirve |
| --- | --- |
| `cargar_datos.py` | Lee y valida características y reservas; define cuándo se superponen dos intervalos. |
| `motor.py` | Hechos, 24 reglas de Experta, clasificación, orden y justificaciones. |
| `interfaz.py` | Catálogo con filtros, formulario y explicación de resultados. |
| `demostracion.py` | Pruebas automáticas de la versión inicial. |
| `requirements.txt` | Dependencias del proyecto. |
| `datos/espacios.csv` | Identificación y características de los espacios. |
| `datos/reservas.csv` | Reservas ficticias existentes: cada fila indica un intervalo ocupado. |
| `imagenes/logo_aura.jpg` | Logo de AURA. |

## Que guarda cada CSV

### datos/espacios.csv

Contiene **22 espacios: 21 aulas y un auditorio**. Los nombres y pisos corresponden a los espacios de la facultad; las capacidades y caracteristicas son simuladas.

La columna **Ejemplo** muestra los datos de una fila: el Aula 201.

| Columna | Que significa | Ejemplo |
| --- | --- | --- |
| `id_espacio` | Codigo unico del espacio. | `A201` |
| `nombre` | Nombre visible del espacio. | `Aula 201` |
| `tipo` | Tipo de espacio: aula o auditorio. | `aula` |
| `piso` | Piso del espacio; `-1` identifica el subsuelo. | `2` |
| `capacidad` | Cantidad maxima de personas. | `30` |
| `reconfigurable` | Permiso para mover mesas y sillas. | `si` |
| `pantalla` | Indica si tiene TV/pantalla. | `si` |
| `camara` | Indica si tiene camara. | `no` |
| `amplificacion_voz` | Indica si tiene un sistema para amplificar la voz. | `no` |
| `wifi` | Indica si tiene conectividad WiFi. | `si` |
| `ruta_accesible` | Ruta accesible: `si`, `no` o `desconocida`. | `si` |
| `privacidad` | Nivel de privacidad: `baja`, `media` o `alta`. | `media` |
| `origen` | Procedencia de los datos. | `simulado` |

### datos/reservas.csv

Contiene **346 reservas ficticias del 04/11 al 10/11 de 2026**. Cada fila representa un intervalo ocupado para un espacio.

La columna **Ejemplo** muestra los datos de una reserva del Aula 201.

| Columna | Que significa | Ejemplo |
| --- | --- | --- |
| `id_espacio` | Codigo del espacio reservado; debe existir en espacios.csv. | `A201` |
| `fecha` | Fecha de la reserva, con formato AAAA-MM-DD. | `2026-11-04` |
| `hora_inicio` | Hora de inicio de la reserva, con formato HH:MM. | `08:00` |
| `hora_fin` | Hora de finalizacion de la reserva, con formato HH:MM. | `11:00` |
| `origen` | Procedencia de los datos. | `simulado` |

**Ejemplo:** el Aula 201 esta reservada el 04/11/2026 de 08:00 a 11:00. Una actividad que se superponga con ese intervalo no puede utilizarla.

El sistema consulta estas reservas para evaluar la disponibilidad. **No crea, modifica ni cancela reservas.**

Cada fila representa una **reserva que ocupa un espacio**. El sistema verifica capacidad, equipamiento y los demás requisitos, y descarta los espacios con alguna reserva que se superponga con la actividad en la misma fecha.

Hay superposición si `inicio_actividad < fin_reserva` y `inicio_reserva < fin_actividad`. Esto incluye cruces parciales, intervalos contenidos y actividades que abarcan una o varias reservas. Por ejemplo, una reserva de **08:00 a 11:00** impide usar ese espacio de **10:00 a 12:00**, pero permite comenzar a las **11:00** o terminar a las **08:00**.

Si no hay una reserva que se superponga, el espacio se considera disponible según los datos cargados, incluso en fechas sin reservas registradas. Un CSV con solo la cabecera significa que no hay reservas. No se definieron horarios de apertura adicionales: las reservas son la única restricción temporal del modelo.

La aplicación únicamente consulta los CSV: una búsqueda no agrega filas ni reserva el espacio recomendado. Actualizar estos archivos manualmente, conservando sus columnas, no requiere cambiar las reglas. Al incorporar cambios en una carpeta existente, reemplazá `horarios.csv` por `reservas.csv`; la aplicación utiliza únicamente el nuevo nombre.

## Uso y criterios

- **Explorar:** filtros opcionales por piso, características y privacidad; fecha y horas solo con **Consultar disponibilidad**. Usar **Aplicar filtros** o **Borrar filtros**.
- **Recomendar:** completar **Tu actividad** y presionar **Buscar espacios**. Muestra hasta cuatro opciones ordenadas y los descartes.

Lo **obligatorio** incumplido descarta; una **preferencia opcional** incumplida genera un aviso sin descartar. Lo no solicitado no restringe.

Privacidad es un mínimo: alta cumple media. Accesibilidad exige ruta confirmada; `desconocida` no alcanza. La actividad es descriptiva; la modalidad **Híbrida** marca **Cámara** obligatoria automáticamente.

| Resultado | Qué significa |
| --- | --- |
| Recomendada | Cumple lo obligatorio y no tiene observaciones. |
| Compatible con observaciones | Cumple lo obligatorio, pero falta una preferencia o la capacidad supera en más del 50 % a los asistentes. |
| Descartada | Incumple al menos una condición obligatoria. |

**Orden:** más preferencias opcionales cumplidas y, después, menor cantidad de lugares sobrantes. La primera opción puede ser compatible con observaciones.

Los desplegables explican opciones, descartes y razonamiento. La tabla de reglas incluye todas las aulas en el orden real de activación. Cada búsqueda usa un motor nuevo.

## Reglas y relación con el brief

Referencias: **Brief del Grupo A (18/09/2026)**, §7 (requisitos RF) y §8 (criterios); **Acta del 24/09/2026**, §4–5 (alcance del MVP). Se describe la aplicación actual de cada criterio.

| Reglas | Qué hacen | Referencia |
| --- | --- | --- |
| R01–R02 | Comprueban capacidad: si faltan lugares, la condición falla. | RF-03; §8. |
| R03–R04 | R04 detecta primero reservas que se superponen, del mismo espacio y fecha. R03 confirma disponibilidad si no se encontró un conflicto. | RF-03; §5. |
| R05–R06 | Validan los equipos obligatorios; si falta uno, la condición falla. | RF-04; §8, CA-02. |
| R07–R09 | Sin pedido de accesibilidad no restringen; si se pide, exigen ruta confirmada. | RF-05; CA-03. |
| R10–R11 | Comparan la privacidad con el mínimo solicitado. | RF-04; §8. |
| R12–R13 | Si se necesita mover mesas y sillas, exigen permiso de reconfiguración. | RF-04; §6, adaptado al modelo simplificado. |
| R14–R15 | Reúnen las seis comprobaciones: solo preseleccionan si se cumplen todas. | RF-03 a RF-05 y RF-07; encadenamiento implementado. |
| R16–R18 | Calculan lugares sobrantes; si una opción viable supera el 50 % de exceso, agregan aviso sin descartarla. | Umbral: §8. Aviso en toda opción viable: decisión de esta versión. |
| R19–R21 | Cuentan preferencias cumplidas; cada faltante genera un aviso sin descartar. | RF-04, RF-07 y §8. |
| R22 | Clasifica como descartada si falla alguna condición obligatoria. | RF-07; §8. |
| R23 | Clasifica como compatible si cumple lo obligatorio y tiene observaciones. | RF-07; §8. |
| R24 | Clasifica como recomendada si cumple lo obligatorio y no tiene observaciones. | RF-07; §8. |

Los **tres niveles de encadenamiento** son:

1. Solicitud, características de espacios y reservas existentes → comprobaciones de requisitos.
2. Comprobaciones → preselección del espacio.
3. Preselección, ajuste de capacidad y preferencias → clasificación final.

Fuera de las 24 reglas: **RF-01** valida entradas; **RF-02** lee CSV; **RF-08** registra justificaciones; **RF-14** reinicia la evaluación.

El acta excluyó **RF-06, RF-09, RF-10 y RF-12**. **Simplificaciones del proyecto:** aulas y auditorio, TV en lugar de proyector, amplificación de voz unificada y reconfiguración como permiso, sin inferir preparación. La cámara automática es una ayuda del formulario, no una regla por tipo de actividad.

## Cuatro pruebas en la interfaz

Antes de cada prueba, presiona **Nueva consulta** y selecciona la fecha **04/11/2026**.

**Cambia solamente los campos indicados en cada caso. Los demas quedan con sus valores iniciales.** Despues, presiona **Buscar espacios**.

### 1. Capacidad y disponibilidad

- **Cantidad de personas:** 40.
- **Requisitos obligatorios:** marcar TV/pantalla.

**Esperado:** seis opciones viables. Las primeras cuatro son Aula 302, Aula 308 y Aula 202 como **Recomendada**, y Aula 304 como **Compatible con observaciones** por exceso de capacidad. Aula 306 se descarta porque esta reservada de 08:00 a 11:00.

### 2. Una preferencia no compensa una reserva existente

- **Cantidad de personas:** 40.
- **Hora de inicio:** 11:00.
- **Preferencias opcionales:** elegir Amplificacion de voz.

**Esperado:** Aula 306, Aula 404 y Aula 307, en ese orden, como **Compatible con observaciones** porque no cumplen la preferencia. El Auditorio tiene amplificacion de voz, pero se descarta porque esta reservado de 11:00 a 14:00.

### 3. Taller con mobiliario y accesibilidad obligatorios

- **Actividad:** Taller.
- **Cantidad de personas:** 25.
- **Requisitos obligatorios:** marcar TV/pantalla, Necesito mover mesas y sillas y Ruta accesible confirmada.
- **Privacidad minima:** Media.

**Esperado:** Aula 206 como **Recomendada**; despues, Aula 302, Aula 308 y Aula 202 como **Compatible con observaciones** por exceso de capacidad.

### 4. Hibrida con privacidad alta

- **Actividad:** Clase hibrida.
- **Cantidad de personas:** 30.
- **Fecha:** 05/11/2026.
- **Modalidad:** Hibrida. La camara se marca automaticamente.
- **Requisitos obligatorios:** marcar Ruta accesible confirmada.
- **Privacidad minima:** Alta.

**Esperado:** solo Aula 303, como **Recomendada**, con 5 lugares sobrantes. Aula 206 y Aula 401 se descartan porque estan reservadas de 08:00 a 11:00.

Estos resultados corresponden a los CSV incluidos y pueden cambiar si se modifican sus datos.

## Comprobar la carga de datos

```powershell
.\.venv\Scripts\python.exe cargar_datos.py
```

Debe informar **22 espacios y 346 reservas registradas**, con fechas del 04/11 al 10/11/2026.

`demostracion.py` conserva identificadores y fechas del catálogo anterior. No corresponde esperar sus antiguos «12 de 12» con estos CSV; las cuatro pruebas anteriores están verificadas para esta versión.

El ZIP de entrega incluye código, datos, logo y configuración. El entorno `.venv` se crea en cada computadora con los comandos de la sección **Ejecutar**; no se copia el entorno de Windows del ZIP original. Para la publicación, el archivo de entrada sigue siendo `interfaz.py` y las dependencias siguen en `requirements.txt`.
