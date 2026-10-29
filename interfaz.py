"""AURA: recomendación de espacios y consulta del catálogo y su disponibilidad."""

import json
from datetime import datetime, time, timedelta, timezone
from html import escape
from pathlib import Path

import streamlit as st

from cargar_datos import cargar_catalogo, unir_franjas
from motor import (Clasificacion, Comprobacion, Espacio, Horario, Justificacion,
                   NOMBRES, Observacion, Preferencia, Solicitud,
                   evaluar, hechos, recomendaciones)

LOGO = Path(__file__).resolve().parent / "imagenes" / "logo_aura.jpg"
ESTADOS = {"recomendada": "Recomendada", "descartada": "Descartada",
           "compatible_con_observaciones": "Compatible con observaciones"}
RECURSOS = tuple(NOMBRES)
EQUIPOS = ("pantalla", "camara", "amplificacion_voz")
ETIQUETAS = {"pantalla": "TV/pantalla", "camara": "Cámara",
             "amplificacion_voz": "Amplificación de voz", "reconfigurable": "Mover mesas y sillas"}
DURACIONES = {"3 horas": 180, "2 horas": 120, "1 hora": 60, "Personalizada": None}


def aplicar_estilo():
    oscuro = st.context.theme.type == "dark"
    superficie, texto, lienzo, panel, marca = (
        ("#1c1921", "#ece7ee", "#131016", "#241c27", "#d58ab7") if oscuro else
        ("#ffffff", "#3d4650", "#ffffff", "#f5ecf2", "#92376d"))
    st.markdown(f"<style>.stApp {{ --aura-superficie: {superficie}; --aura-texto: {texto}; "
                f"--aura-lienzo: {lienzo}; --aura-panel: {panel}; --aura-marca: {marca}; }}</style>",
                unsafe_allow_html=True)
    st.markdown("""
        <style>
        .stApp { background: var(--aura-lienzo); }
        .block-container { max-width: 1500px; padding: 2rem 2.5rem 2.5rem; }
        h1, h2, h3 { letter-spacing: -0.025em; }
        [data-testid="stSidebar"] {
            background: var(--aura-panel);
            border-right: 1px solid color-mix(in srgb, var(--aura-texto) 12%, transparent);
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.65rem; }
        [data-testid="stSidebar"] h2 { font-size: 1.7rem; }
        [data-testid="stSidebar"] h3 { font-size: 1.15rem; }
        @media (min-width: 1100px) {
            [data-testid="stSidebar"][aria-expanded="true"] {
                width: 420px !important; min-width: 420px !important; max-width: 420px !important;
            }
        }
        @media (min-width: 769px) and (max-width: 1099px) {
            [data-testid="stSidebar"][aria-expanded="true"] {
                width: 360px !important; min-width: 360px !important; max-width: 360px !important;
            }
        }
        .st-key-aura_header { margin-bottom: 0.8rem; }
        .aura-titulo {
            font-size: clamp(2rem, 3.2vw, 3.5rem); line-height: 1.08;
            font-weight: 750; color: var(--aura-texto); margin: 0 0 1.2rem;
        }
        .aura-destacado { display: block; color: var(--aura-marca); }
        .aura-intro { font-size: 1.16rem; line-height: 1.5; margin-bottom: 1rem; }
        .aura-aviso {
            display: inline-block; padding: 0.4rem 0.7rem; border-radius: 7px;
            color: var(--aura-marca);
            background: color-mix(in srgb, var(--aura-marca) 8%, var(--aura-superficie));
            font-weight: 600; font-size: 0.88rem;
        }
        [class*="st-key-aura_opcion_"], [class*="st-key-aura_espacio_"] {
            background: var(--aura-superficie); color: var(--aura-texto);
            border: 1px solid color-mix(in srgb, var(--aura-marca) 24%, transparent);
            border-radius: 14px; padding: 1.25rem;
        }
        .st-key-aura_catalogo { margin: 0.6rem 0 1.2rem; }
        .st-key-aura_opcion_1 { border: 2px solid var(--aura-marca); }
        .aura-etiquetas { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.35rem 0; }
        .aura-etiqueta {
            background: color-mix(in srgb, var(--aura-texto) 6%, var(--aura-superficie));
            color: var(--aura-texto); border-radius: 7px;
            padding: 0.3rem 0.55rem; font-size: 0.84rem;
        }
        .aura-estado { display: inline-block; font-weight: 600; font-size: 0.85rem;
                       padding: 0.35rem 0.7rem; border-radius: 7px; }
        .aura-recomendada { color: #176035; background: #e7f5eb; }
        .aura-observaciones { color: #795100; background: #fff1ce; }
        .aura-primera { color: var(--aura-marca); font-weight: 600;
                        font-size: 0.8rem; letter-spacing: 0.05em; }
        [data-testid="stBaseButton-primary"] {
            background-color: #92376d; border-color: #92376d; color: #ffffff;
            min-height: 2.8rem; border-radius: 9px; font-weight: 600;
        }
        [data-testid="stBaseButton-primary"]:hover {
            background-color: #782958; border-color: #782958; color: #ffffff;
        }
        [data-testid="stBaseButton-secondary"] { border-radius: 9px; }
        @media (max-width: 640px) {
            .block-container { padding: 1rem 1rem 2rem; }
            .st-key-aura_header [data-testid="stImage"] { max-width: 210px; }
            .aura-titulo { font-size: 2rem; }
            .aura-intro { font-size: 1rem; }
            [class*="st-key-aura_opcion_"], [class*="st-key-aura_espacio_"] { padding: 1rem; }
        }
        </style>
    """, unsafe_allow_html=True)


