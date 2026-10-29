"""12 ejemplos , con resultado esperado y obtenido.

Adaptan situaciones del brief y agregan comprobaciones del nuevo modelo.
Son pruebas del desarrollo; 
"""

import argparse
from datetime import date, time

from cargar_datos import cargar_catalogo
from motor import (CANTIDAD_REGLAS, Clasificacion, Comprobacion, Observacion,
                   evaluar, explicar, hechos, recomendaciones)


def solicitud_ejemplo(**cambios):
    solicitud = {
        "tipo_actividad": "Clase", "modalidad": "presencial", "asistentes": 28,
        "fecha": date(2026, 10, 22), "hora_inicio": time(10), "hora_fin": time(12),
        "equipamiento_obligatorio": ["pantalla"],
    }
    solicitud.update(cambios)
    return solicitud


def estado(motor, codigo):
    return hechos(motor, Clasificacion, codigo)[0]["estado"]


def falla(motor, codigo, criterio):
    return any(h["criterio"] == criterio and not h["cumple"]
               for h in hechos(motor, Comprobacion, codigo))


def orden(motor):
    return [h["id_espacio"] for h in recomendaciones(motor)]


def casos_demostracion():
    taller = solicitud_ejemplo(
        tipo_actividad="Taller", asistentes=24, hora_inicio=time(13), hora_fin=time(15),
        requiere_reconfiguracion=True, requiere_accesibilidad=True, privacidad_obligatoria="media")
    return [
        {"codigo": "V01", "nombre": "Clase de 28 personas con TV obligatoria",
         "solicitud": solicitud_ejemplo(),
         "esperado": "A101 recomendada y en primer lugar.",
         "verificar": lambda m: estado(m, "A101") == "recomendada" and orden(m)[0] == "A101"},
        {"codigo": "V02", "nombre": "Cámara obligatoria en una actividad híbrida",
         "solicitud": solicitud_ejemplo(modalidad="hibrida", equipamiento_obligatorio=["camara"]),
         "esperado": "A101 descartada por falta de cámara.",
         "verificar": lambda m: estado(m, "A101") == "descartada" and falla(m, "A101", "equipamiento")},
        {"codigo": "V03", "nombre": "Ruta accesible obligatoria sin confirmar",
         "solicitud": solicitud_ejemplo(asistentes=20, requiere_accesibilidad=True),
         "esperado": "A104 descartada por accesibilidad no confirmada.",
         "verificar": lambda m: estado(m, "A104") == "descartada" and falla(m, "A104", "accesibilidad")},
        {"codigo": "V04", "nombre": "Taller que necesita mover mesas y sillas",
         "solicitud": taller,
         "esperado": "S103 recomendada primero; A102 como alternativa. Sin inferir preparación previa.",
         "verificar": lambda m: orden(m) == ["S103", "A102"] and estado(m, "S103") == "recomendada"},
        {"codigo": "V05", "nombre": "Faltan asistentes y modalidad",
         "solicitud": solicitud_ejemplo(asistentes=None, modalidad=None),
         "esperado": "Sin conclusión: hay datos indispensables incompletos.", "espera_error": "cantidad de asistentes"},
        {"codigo": "V06", "nombre": "Ningún espacio alcanza para 130 personas",
         "solicitud": solicitud_ejemplo(asistentes=130),
         "esperado": "Diez espacios descartados y ninguna opción viable.",
         "verificar": lambda m: not orden(m) and all(h["estado"] == "descartada" for h in hechos(m, Clasificacion))},
        {"codigo": "V07", "nombre": "Solo el auditorio tiene horario para una reunión de 10",
         "solicitud": solicitud_ejemplo(tipo_actividad="Reunión", asistentes=10,
                                         hora_inicio=time(20), hora_fin=time(22), equipamiento_obligatorio=[]),
         "esperado": "AU01 como única opción, con aviso por exceso de capacidad.",
         "verificar": lambda m: orden(m) == ["AU01"] and estado(m, "AU01") == "compatible_con_observaciones"
         and any(h["criterio"] == "exceso" for h in hechos(m, Observacion, "AU01"))},
        {"codigo": "V08", "nombre": "Clase de 40: aula de 45 antes que aula de 90",
         "solicitud": solicitud_ejemplo(asistentes=40, hora_inicio=time(13), hora_fin=time(15)),
         "esperado": "A102 recomendada primero y A201 entre las alternativas.",
         "verificar": lambda m: orden(m)[0] == "A102" and "A201" in orden(m) and estado(m, "A102") == "recomendada"},
        {"codigo": "V09", "nombre": "Preferir cámara y amplificación sin hacerlas obligatorias",
         "solicitud": dict(taller, equipamiento_deseable=["camara", "amplificacion_voz"]),
         "esperado": "A102 primero con 1 de 2 preferencias; S103 sigue viable con 0 de 2.",
         "verificar": lambda m: orden(m) == ["A102", "S103"]
         and [h["preferencias_cumplidas"] for h in recomendaciones(m)] == [1, 0]},
        {"codigo": "V10", "nombre": "Amplificación de voz obligatoria",
         "solicitud": solicitud_ejemplo(asistentes=30, hora_inicio=time(13), hora_fin=time(15),
                                         equipamiento_obligatorio=["amplificacion_voz"]),
         "esperado": "Solo AU01 es viable, con aviso por exceso de capacidad.",
         "verificar": lambda m: orden(m) == ["AU01"] and estado(m, "AU01") == "compatible_con_observaciones"},
        {"codigo": "V11", "nombre": "Mover mesas y sillas es obligatorio para 40 personas",
         "solicitud": solicitud_ejemplo(asistentes=40, hora_inicio=time(13), hora_fin=time(15),
                                         requiere_reconfiguracion=True),
         "esperado": "Solo A102 es viable; A201 se descarta por no permitir reconfiguración.",
         "verificar": lambda m: orden(m) == ["A102"] and falla(m, "A201", "reconfiguracion")},
        {"codigo": "V12", "nombre": "Privacidad alta y sala de 12 para 8 personas",
         "solicitud": solicitud_ejemplo(asistentes=8, equipamiento_obligatorio=[],
                                         privacidad_obligatoria="alta", requiere_accesibilidad=True),
         "esperado": "Solo S101 recomendada. El 50 % exacto de exceso no genera aviso.",
         "verificar": lambda m: orden(m) == ["S101"] and estado(m, "S101") == "recomendada"
         and not hechos(m, Observacion, "S101")},
    ]


