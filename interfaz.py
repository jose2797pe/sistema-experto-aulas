"""Interfaz de recomendación de espacios. Las decisiones están en motor.py."""

import json
from datetime import datetime, time, timedelta

import streamlit as st

from cargar_datos import cargar_catalogo
from motor import (Clasificacion, Comprobacion, Espacio, Horario, Justificacion,
                   NOMBRES, Observacion, Preferencia, Solicitud,
                   evaluar, hechos, recomendaciones)

ESTADOS = {"recomendada": "Recomendada", "descartada": "Descartada",
           "compatible_con_observaciones": "Compatible con observaciones"}
RECURSOS = tuple(NOMBRES)


def aplicar_estilo():
    """Ajusta el ancho, el espaciado y el botón principal."""
    st.markdown("""
        <style>
        .block-container {
            max-width: 1060px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }
        h1 { letter-spacing: -0.035em; }
        [data-testid="stForm"] {
            border-radius: 16px;
            padding: 1.5rem;
        }
        [data-testid="stMetricValue"] { font-size: 1.6rem; }
        [data-testid="stBaseButton-primary"] {
            background-color: #14796c;
            border-color: #14796c;
            color: #ffffff;
        }
        [data-testid="stBaseButton-primary"]:hover {
            background-color: #106457;
            border-color: #106457;
            color: #ffffff;
        }
        @media (max-width: 640px) {
            .block-container { padding-top: 1.5rem; }
            [data-testid="stForm"] { padding: 1rem; }
            h1 { font-size: 1.9rem; }
        }
        </style>
    """, unsafe_allow_html=True)


def limpiar_consulta():
    for clave in list(st.session_state):
        if clave.startswith("consulta_") or clave in ("resultado", "ver_descartado", "ver_razonamiento"):
            del st.session_state[clave]


def guardar_resultado(motor, espacios, solicitud):
    """Guarda una foto de la última búsqueda; cambiar un selector no reevalúa."""
    iniciales, derivados = [], []
    for hecho in motor.facts.values():
        if type(hecho).__name__ == "InitialFact" or isinstance(hecho, Justificacion):
            continue
        datos = {k: v for k, v in hecho.items() if not k.startswith("__")}
        fila = {"tipo": type(hecho).__name__, "datos": datos}
        if isinstance(hecho, (Solicitud, Espacio, Horario, Preferencia)):
            iniciales.append(fila)
        else:
            derivados.append(fila)
    resultado = {
        "solicitud": solicitud, "espacios": {e["id_espacio"]: e for e in espacios},
        "opciones": recomendaciones(motor), "iniciales": iniciales, "derivados": derivados,
        "clasificaciones": [dict(h) for h in hechos(motor, Clasificacion)],
        "comprobaciones": [dict(h) for h in hechos(motor, Comprobacion)],
        "observaciones": [dict(h) for h in hechos(motor, Observacion)], "traza": motor.traza,
    }
    st.session_state["resultado"] = json.loads(json.dumps(resultado, default=str))