def mostrar_encabezado(espacios, fechas):
    with st.container(key="aura_header"):
        if LOGO.is_file():
            imagen, texto = st.columns([1, 2.1], vertical_alignment="center")
            imagen.image(str(LOGO), width=340)
        else:
            st.caption("AURA · Recomendación de aulas y espacios")
            texto = st.container()
        with texto:
            st.html('<h1 class="aura-titulo">Encontrá el espacio ideal '
                    '<span class="aura-destacado">para tu próxima clase</span></h1>')
            st.html('<p class="aura-intro">Indicá qué necesitás y encontrá aulas '
                    'y espacios con una explicación clara.</p>')
            if fechas:
                st.caption(f"Catálogo simulado · {len(espacios)} espacios · "
                           f"{fechas[0]:%d/%m/%Y} al {fechas[-1]:%d/%m/%Y}")
            st.markdown('<span class="aura-aviso">AURA recomienda aulas y espacios. '
                        'No realiza reservas.</span>', unsafe_allow_html=True)


def fecha_actual():
    """Usa la fecha del navegador; sin contexto, usa la fecha UTC."""
    return (datetime.now(timezone.utc) - timedelta(minutes=st.context.timezone_offset or 0)).date()


def ajustar_camara():
    """Activa y bloquea cámara en híbrida; conserva las elecciones manuales."""
    if st.session_state.get("consulta_modalidad") == "hibrida":
        if not st.session_state.get("consulta_camara", False):
            st.session_state["consulta_camara_automatica"] = True
            st.session_state["consulta_camara"] = True
    elif st.session_state.get("consulta_camara_automatica", False):
        st.session_state["consulta_camara"] = False
        st.session_state["consulta_camara_automatica"] = False


def limpiar_consulta():
    for clave in list(st.session_state):
        if clave.startswith("consulta_") or clave in (
                "resultado", "ver_descartado", "ver_razonamiento"):
            del st.session_state[clave]


