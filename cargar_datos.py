"""Lee el catálogo simulado. No modifica archivos ni registra reservas."""

import csv
from datetime import date, time
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent / "datos"
EQUIPAMIENTO = ("pantalla", "camara", "amplificacion_voz")
COLUMNAS_ESPACIOS = (
    "id_espacio", "nombre", "tipo", "piso", "capacidad", "reconfigurable",
    "pantalla", "camara", "amplificacion_voz", "wifi", "ruta_accesible",
    "privacidad", "origen",
)
COLUMNAS_HORARIOS = ("id_espacio", "fecha", "hora_inicio", "hora_fin", "origen")


def leer_csv(ruta, columnas):
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames != list(columnas):
            raise ValueError(f"{ruta.name}: se esperan estas columnas, en orden: "
                             + ", ".join(columnas))
        filas = []
        for numero, fila in enumerate(lector, start=2):
            if None in fila or any(valor is None or not valor.strip() for valor in fila.values()):
                raise ValueError(f"{ruta.name}, fila {numero}: hay datos vacíos o columnas de más.")
            filas.append({campo: valor.strip() for campo, valor in fila.items()})
    return filas


def convertir_si_no(valor, permite_desconocida=False):
    opciones = {"si": True, "sí": True, "no": False}
    if permite_desconocida:
        opciones["desconocida"] = None
    if valor.casefold() not in opciones:
        raise ValueError("Se esperaba si/no" + ("/desconocida." if permite_desconocida else "."))
    return opciones[valor.casefold()]


def cargar_catalogo(carpeta=CARPETA_DATOS):
    """Devuelve espacios y franjas LIBRES con números, fechas y booleanos."""
    carpeta = Path(carpeta)
    espacios, codigos = [], set()
    for fila in leer_csv(carpeta / "espacios.csv", COLUMNAS_ESPACIOS):
        codigo = fila["id_espacio"]
        try:
            if codigo in codigos:
                raise ValueError("Código de espacio repetido.")
            fila["piso"], fila["capacidad"] = int(fila["piso"]), int(fila["capacidad"])
            if fila["piso"] < -1 or fila["capacidad"] <= 0:
                raise ValueError("El piso debe ser -1 o mayor y la capacidad debe ser positiva.")
            if fila["tipo"] not in ("aula", "sala", "auditorio"):
                raise ValueError("El tipo debe ser aula, sala o auditorio.")
            if fila["privacidad"] not in ("baja", "media", "alta"):
                raise ValueError("La privacidad debe ser baja, media o alta.")
            for campo in (*EQUIPAMIENTO, "reconfigurable", "wifi"):
                fila[campo] = convertir_si_no(fila[campo])
            fila["ruta_accesible"] = convertir_si_no(fila["ruta_accesible"], True)
        except ValueError as error:
            raise ValueError(f"espacios.csv, {codigo}: {error}") from error
        codigos.add(codigo)
        espacios.append(fila)
    if not espacios:
        raise ValueError("El catálogo de espacios está vacío.")

    horarios = []
    for fila in leer_csv(carpeta / "horarios.csv", COLUMNAS_HORARIOS):
        codigo = fila["id_espacio"]
        try:
            if codigo not in codigos:
                raise ValueError("El código no existe en espacios.csv.")
            fila["fecha"] = date.fromisoformat(fila["fecha"])
            for campo in ("hora_inicio", "hora_fin"):
                fila[campo] = time.fromisoformat(fila[campo])
                if fila[campo].tzinfo is not None:
                    raise ValueError("Usar horas locales sin zona horaria.")
            if fila["hora_inicio"] >= fila["hora_fin"]:
                raise ValueError("La hora de fin debe ser posterior al inicio, en el mismo día.")
        except ValueError as error:
            raise ValueError(f"horarios.csv, {codigo}: {error}") from error
        horarios.append(fila)
    return espacios, horarios


def unir_franjas(horarios):
    """Une franjas vecinas o superpuestas; conserva los huecos sin disponibilidad."""
    resultado = []
    for horario in sorted(horarios, key=lambda h: (
        h["id_espacio"], h["fecha"], h["hora_inicio"], h["hora_fin"]
    )):
        actual = dict(horario)
        if resultado:
            anterior = resultado[-1]
            misma_agenda = (anterior["id_espacio"], anterior["fecha"]) == (
                actual["id_espacio"], actual["fecha"])
            if misma_agenda and actual["hora_inicio"] <= anterior["hora_fin"]:
                anterior["hora_fin"] = max(anterior["hora_fin"], actual["hora_fin"])
                if anterior["origen"] != actual["origen"]:
                    anterior["origen"] = "mixto"
                continue
        resultado.append(actual)
    return resultado


if __name__ == "__main__":
    espacios, horarios = cargar_catalogo()
    fechas = sorted({h["fecha"] for h in horarios})
    print(f"Catálogo simulado cargado: {len(espacios)} espacios y {len(horarios)} franjas libres.")
    print("Fechas: " + ", ".join(f"{fecha:%d/%m/%Y}" for fecha in fechas))