def mostrar_resultado(r):
    s, espacios = r["solicitud"], r["espacios"]
    st.divider()
    st.subheader("Resultado de la última búsqueda")
    fecha = datetime.strptime(s["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")
    st.write(f"**{s['tipo_actividad'] or 'Actividad'}** · {s['asistentes']} personas · "
             f"{fecha} · {s['hora_inicio'][:5]} a {s['hora_fin'][:5]}")
    st.caption("Si cambiás algún dato del formulario, presioná Buscar espacios para actualizar el resultado.")
    if not r["opciones"]:
        st.warning("Ningún espacio cumple todos los requisitos obligatorios.")
        st.caption("Revisá los espacios descartados para conocer los motivos.")
    else:
        st.caption("Orden: más preferencias cumplidas y luego menos lugares sobrantes.")
        for numero, opcion in enumerate(r["opciones"][:4], start=1):
            c = opcion["id_espacio"]
            espacio = espacios[c]
            titulo = "Primera opción" if numero == 1 else f"Alternativa {numero - 1}"
            with st.container(border=True):
                st.caption(titulo.upper())
                st.subheader(espacio["nombre"])
                st.caption(f"Código del espacio: {c}")
                if opcion["estado"] == "compatible_con_observaciones":
                    st.warning(ESTADOS[opcion["estado"]])
                else:
                    st.success(ESTADOS[opcion["estado"]])
                columnas = st.columns(3 if opcion["preferencias_totales"] else 2)
                columnas[0].metric("Capacidad", f"{espacio['capacidad']} personas")
                columnas[1].metric("Lugares sobrantes", opcion["holgura"])
                if opcion["preferencias_totales"]:
                    columnas[2].metric("Preferencias cumplidas",
                                       f"{opcion['preferencias_cumplidas']} de {opcion['preferencias_totales']}")
                for aviso in r["observaciones"]:
                    if aviso["id_espacio"] == c:
                        st.write("• " + aviso["motivo"])
    descartados = sorted(h["id_espacio"] for h in r["clasificaciones"] if h["estado"] == "descartada")
    with st.expander(f"Espacios descartados ({len(descartados)})"):
        if descartados:
            filas = []
            for c in descartados:
                motivos = [h["motivo"] for h in r["comprobaciones"]
                           if h["id_espacio"] == c and not h["cumple"]]
                filas.append({"Espacio": espacios[c]["nombre"], "Motivos": " ".join(motivos)})
            st.dataframe(filas, hide_index=True, width="stretch")
            codigo = st.selectbox("Ver explicación de un espacio descartado", descartados,
                                  format_func=lambda c: espacios[c]["nombre"], key="ver_descartado")
            for h in r["comprobaciones"]:
                if h["id_espacio"] == codigo and not h["cumple"]:
                    st.write("• " + h["motivo"])
        else:
            st.write("No se descartó ningún espacio.")
    with st.expander("Ver cómo llegó a la conclusión"):
        codigo = st.selectbox("Espacio para consultar el razonamiento", sorted(espacios),
                              format_func=lambda c: espacios[c]["nombre"], key="ver_razonamiento")
        st.code("\n".join(f"{p['regla']}: {p['motivo']}" for p in r["traza"] if p["id_espacio"] == codigo),
                language=None)
        st.write("Hechos iniciales: solicitud, catálogo, franjas libres y preferencias.")
        st.json(r["iniciales"], expanded=False)
        st.write("Hechos deducidos por las reglas.")
        st.json(r["derivados"], expanded=False)
        st.write("Reglas activadas en orden de ejecución.")
        st.dataframe(r["traza"], hide_index=True, width="stretch")


def mostrar_interfaz():
    st.set_page_config(page_title="Recomendación de espacios", page_icon="🏫", layout="wide")
    aplicar_estilo()
    st.caption("ESPACIOS UNIVERSITARIOS")
    st.title("Recomendación de espacios")
    st.write("Contanos qué vas a organizar y encontrá un espacio que se ajuste a tus necesidades.")
    st.caption("Catálogo simulado · Las búsquedas no generan reservas.")
    try:
        espacios, horarios = cargar_catalogo()
    except (OSError, ValueError) as error:
        st.error(f"No se puede obtener una conclusión: no se pudo cargar el catálogo. {error}")
        st.stop()
    fechas = sorted({h["fecha"] for h in horarios})
    encabezado, accion = st.columns([3, 1], vertical_alignment="center")
    encabezado.subheader("Tu solicitud")
    accion.button("Nueva consulta", on_click=limpiar_consulta, key="nueva_consulta", width="stretch")

    with st.form("formulario_solicitud"):
        st.markdown("#### 1. Datos de la actividad")
        nombre, modo, cantidad = st.columns([2, 1, 1])
        with nombre:
            actividad = st.text_input("Actividad", value="Clase", placeholder="Ejemplo: reunión de equipo",
                                      help="Escribí un nombre para identificar la actividad.",
                                      key="consulta_actividad")
        with modo:
            modalidad = st.selectbox("Modalidad", ("presencial", "hibrida"),
                                     format_func=lambda x: "Híbrida" if x == "hibrida" else "Presencial",
                                     help="Presencial: en el edificio. Híbrida: participantes presenciales y a distancia. "
                                          "Elegí los equipos necesarios en los requisitos.",
                                     key="consulta_modalidad")
        with cantidad:
            asistentes = st.number_input("Cantidad de personas", min_value=1, value=None, step=1,
                                          placeholder="Ej.: 30", key="consulta_asistentes")

        st.markdown("#### 2. Fecha y horario")
        dia, hora, minutos = st.columns(3)
        with dia:
            fecha = st.date_input("Fecha", value=fechas[0] if fechas else datetime.now().date(),
                                   format="DD/MM/YYYY", key="consulta_fecha")
        with hora:
            inicio = st.time_input("Hora de inicio", value=time(10), key="consulta_inicio")
        with minutos:
            duracion = st.number_input("Duración en minutos", min_value=1, max_value=1440, value=120, step=15,
                                        key="consulta_duracion")
        st.caption("Fechas con franjas libres en el catálogo: " +
                   (", ".join(f"{f:%d/%m/%Y}" for f in fechas) or "ninguna"))

        st.divider()
        st.markdown("#### 3. Qué necesitás")
        st.caption("Un espacio debe cumplir todos los requisitos obligatorios para ser una opción.")
        obligatorios = st.multiselect("Lo necesito obligatoriamente", RECURSOS,
                                       format_func=lambda r: NOMBRES[r],
                                       help="TV/pantalla: mostrar contenido. Amplificación de voz: "
                                            "hacer que se escuche a quien habla. Reconfigurable: mover mesas y sillas.",
                                       key="consulta_obligatorios")
        reserva, acceso = st.columns(2, vertical_alignment="bottom")
        with reserva:
            privacidad = st.selectbox("Privacidad mínima obligatoria", (None, "baja", "media", "alta"),
                                       format_func=lambda n: n.capitalize() if n else "Sin requisito",
                                       key="consulta_privacidad")
        with acceso:
            accesibilidad = st.checkbox("Necesito una ruta accesible confirmada", key="consulta_accesibilidad")
        with st.expander("Preferencias opcionales"):
            st.caption("Si una preferencia no se cumple, el espacio sigue siendo una opción.")
            deseables = st.multiselect("Me gustaría, pero no es obligatorio", RECURSOS,
                                        format_func=lambda r: NOMBRES[r], key="consulta_deseables")
            privacidad_deseable = st.selectbox("Privacidad preferida", (None, "baja", "media", "alta"),
                                               format_func=lambda n: n.capitalize() if n else "Sin preferencia",
                                               key="consulta_privacidad_deseable")
        st.caption("Hay WiFi en todo el edificio. Las notebooks se solicitan en Bedelía y se llevan al salón.")
        buscar = st.form_submit_button("Buscar espacios", type="primary", width="stretch")

    if buscar:
        st.session_state.pop("resultado", None)
        try:
            if asistentes is None:
                raise ValueError("Completá la cantidad de personas.")
            if fecha is None or inicio is None:
                raise ValueError("Completá la fecha y la hora de inicio.")
            if type(duracion) is not int or not 1 <= duracion <= 1440:
                raise ValueError("Completá una duración de 1 a 1440 minutos.")
            fin = datetime.combine(fecha, inicio) + timedelta(minutes=duracion)
            if fin.date() != fecha:
                raise ValueError("La actividad debe comenzar y terminar dentro del mismo día.")
            solicitud = {
                "tipo_actividad": actividad, "modalidad": modalidad, "asistentes": asistentes,
                "fecha": fecha, "hora_inicio": inicio, "hora_fin": fin.time(),
                "equipamiento_obligatorio": [r for r in obligatorios if r != "reconfigurable"],
                "equipamiento_deseable": [r for r in deseables if r != "reconfigurable"],
                "requiere_reconfiguracion": "reconfigurable" in obligatorios,
                "prefiere_reconfiguracion": "reconfigurable" in deseables,
                "requiere_accesibilidad": accesibilidad,
                "privacidad_obligatoria": privacidad, "privacidad_deseable": privacidad_deseable,
            }
            motor = evaluar(espacios, solicitud, horarios)
            guardar_resultado(motor, espacios, solicitud)
        except ValueError as error:
            st.error(f"No se puede obtener una conclusión: {error}")
    if "resultado" in st.session_state:
        mostrar_resultado(st.session_state["resultado"])


if __name__ == "__main__":
    mostrar_interfaz()
