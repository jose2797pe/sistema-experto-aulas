# AURA - Recomendador experto de aulas y espacios

Sistema experto con **Experta y Streamlit** que recomienda espacios segun sus caracteristicas y las reservas ficticias ya registradas, y explica sus decisiones. **No crea, modifica ni cancela reservas, ni bloquea horarios.**

Desarrollado por el **Grupo B - Analisis de Datos II - Segundo cuatrimestre de 2026**.

## Ejecutar

Desde la carpeta del proyecto, en PowerShell, con Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run interfaz.py
```

## Archivos

| Archivo | Para que sirve |
| --- | --- |
| `cargar_datos.py` | Lee y valida caracteristicas y reservas; define cuando se superponen dos intervalos. |
| `motor.py` | Hechos, 24 reglas de Experta, clasificacion, orden y justificaciones. |
| `interfaz.py` | Catalogo con filtros, formulario y explicacion de resultados. |
| `demostracion.py` | Pruebas automaticas de la version inicial. |
| `requirements.txt` | Dependencias del proyecto. |
| `datos/espacios.csv` | Identificacion y caracteristicas de los espacios. |
| `datos/reservas.csv` | Reservas ficticias existentes: cada fila indica un intervalo ocupado. |
| `imagenes/logo_aura.jpg` | Logo de AURA. |

## Que guarda cada CSV

`datos/espacios.csv` contiene **22 espacios: 21 aulas y un auditorio**. Los nombres y pisos corresponden a los espacios de la facultad; capacidades, caracteristicas y disponibilidad son simuladas.

| Columna | Que significa |
| --- | --- |
| `id_espacio` | Codigo unico, por ejemplo `A201` o `AU01`. |
| `nombre` | Nombre visible: Aula 201, Auditorio, etc. |
| `tipo` | `aula` o `auditorio` en este catalogo. |
| `piso` | Piso 2, 3 o 4; `-1` identifica el subsuelo del auditorio. |
| `capacidad` | Cantidad maxima de personas. |
| `reconfigurable` | Permiso para mover mesas y sillas. |
| `pantalla` | Disponibilidad de TV/pantalla. |
| `camara` | Disponibilidad de camara. |
| `amplificacion_voz` | Sistema para amplificar la voz. |
| `wifi` | Conectividad; esta presente en todo el edificio. |
| `ruta_accesible` | `si`, `no` o `desconocida`. |
| `privacidad` | Nivel `baja`, `media` o `alta`. |
| `origen` | Procedencia; actualmente `simulado`. |

`datos/reservas.csv` (antes llamado `horarios.csv`) contiene **346 reservas ficticias del 04/11 al 10/11 de 2026**. Se conservaron las filas, fechas y horas originales. Sus columnas son `id_espacio`, `fecha` (`AAAA-MM-DD`), `hora_inicio`, `hora_fin` (`HH:MM`) y `origen`.

Cada fila representa una **reserva que ocupa un espacio**. El sistema verifica capacidad, equipamiento y los demas requisitos, y descarta los espacios con alguna reserva que se superponga con la actividad en la misma fecha.

Hay superposicion si `inicio_actividad < fin_reserva` y `inicio_reserva < fin_actividad`. Esto incluye cruces parciales, intervalos contenidos y actividades que abarcan una o varias reservas. Por ejemplo, una reserva de **08:00 a 11:00** impide usar ese espacio de **10:00 a 12:00**, pero permite comenzar a las **11:00** o terminar a las **08:00**.

Si no hay una reserva que se superponga, el espacio se considera disponible segun los datos cargados, incluso en fechas sin reservas registradas. Un CSV con solo la cabecera significa que no hay reservas. No se definieron horarios de apertura adicionales: las reservas son la unica restriccion temporal del modelo.

La aplicacion unicamente consulta los CSV: una busqueda no agrega filas ni reserva el espacio recomendado. Actualizar estos archivos manualmente, conservando sus columnas, no requiere cambiar las reglas. Al incorporar cambios en una carpeta existente, reemplaza `horarios.csv` por `reservas.csv`; la aplicacion utiliza unicamente el nuevo nombre.

## Uso y criterios

- **Explorar:** filtros opcionales por piso, caracteristicas y privacidad; fecha y horas solo con **Consultar disponibilidad**. Usar **Aplicar filtros** o **Borrar filtros**.
- **Recomendar:** completar **Tu actividad** y presionar **Buscar espacios**. Muestra hasta cuatro opciones ordenadas y los descartes.

Lo **obligatorio** incumplido descarta; una **preferencia opcional** incumplida genera un aviso sin descartar. Lo no solicitado no restringe.

Privacidad es un minimo: alta cumple media. Accesibilidad exige ruta confirmada; `desconocida` no alcanza. La actividad es descriptiva; la modalidad **Hibrida** marca **Camara** obligatoria automaticamente.

| Resultado | Que significa |
| --- | --- |
| Recomendada | Cumple lo obligatorio y no tiene observaciones. |
| Compatible con observaciones | Cumple lo obligatorio, pero falta una preferencia o la capacidad supera en mas del 50 % a los asistentes. |
| Descartada | Incumple al menos una condicion obligatoria. |

**Orden:** mas preferencias opcionales cumplidas y, despues, menor cantidad de lugares sobrantes. La primera opcion puede ser compatible con observaciones.

Los desplegables explican opciones, descartes y razonamiento. La tabla de reglas incluye todas las aulas en el orden real de activacion. Cada busqueda usa un motor nuevo.

## Reglas y relacion con el brief

Referencias: **Brief del Grupo A (18/09/2026)**, seccion7 (requisitos RF) y seccion8 (criterios); **Acta del 24/09/2026**, seccion4-5 (alcance del MVP). Se describe la aplicacion actual de cada criterio.

| Reglas | Que hacen | Referencia |
| --- | --- | --- |
| R01-R02 | Comprueban capacidad: si faltan lugares, la condicion falla. | RF-03; seccion8. |
| R03-R04 | R04 detecta primero reservas que se superponen, del mismo espacio y fecha. R03 confirma disponibilidad si no se encontro un conflicto. | RF-03; seccion5. |
| R05-R06 | Validan los equipos obligatorios; si falta uno, la condicion falla. | RF-04; seccion8, CA-02. |
| R07-R09 | Sin pedido de accesibilidad no restringen; si se pide, exigen ruta confirmada. | RF-05; CA-03. |
| R10-R11 | Comparan la privacidad con el minimo solicitado. | RF-04; seccion8. |
| R12-R13 | Si se necesita mover mesas y sillas, exigen permiso de reconfiguracion. | RF-04; seccion6, adaptado al modelo simplificado. |
| R14-R15 | Reunen las seis comprobaciones: solo preseleccionan si se cumplen todas. | RF-03 a RF-05 y RF-07; encadenamiento implementado. |
| R16-R18 | Calculan lugares sobrantes; si una opcion viable supera el 50 % de exceso, agregan aviso sin descartarla. | Umbral: seccion8. Aviso en toda opcion viable: decision de esta version. |
| R19-R21 | Cuentan preferencias cumplidas; cada faltante genera un aviso sin descartar. | RF-04, RF-07 y seccion8. |
| R22 | Clasifica como descartada si falla alguna condicion obligatoria. | RF-07; seccion8. |
| R23 | Clasifica como compatible si cumple lo obligatorio y tiene observaciones. | RF-07; seccion8. |
| R24 | Clasifica como recomendada si cumple lo obligatorio y no tiene observaciones. | RF-07; seccion8. |

Los **tres niveles de encadenamiento** son:

1. Solicitud, caracteristicas de espacios y reservas existentes -> comprobaciones de requisitos.
2. Comprobaciones -> preseleccion del espacio.
3. Preseleccion, ajuste de capacidad y preferencias -> clasificacion final.

Fuera de las 24 reglas: **RF-01** valida entradas; **RF-02** lee CSV; **RF-08** registra justificaciones; **RF-14** reinicia la evaluacion.

El acta excluyo **RF-06, RF-09, RF-10 y RF-12**. **Simplificaciones del proyecto:** aulas y auditorio, TV en lugar de proyector, amplificacion de voz unificada y reconfiguracion como permiso, sin inferir preparacion. La camara automatica es una ayuda del formulario, no una regla por tipo de actividad.

## Cuatro pruebas en la interfaz

En cada caso, usa **duracion de 3 horas** y presiona **Buscar espacios**. Antes de pasar al siguiente, quita los requisitos y preferencias anteriores. Salvo indicacion: modalidad **Presencial**, privacidad minima **Sin requisito**, privacidad preferida **Sin preferencia** y ninguna opcion marcada.

### 1. Capacidad y disponibilidad

**Completar:** actividad Clase; 40 personas; 04/11/2026; 08:00. Marcar **TV/pantalla** como obligatoria.

**Esperado:** seis opciones viables. Se muestran Aula 302, Aula 308 y Aula 202 como **Recomendada**, con 0, 0 y 5 lugares sobrantes, y Aula 304 como **Compatible con observaciones**, con 30 lugares sobrantes. Las siguientes alternativas son Aula 405 y Auditorio. Aula 201 falla por capacidad y por una reserva de 08:00 a 11:00; Aula 306 tambien esta reservada en ese intervalo.

### 2. Una preferencia no compensa una reserva existente

**Completar:** actividad Clase; 40 personas; 04/11/2026; 11:00. En **Preferencias opcionales -> Me gustaria, pero no es obligatorio**, elegir **Amplificacion de voz**.

**Esperado:** Aula 306, Aula 404 y Aula 307, en ese orden. Todas son **Compatible con observaciones** porque no tienen amplificacion de voz, pero cumplen lo obligatorio. El Auditorio tiene ese equipo, pero se descarta por una reserva de 11:00 a 14:00: cumplir una preferencia no compensa la falta de disponibilidad.

### 3. Taller con mobiliario y accesibilidad obligatorios

**Completar:** actividad Taller; 25 personas; 04/11/2026; 08:00. Marcar **TV/pantalla**, **Necesito mover mesas y sillas** y **Ruta accesible confirmada**. Privacidad minima: **Media**.

**Esperado:** Aula 206 como **Recomendada**, con 10 lugares sobrantes; despues, Aula 302, Aula 308 y Aula 202 como **Compatible con observaciones** por exceso de capacidad. Aula 306 falla por reserva y por no permitir mover el mobiliario. Aula 309 falla por reserva, reconfiguracion y ruta accesible sin confirmar.

### 4. Hibrida con privacidad alta

**Completar:** actividad Clase hibrida; 30 personas; 05/11/2026; 08:00; modalidad **Hibrida**. Marcar **Ruta accesible confirmada** y privacidad minima **Alta**. La camara queda obligatoria automaticamente.

**Esperado:** solo Aula 303, **Recomendada**, con 5 lugares sobrantes. Aula 206 y Aula 401 tambien tienen camara y privacidad alta, pero se descartan por reservas de 08:00 a 11:00. Si cambias a **40 personas** y volves a buscar, no habra opciones: los espacios con privacidad alta tienen capacidad para 35.

Estos resultados corresponden al catalogo incluido; pueden cambiar al actualizar los CSV. Los motivos se comprueban en los desplegables de opciones y descartes.

## Comprobar la carga de datos

```powershell
.\.venv\Scripts\python.exe cargar_datos.py
```

Debe informar **22 espacios y 346 reservas registradas**, con fechas del 04/11 al 10/11/2026.

`demostracion.py` conserva identificadores y fechas del catalogo anterior. No corresponde esperar sus antiguos "12 de 12" con estos CSV; las cuatro pruebas anteriores estan verificadas para esta version.

El ZIP de entrega incluye codigo, datos, logo y configuracion. El entorno `.venv` se crea en cada computadora con los comandos de la seccion **Ejecutar**; no se copia el entorno de Windows del ZIP original. Para la publicacion, el archivo de entrada sigue siendo `interfaz.py` y las dependencias siguen en `requirements.txt`.