def crear_solicitud(actividad="Clase", modalidad="presencial", asistentes=None,
                    fecha=None, inicio=None, duracion=180, obligatorios=(), deseables=(),
                    accesibilidad=False, privacidad=None, privacidad_deseable=None):
    """Convierte los datos del formulario a la estructura que espera evaluar()."""
    if asistentes is None:
        raise ValueError("Completá la cantidad de personas.")
    if fecha is None or inicio is None:
        raise ValueError("Completá la fecha y la hora de inicio.")
    if type(duracion) is not int or not 1 <= duracion <= 1440:
        raise ValueError("Completá una duración de 1 a 1440 minutos.")
    fin = datetime.combine(fecha, inicio) + timedelta(minutes=duracion)
    if fin.date() != fecha:
        raise ValueError("La actividad debe comenzar y terminar dentro del mismo día.")
    obligatorios = list(dict.fromkeys(obligatorios))
    if modalidad == "hibrida" and "camara" not in obligatorios:
        obligatorios.append("camara")
    deseables = [r for r in deseables if r not in obligatorios]
    return {
        "tipo_actividad": actividad, "modalidad": modalidad, "asistentes": asistentes,
        "fecha": fecha, "hora_inicio": inicio, "hora_fin": fin.time(),
        "equipamiento_obligatorio": [r for r in obligatorios if r != "reconfigurable"],
        "equipamiento_deseable": [r for r in deseables if r != "reconfigurable"],
        "requiere_reconfiguracion": "reconfigurable" in obligatorios,
        "prefiere_reconfiguracion": "reconfigurable" in deseables,
        "requiere_accesibilidad": accesibilidad,
        "privacidad_obligatoria": privacidad, "privacidad_deseable": privacidad_deseable,
    }


def mostrar_formulario_completo(fecha_inicial):
    with st.sidebar:
        st.header("Tu actividad")
        st.caption("Elegí los requisitos para recibir una recomendación.")
        actividad = st.text_input("Actividad", value="Clase", key="consulta_actividad")
        asistentes = st.number_input("Cantidad de personas", min_value=1, value=None, step=1,
                                      placeholder="Ej.: 30", key="consulta_asistentes")
        modalidad = st.selectbox("Modalidad", ("presencial", "hibrida"), key="consulta_modalidad",
                                 format_func=lambda x: "Híbrida" if x == "hibrida" else "Presencial",
                                 on_change=ajustar_camara)
        ajustar_camara()
        dia, hora = st.columns(2)
        with dia:
            fecha = st.date_input("Fecha", value=fecha_inicial, format="DD/MM/YYYY", key="consulta_fecha")
        with hora:
            inicio = st.time_input("Hora de inicio", value=time(8), key="consulta_inicio")
        tipo = st.selectbox("Duración", tuple(DURACIONES), key="consulta_duracion_tipo")
        duracion = DURACIONES[tipo]
        if duracion is None:
            duracion = st.number_input("Duración en minutos", min_value=1, max_value=1440,
                                        value=180, step=15, key="consulta_duracion")
        if fecha is not None and inicio is not None and type(duracion) is int:
            fin = datetime.combine(fecha, inicio) + timedelta(minutes=duracion)
            st.caption(f"Finalización: {fin:%d/%m/%Y} a las {fin:%H:%M}.")
        st.divider()
        st.subheader("Requisitos obligatorios")
        obligatorios = []
        for equipo in EQUIPOS:
            if st.checkbox(ETIQUETAS[equipo], key=f"consulta_{equipo}",
                           disabled=equipo == "camara" and modalidad == "hibrida"):
                obligatorios.append(equipo)
        if modalidad == "hibrida":
            st.caption("La cámara es obligatoria en modalidad híbrida.")
        if st.checkbox("Necesito mover mesas y sillas", key="consulta_reconfigurable"):
            obligatorios.append("reconfigurable")
        accesibilidad = st.checkbox("Ruta accesible confirmada", key="consulta_accesibilidad")
        privacidad = st.selectbox("Privacidad mínima", (None, "baja", "media", "alta"),
                                   format_func=lambda n: n.capitalize() if n else "Sin requisito",
                                   key="consulta_privacidad")
        opciones = [r for r in RECURSOS if r not in obligatorios]
        anteriores = st.session_state.get("consulta_deseables", [])
        vigentes = [r for r in anteriores if r in opciones]
        if vigentes != anteriores:
            st.session_state["consulta_deseables"] = vigentes
        with st.expander("Preferencias opcionales"):
            st.caption("Si no se cumplen, el espacio puede seguir siendo una opción.")
            deseables = st.multiselect("Me gustaría, pero no es obligatorio", opciones,
                                        format_func=lambda r: ETIQUETAS[r], key="consulta_deseables",
                                        placeholder="Sin preferencias de equipamiento")
            privacidad_deseable = st.selectbox("Privacidad preferida", (None, "baja", "media", "alta"),
                                               format_func=lambda n: n.capitalize() if n else "Sin preferencia",
                                               key="consulta_privacidad_deseable")
        buscar = st.button("Buscar espacios", type="primary", width="stretch", key="buscar_espacios")
        st.button("Nueva consulta", on_click=limpiar_consulta, key="nueva_consulta", width="stretch",
                   help="Limpia el formulario y el resultado para comenzar otra búsqueda.")
        st.caption("Hay WiFi en todo el edificio. Las notebooks se solicitan en Bedelía.")
    if buscar:
        return dict(actividad=actividad, modalidad=modalidad, asistentes=asistentes, fecha=fecha,
                    inicio=inicio, duracion=duracion, obligatorios=obligatorios, deseables=deseables,
                    accesibilidad=accesibilidad, privacidad=privacidad,
                    privacidad_deseable=privacidad_deseable)
    return None