def ejecutar_caso(caso, espacios, horarios):
    try:
        motor = evaluar(espacios, caso["solicitud"], horarios)
    except ValueError as error:
        esperado = caso.get("espera_error")
        return bool(esperado and esperado in str(error)), "Sin conclusión: " + str(error), None
    bien = not caso.get("espera_error") and caso["verificar"](motor)
    detalle = "; ".join(f"{h['id_espacio']}: {h['estado'].upper().replace('_', ' ')}" for h in recomendaciones(motor))
    return bien, detalle or "Ningún espacio compatible", motor


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--detalle", action="store_true", help="Mostrar las reglas activadas en cada ejemplo.")
    detalle = argumentos.parse_args().detalle
    espacios, horarios = cargar_catalogo()
    casos, correctos = casos_demostracion(), 0
    print("Ejemplos del catálogo simulado — versión simplificada\n")
    for caso in casos:
        bien, obtenido, motor = ejecutar_caso(caso, espacios, horarios)
        correctos += bien
        print(f"[{'BIEN' if bien else 'REVISAR'}] {caso['codigo']}: {caso['nombre']}")
        print("  Esperado: " + caso["esperado"])
        print("  Obtenido: " + obtenido)
        if detalle and motor:
            for espacio in espacios:
                print("  " + espacio["id_espacio"] + ":")
                for paso in explicar(motor, espacio["id_espacio"]):
                    print("    " + paso)
        print()
    print(f"Resultado: {correctos} de {len(casos)} ejemplos correctos.")
    print(f"Reglas del motor: {CANTIDAD_REGLAS}")
    return 0 if correctos == len(casos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