def filtrar_espacios(espacios, horarios, piso=None, fecha=None, inicio=None, fin=None):
    """Filtra el catálogo; la disponibilidad exige cubrir todo el intervalo pedido."""
    visibles = [e for e in espacios if piso is None or e["piso"] == piso]
    if fecha is not None:
        if inicio is None or fin is None or inicio >= fin:
            raise ValueError("La hora de fin debe ser posterior al inicio, en el mismo día.")
        disponibles = {h["id_espacio"] for h in unir_franjas(horarios)
                       if h["fecha"] == fecha and h["hora_inicio"] <= inicio and fin <= h["hora_fin"]}
        visibles = [e for e in visibles if e["id_espacio"] in disponibles]
    return visibles


def mostrar_catalogo(espacios, horarios, fechas, fecha_inicial):
    with st.container(key="aura_catalogo"):
        st.subheader("Explorá los espacios")
        st.caption("Conocé las aulas y sus características. Para recibir una recomendación, "
                   "completá Tu actividad en el panel lateral.")
        piso = st.selectbox("Piso", [None, *sorted({e["piso"] for e in espacios})],
                            format_func=lambda p: "Todos los pisos" if p is None else
                            ubicacion({"piso": p}), key="catalogo_piso")
        consultar = st.toggle("Consultar disponibilidad", key="catalogo_disponibilidad")
        fecha = inicio = fin = None
        if consultar:
            if not fechas:
                st.info("No hay fechas con horarios cargados para consultar disponibilidad.")
                return
            dia, desde, hasta = st.columns([1.3, 1, 1])
            with dia:
                fecha = st.selectbox("Fecha para consultar", fechas,
                                     index=fechas.index(fecha_inicial) if fecha_inicial in fechas else len(fechas) - 1,
                                     format_func=lambda d: f"{d:%d/%m/%Y}", key="catalogo_fecha")
            with desde:
                inicio = st.time_input("Desde", value=time(8), key="catalogo_inicio")
            with hasta:
                fin = st.time_input("Hasta", value=time(11), key="catalogo_fin")
            st.caption("Disponibilidad según los horarios cargados. El espacio debe estar libre "
                       "durante todo el intervalo. Esta consulta no genera reservas.")
        try:
            visibles = filtrar_espacios(espacios, horarios, piso, fecha, inicio, fin)
        except ValueError as error:
            st.error(str(error))
            return
        st.caption(f"{len(visibles)} de {len(espacios)} espacios" +
                   (f" · Disponibles el {fecha:%d/%m/%Y}, de {inicio:%H:%M} a {fin:%H:%M}."
                    if consultar else " · Sin filtrar por disponibilidad."))
        if not visibles:
            st.info("No hay espacios que coincidan con estos filtros. Probá otro piso u horario.")
        for comienzo in range(0, len(visibles), 2):
            columnas = st.columns(2)
            for indice, espacio in enumerate(visibles[comienzo:comienzo + 2]):
                with columnas[indice], st.container(key=f"aura_espacio_{espacio['id_espacio']}"):
                    st.subheader(espacio["nombre"])
                    st.caption(f"{espacio['tipo'].capitalize()} · {ubicacion(espacio)} · {espacio['id_espacio']}")
                    st.write(f"Capacidad: **{espacio['capacidad']} personas**")
                    if consultar:
                        st.markdown('<span class="aura-estado aura-recomendada">Disponible en este horario</span>',
                                    unsafe_allow_html=True)
                    mostrar_caracteristicas(espacio)


def guardar_resultado(motor, espacios, solicitud):
    """Conserva la consulta ejecutada; editar los campos no recalcula el resultado."""
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


def ubicacion(espacio):
    piso = espacio["piso"]
    return "Planta baja" if piso == 0 else f"Subsuelo · Piso −{abs(piso)}" if piso < 0 else f"Piso {piso}"


def mostrar_caracteristicas(espacio):
    etiquetas = [ETIQUETAS[r] for r in EQUIPOS if espacio.get(r) is True]
    if not etiquetas:
        etiquetas.append("Sin equipos audiovisuales")
    etiquetas.append("Reconfigurable" if espacio.get("reconfigurable") is True else "Mesas y sillas fijas")
    etiquetas.append("WiFi" if espacio.get("wifi") is True else "Sin WiFi")
    ruta = espacio.get("ruta_accesible")
    etiquetas.append("Ruta accesible" if ruta is True else
                     "Sin ruta accesible" if ruta is False else "Accesibilidad sin confirmar")
    etiquetas.append(f"Privacidad {espacio['privacidad']}")
    st.markdown('<div class="aura-etiquetas">' +
                "".join(f'<span class="aura-etiqueta">{escape(t)}</span>' for t in etiquetas) +
                '</div>', unsafe_allow_html=True)


def mostrar_tarjeta(r, opcion, numero):
    codigo = opcion["id_espacio"]
    espacio = r["espacios"][codigo]
    with st.container(key=f"aura_opcion_{numero}"):
        st.markdown(f'<div class="aura-primera">{"PRIMERA OPCIÓN" if numero == 1 else "ALTERNATIVA " + str(numero - 1)}</div>',
                    unsafe_allow_html=True)
        st.subheader(espacio["nombre"])
        clase = "aura-recomendada" if opcion["estado"] == "recomendada" else "aura-observaciones"
        st.markdown(f'<span class="aura-estado {clase}">{ESTADOS[opcion["estado"]]}</span>',
                    unsafe_allow_html=True)
        st.write(f"**{ubicacion(espacio)}** · Código: {codigo}")
        st.write(f"Capacidad: **{espacio['capacidad']} personas**")
        st.write(f"Lugares sobrantes: **{opcion['holgura']}**")
        if opcion["preferencias_totales"]:
            st.write(f"Preferencias cumplidas: **{opcion['preferencias_cumplidas']} de {opcion['preferencias_totales']}**")
        mostrar_caracteristicas(espacio)
        for aviso in r["observaciones"]:
            if aviso["id_espacio"] == codigo:
                st.warning(aviso["motivo"])
        with st.expander("Ver por qué es una opción"):
            for h in r["comprobaciones"]:
                if h["id_espacio"] == codigo:
                    st.write("✓ " + h["motivo"])


def mostrar_resultado(r):
    s, espacios = r["solicitud"], r["espacios"]
    st.subheader("Resultado de tu búsqueda")
    fecha = datetime.strptime(s["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")
    st.write(f"**{s['tipo_actividad']}** · {s['asistentes']} personas · "
             f"{fecha} · {s['hora_inicio'][:5]} a {s['hora_fin'][:5]}")
    st.caption("Resultado de la última consulta ejecutada. Si cambiás los datos, presioná Buscar espacios.")
    if not r["opciones"]:
        st.warning("Ningún espacio cumple todos los requisitos obligatorios.")
        st.caption("Revisá los espacios descartados para conocer los motivos.")
    else:
        st.caption("Orden: más preferencias cumplidas y luego menos lugares sobrantes.")
        opciones = r["opciones"][:4]
        if len(r["opciones"]) > 4:
            st.caption(f"Se muestran las primeras 4 de {len(r['opciones'])} opciones viables.")
        for inicio in range(0, len(opciones), 2):
            columnas = st.columns(2)
            for indice, opcion in enumerate(opciones[inicio:inicio + 2]):
                with columnas[indice]:
                    mostrar_tarjeta(r, opcion, inicio + indice + 1)
    descartados = sorted(h["id_espacio"] for h in r["clasificaciones"] if h["estado"] == "descartada")
    with st.expander(f"Espacios descartados ({len(descartados)})"):
        if descartados:
            filas = []
            for codigo in descartados:
                motivos = [h["motivo"] for h in r["comprobaciones"]
                           if h["id_espacio"] == codigo and not h["cumple"]]
                filas.append({"Espacio": espacios[codigo]["nombre"], "Ubicación": ubicacion(espacios[codigo]),
                              "Motivos": " ".join(motivos)})
            st.dataframe(filas, hide_index=True, width="stretch")
            codigo = st.selectbox("Ver explicación de un espacio descartado", descartados,
                                  format_func=lambda c: f"{espacios[c]['nombre']} · {ubicacion(espacios[c])}",
                                  key="ver_descartado")
            for h in r["comprobaciones"]:
                if h["id_espacio"] == codigo and not h["cumple"]:
                    st.write("• " + h["motivo"])
        else:
            st.write("No se descartó ningún espacio.")
    with st.expander("Ver cómo llegó a la conclusión"):
        codigo = st.selectbox("Espacio para consultar el razonamiento", sorted(espacios),
                              format_func=lambda c: f"{espacios[c]['nombre']} · {ubicacion(espacios[c])}",
                              key="ver_razonamiento")
        st.code("\n".join(f"{p['regla']}: {p['motivo']}" for p in r["traza"] if p["id_espacio"] == codigo),
                language=None)
        st.write("Hechos iniciales: solicitud, catálogo, franjas libres y preferencias.")
        st.json(r["iniciales"], expanded=False)
        st.write("Hechos deducidos por las reglas.")
        st.json(r["derivados"], expanded=False)
        st.write("Reglas activadas en orden de ejecución.")
        st.dataframe(r["traza"], hide_index=True, width="stretch")


def mostrar_pie():
    st.divider()
    st.caption("AURA recomienda aulas y espacios. No realiza reservas.")
    st.caption("Desarrollado por el Grupo B · Análisis de Datos II · Segundo cuatrimestre de 2026.")


def mostrar_interfaz():
    st.set_page_config(page_title="AURA · Recomendación de espacios",
                       page_icon=str(LOGO) if LOGO.is_file() else "🏫",
                       layout="wide", initial_sidebar_state="auto")
    aplicar_estilo()
    try:
        espacios, horarios = cargar_catalogo()
    except (OSError, ValueError) as error:
        st.error(f"No se pudo cargar el catálogo: {error}")
        mostrar_pie()
        st.stop()
    fechas = sorted({h["fecha"] for h in horarios})
    hoy = fecha_actual()
    fechas_vigentes = [f for f in fechas if f >= hoy]
    fecha_inicial = fechas_vigentes[0] if fechas_vigentes else hoy
    datos = mostrar_formulario_completo(fecha_inicial)
    mostrar_encabezado(espacios, fechas)
    if not fechas_vigentes:
        st.warning("No hay fechas vigentes en el catálogo. Actualizá horarios.csv para consultar nuevas fechas.")
    if datos is not None:
        st.session_state.pop("resultado", None)
        try:
            solicitud = crear_solicitud(**datos)
            with st.spinner("Buscando espacios para tu actividad…"):
                motor = evaluar(espacios, solicitud, horarios)
                guardar_resultado(motor, espacios, solicitud)
        except ValueError as error:
            st.error(str(error))
    if "resultado" in st.session_state:
        mostrar_resultado(st.session_state["resultado"])
        with st.expander("Ver todos los espacios"):
            mostrar_catalogo(espacios, horarios, fechas, fecha_inicial)
    else:
        mostrar_catalogo(espacios, horarios, fechas, fecha_inicial)
    mostrar_pie()


if __name__ == "__main__":
    mostrar_interfaz()
