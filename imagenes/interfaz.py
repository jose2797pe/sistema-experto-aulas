"""AURA: recomendacion de espacios y consulta del catalogo y su disponibilidad."""

import json
from datetime import datetime, time, timedelta, timezone
from html import escape
from pathlib import Path

import streamlit as st

from cargar_datos import cargar_catalogo, se_superponen
from motor import (Clasificacion, Comprobacion, Espacio, Reserva, Justificacion,
                   NIVELES, NOMBRES, Observacion, Preferencia, Solicitud,
                   evaluar, hechos, recomendaciones)

LOGO = Path(__file__).resolve().parent / "imagenes" / "logo_aura.jpg"
ESTADOS = {"recomendada": "Recomendada", "descartada": "Descartada",
           "compatible_con_observaciones": "Compatible con observaciones"}
RECURSOS = tuple(NOMBRES)
EQUIPOS = ("pantalla", "camara", "amplificacion_voz")
ETIQUETAS = {"pantalla": "TV/pantalla", "camara": "Camara",
             "amplificacion_voz": "Amplificacion de voz", "reconfigurable": "Mover mesas y sillas"}
CARACTERISTICAS_CATALOGO = {**{r: ETIQUETAS[r] for r in EQUIPOS},
                           "ruta_accesible": "Ruta accesible confirmada",
                           "reconfigurable": "Mobiliario reconfigurable"}
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
        .block-container [data-testid="stVerticalBlock"] { gap: 0.5rem; }
        .block-container [data-testid="stMarkdownContainer"],
        .block-container [data-testid="stCaptionContainer"] { margin-bottom: 0; }
        .block-container [data-testid="stMarkdownContainer"] p,
        .block-container [data-testid="stCaptionContainer"] p { margin: 0; }
        .block-container h2, .block-container h3 {
            margin: 0; padding: 0.2rem 0 0.25rem; line-height: 1.25;
        }
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
        .st-key-aura_header { margin-bottom: 0.5rem; }
        .st-key-aura_header [data-testid="stVerticalBlock"] { gap: 0.4rem; }
        .aura-titulo {
            font-size: clamp(2rem, 3.2vw, 3.5rem); line-height: 1.08;
            font-weight: 750; color: var(--aura-texto); margin: 0 0 0.4rem;
        }
        .aura-destacado { display: block; color: var(--aura-marca); }
        .aura-intro { font-size: 1.16rem; line-height: 1.4; margin: 0; }
        .aura-aviso {
            display: inline-block; padding: 0.4rem 0.7rem; border-radius: 7px;
            color: var(--aura-marca);
            background: color-mix(in srgb, var(--aura-marca) 8%, var(--aura-superficie));
            font-weight: 600; font-size: 0.88rem;
        }
        .aura-guia {
            display: flex; align-items: center; gap: 0.6rem;
            color: color-mix(in srgb, var(--aura-texto) 80%, transparent);
            font-size: 0.85rem; font-weight: 400;
            line-height: 1.4; margin: 0.1rem 0 0.25rem;
        }
        .aura-flecha { font-size: 1.1rem; line-height: 1; flex-shrink: 0; }
        .aura-resumen {
            color: var(--aura-texto); font-size: 0.94rem; line-height: 1.5;
            background: color-mix(in srgb, var(--aura-marca) 5%, var(--aura-superficie));
            border: 1px solid color-mix(in srgb, var(--aura-marca) 18%, transparent);
            border-radius: 9px; padding: 0.7rem 0.9rem;
        }
        .aura-resumen strong { color: var(--aura-marca); }
        .aura-flujo {
            display: grid; grid-template-columns: 1fr 28px 1.3fr 40px 1.5fr 28px 1.5fr;
            gap: 0.4rem; margin: 0.3rem 0; align-items: stretch;
        }
        .aura-flujo-caja {
            border: 1px solid color-mix(in srgb, var(--aura-marca) 25%, transparent);
            background: var(--aura-superficie); color: var(--aura-texto);
            border-radius: 9px; padding: 0.6rem 0.7rem; min-height: 3rem;
            display: flex; align-items: center; justify-content: center;
            text-align: center; font-size: 0.9rem; line-height: 1.35;
        }
        .aura-flujo-inicio { grid-column: 1; grid-row: 1; }
        .aura-flujo-entrada { grid-column: 2; grid-row: 1; }
        .aura-flujo-pregunta {
            grid-column: 3; grid-row: 1; font-weight: 600;
            background: color-mix(in srgb, var(--aura-marca) 5%, var(--aura-superficie));
        }
        .aura-flujo-si { grid-column: 4; grid-row: 1; }
        .aura-flujo-preferencias { grid-column: 5; grid-row: 1; }
        .aura-flujo-salida { grid-column: 6; grid-row: 1; }
        .aura-flujo-fin { grid-column: 7; grid-row: 1; }
        .aura-flujo-no { grid-column: 3; grid-row: 2; flex-direction: column; }
        .aura-flujo-descartar { grid-column: 3; grid-row: 3; }
        .aura-flujo-conector {
            display: flex; align-items: center; justify-content: center;
            gap: 0.15rem; color: var(--aura-marca); font-size: 0.8rem;
        }
        .aura-flujo-flecha { font-size: 1.2rem; line-height: 1; }
        @media (max-width: 1200px) {
            .aura-flujo { grid-template-columns: 1fr 1fr; }
            .aura-flujo-inicio { grid-column: 1 / -1; grid-row: 1; }
            .aura-flujo-entrada { grid-column: 1 / -1; grid-row: 2; }
            .aura-flujo-pregunta { grid-column: 1 / -1; grid-row: 3; }
            .aura-flujo-no { grid-column: 1; grid-row: 4; }
            .aura-flujo-si { grid-column: 2; grid-row: 4; flex-direction: column; }
            .aura-flujo-descartar { grid-column: 1; grid-row: 5; align-self: start; }
            .aura-flujo-preferencias { grid-column: 2; grid-row: 5; }
            .aura-flujo-salida { grid-column: 2; grid-row: 6; }
            .aura-flujo-fin { grid-column: 2; grid-row: 7; }
            .aura-flujo-entrada .aura-flujo-flecha,
            .aura-flujo-si .aura-flujo-flecha,
            .aura-flujo-salida .aura-flujo-flecha { transform: rotate(90deg); }
        }
        [class*="st-key-aura_opcion_"], [class*="st-key-aura_espacio_"] {
            background: var(--aura-superficie); color: var(--aura-texto);
            border: 1px solid color-mix(in srgb, var(--aura-marca) 24%, transparent);
            border-radius: 14px; padding: 1.25rem;
        }
        .st-key-aura_catalogo { margin: 0.3rem 0 0.8rem; }
        .st-key-aura_catalogo h2 {
            font-size: clamp(1.75rem, 2.2vw, 2.2rem); font-weight: 750;
            color: var(--aura-texto); line-height: 1.2; text-wrap: balance;
        }
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
            .aura-flecha { transform: rotate(90deg); }
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
            st.caption("AURA \xb7 Recomendacion de aulas y espacios")
            texto = st.container()
        with texto:
            st.html('<h1 class="aura-titulo">Encontra el espacio ideal '
                    '<span class="aura-destacado">para tu proxima clase</span></h1>')
            st.html('<p class="aura-intro">Indica que necesitas y encontra aulas '
                    'segun sus caracteristicas y las reservas ficticias existentes.</p>')
            detalle = f"Datos simulados \xb7 {len(espacios)} espacios"
            if fechas:
                detalle += (f" \xb7 Reservas ficticias del {fechas[0]:%d/%m/%Y} "
                            f"al {fechas[-1]:%d/%m/%Y}.")
            st.caption(detalle)
            st.markdown('<span class="aura-aviso">AURA recomienda aulas y espacios. '
                        'No realiza reservas.</span>', unsafe_allow_html=True)
            with st.container(key="aura_autoria"):
                st.caption("Desarrollado por el Grupo B \xb7 Analisis de Datos II \xb7 Segundo cuatrimestre de 2026.")


def fecha_actual():
    """Usa la fecha del navegador; sin contexto, usa la fecha UTC."""
    return (datetime.now(timezone.utc) - timedelta(minutes=st.context.timezone_offset or 0)).date()


def ajustar_camara():
    """Activa y bloquea camara en hibrida; conserva las elecciones manuales."""
    if st.session_state.get("consulta_modalidad") == "hibrida":
        if not st.session_state.get("consulta_camara", False):
            st.session_state["consulta_camara_automatica"] = True
            st.session_state["consulta_camara"] = True
    elif st.session_state.get("consulta_camara_automatica", False):
        st.session_state["consulta_camara"] = False
        st.session_state["consulta_camara_automatica"] = False


def limpiar_consulta():
    for clave in list(st.session_state):
        if clave.startswith(("consulta_", "catalogo_")) or clave in (
                "resultado", "ver_descartado", "ver_razonamiento"):
            del st.session_state[clave]


def volver_al_catalogo():
    """Vuelve a mostrar todos los espacios y conserva los datos de Tu actividad."""
    for clave in list(st.session_state):
        if clave.startswith("catalogo_") or clave in (
                "resultado", "ver_descartado", "ver_razonamiento"):
            del st.session_state[clave]


def limpiar_filtros():
    """Muestra todo el catalogo sin modificar los datos de Tu actividad."""
    valores = {"catalogo_piso": None, "catalogo_caracteristicas": [],
               "catalogo_privacidad": None, "catalogo_disponibilidad": False}
    for clave in list(st.session_state):
        if clave.startswith("catalogo_") and clave not in valores:
            del st.session_state[clave]
    # Asignar los valores explicitamente tambien reinicia los controles del navegador.
    st.session_state.update(valores)


def crear_solicitud(actividad="Clase", modalidad="presencial", asistentes=None,
                    fecha=None, inicio=None, duracion=180, obligatorios=(), deseables=(),
                    accesibilidad=False, privacidad=None, privacidad_deseable=None):
    """Convierte los datos del formulario a la estructura que espera evaluar()."""
    if asistentes is None:
        raise ValueError("Completa la cantidad de personas.")
    if fecha is None or inicio is None:
        raise ValueError("Completa la fecha y la hora de inicio.")
    if type(duracion) is not int or not 1 <= duracion <= 1440:
        raise ValueError("Completa una duracion de 1 a 1440 minutos.")
    fin = datetime.combine(fecha, inicio) + timedelta(minutes=duracion)
    if fin.date() != fecha:
        raise ValueError("La actividad debe comenzar y terminar dentro del mismo dia.")
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
        st.caption("Elegi los requisitos para recibir una recomendacion.")
        actividad = st.text_input("Actividad", value="Clase", key="consulta_actividad")
        asistentes = st.number_input("Cantidad de personas", min_value=1, value=None, step=1,
                                      placeholder="Ej.: 30", key="consulta_asistentes")
        modalidad = st.selectbox("Modalidad", ("presencial", "hibrida"), key="consulta_modalidad",
                                 format_func=lambda x: "Hibrida" if x == "hibrida" else "Presencial",
                                 on_change=ajustar_camara)
        ajustar_camara()
        dia, hora = st.columns(2)
        with dia:
            fecha = st.date_input("Fecha", value=fecha_inicial, format="DD/MM/YYYY", key="consulta_fecha")
        with hora:
            inicio = st.time_input("Hora de inicio", value=time(8), key="consulta_inicio")
        tipo = st.selectbox("Duracion", tuple(DURACIONES), key="consulta_duracion_tipo")
        duracion = DURACIONES[tipo]
        if duracion is None:
            duracion = st.number_input("Duracion en minutos", min_value=1, max_value=1440,
                                        value=180, step=15, key="consulta_duracion")
        st.divider()
        st.subheader("Requisitos obligatorios")
        obligatorios = []
        for equipo in EQUIPOS:
            if st.checkbox(ETIQUETAS[equipo], key=f"consulta_{equipo}",
                           disabled=equipo == "camara" and modalidad == "hibrida"):
                obligatorios.append(equipo)
        if modalidad == "hibrida":
            st.caption("La camara es obligatoria en modalidad hibrida.")
        if st.checkbox("Necesito mover mesas y sillas", key="consulta_reconfigurable"):
            obligatorios.append("reconfigurable")
        accesibilidad = st.checkbox("Ruta accesible confirmada", key="consulta_accesibilidad")
        privacidad = st.selectbox("Privacidad minima", (None, "baja", "media", "alta"),
                                   format_func=lambda n: n.capitalize() if n else "Sin requisito",
                                   key="consulta_privacidad")
        opciones = [r for r in RECURSOS if r not in obligatorios]
        anteriores = st.session_state.get("consulta_deseables", [])
        vigentes = [r for r in anteriores if r in opciones]
        if vigentes != anteriores:
            st.session_state["consulta_deseables"] = vigentes
        with st.expander("Preferencias opcionales"):
            st.caption("Si no se cumplen, el espacio puede seguir siendo una opcion.")
            deseables = st.multiselect("Me gustaria, pero no es obligatorio", opciones,
                                        format_func=lambda r: ETIQUETAS[r], key="consulta_deseables",
                                        placeholder="Sin preferencias de equipamiento")
            privacidad_deseable = st.selectbox("Privacidad preferida", (None, "baja", "media", "alta"),
                                               format_func=lambda n: n.capitalize() if n else "Sin preferencia",
                                               key="consulta_privacidad_deseable")
        buscar = st.button("Buscar espacios", type="primary", width="stretch", key="buscar_espacios")
        st.button("Nueva consulta", on_click=limpiar_consulta, key="nueva_consulta", width="stretch",
                   help="Limpia el formulario, los filtros y el resultado para comenzar otra busqueda.")
        st.caption("Hay WiFi en todo el edificio. Las notebooks se solicitan en Bedelia.")
    if buscar:
        return dict(actividad=actividad, modalidad=modalidad, asistentes=asistentes, fecha=fecha,
                    inicio=inicio, duracion=duracion, obligatorios=obligatorios, deseables=deseables,
                    accesibilidad=accesibilidad, privacidad=privacidad,
                    privacidad_deseable=privacidad_deseable)
    return None


def filtrar_espacios(espacios, reservas, piso=None, fecha=None, inicio=None, fin=None,
                     equipos=(), accesibilidad=False, privacidad=None, reconfigurable=False):
    """Filtra caracteristicas y excluye espacios con reservas que se superpongan."""
    visibles = [e for e in espacios if (piso is None or e["piso"] == piso)
                and all(e.get(recurso) is True for recurso in equipos)
                and (not accesibilidad or e["ruta_accesible"] is True)
                and (privacidad is None or NIVELES[e["privacidad"]] >= NIVELES[privacidad])
                and (not reconfigurable or e["reconfigurable"] is True)]
    if any(valor is not None for valor in (fecha, inicio, fin)):
        if any(valor is None for valor in (fecha, inicio, fin)):
            raise ValueError("Completa la fecha, la hora de inicio y la hora de fin.")
        if inicio >= fin:
            raise ValueError("La hora de fin debe ser posterior al inicio, en el mismo dia.")
        ocupados = {r["id_espacio"] for r in reservas
                    if r["fecha"] == fecha and se_superponen(inicio, fin, r["hora_inicio"], r["hora_fin"])}
        visibles = [e for e in visibles if e["id_espacio"] not in ocupados]
    return visibles


def mostrar_catalogo(espacios, reservas, fecha_inicial):
    with st.container(key="aura_catalogo"):
        st.header("Explora todos los espacios \u2193")
        st.markdown("Conoce todas las aulas y el auditorio, sus caracteristicas y "
                    "**filtra segun lo que necesitas.**")
        st.markdown('<div class="aura-guia"><span class="aura-flecha" aria-hidden="true">\u2190</span>'
                    '<span>Si queres una recomendacion, completa el formulario.</span></div>',
                    unsafe_allow_html=True)
        columna_piso, columna_caracteristicas, columna_privacidad = st.columns([1, 2, 1])
        with columna_piso:
            piso = st.selectbox("Piso", [None, *sorted({e["piso"] for e in espacios})],
                                format_func=lambda p: "Todos los pisos" if p is None else
                                ubicacion({"piso": p}), key="catalogo_piso", placeholder="Todos los pisos")
        with columna_caracteristicas:
            caracteristicas = st.multiselect("Caracteristicas del espacio", tuple(CARACTERISTICAS_CATALOGO),
                                               format_func=lambda r: CARACTERISTICAS_CATALOGO[r],
                                               placeholder="Sin filtrar", key="catalogo_caracteristicas")
        with columna_privacidad:
            privacidad = st.selectbox("Privacidad minima", (None, "baja", "media", "alta"),
                                      format_func=lambda p: p.capitalize() if p else "Sin filtrar",
                                      key="catalogo_privacidad", placeholder="Sin filtrar")
        nuevos = dict(piso=piso, equipos=tuple(r for r in caracteristicas if r in EQUIPOS),
                      accesibilidad="ruta_accesible" in caracteristicas, privacidad=privacidad,
                      reconfigurable="reconfigurable" in caracteristicas)
        consultar = st.toggle("Consultar disponibilidad", key="catalogo_disponibilidad")
        if consultar:
            st.caption("Se excluyen las aulas con reservas ficticias que se superpongan. "
                       "Si no hay reservas registradas para esa fecha y horario, el aula se considera disponible.")
            dia, desde, hasta = st.columns([1.3, 1, 1])
            with dia:
                fecha = st.date_input("Fecha para consultar", value=fecha_inicial,
                                      format="DD/MM/YYYY", key="catalogo_fecha")
            with desde:
                inicio = st.time_input("Desde", value=time(8), key="catalogo_inicio")
            with hasta:
                fin = st.time_input("Hasta", value=time(11), key="catalogo_fin")
            nuevos.update(fecha=fecha, inicio=inicio, fin=fin)
        predeterminados = dict(piso=None, equipos=(), accesibilidad=False,
                               privacidad=None, reconfigurable=False)
        aplicados = st.session_state.get("catalogo_filtros", predeterminados)
        columna_aplicar, columna_borrar = st.columns([2, 1])
        with columna_aplicar:
            aplicar = st.button("Aplicar filtros", type="primary", width="stretch", key="catalogo_aplicar")
        with columna_borrar:
            st.button("Borrar filtros", on_click=limpiar_filtros, width="stretch", key="catalogo_borrar")
        if aplicar:
            try:
                if consultar and any(nuevos[campo] is None for campo in ("fecha", "inicio", "fin")):
                    raise ValueError("Completa la fecha, la hora de inicio y la hora de fin.")
                filtrar_espacios(espacios, reservas, **nuevos)
            except ValueError as error:
                st.error(str(error))
            else:
                aplicados = dict(nuevos)
                st.session_state["catalogo_filtros"] = aplicados
        if nuevos != aplicados:
            st.caption("Tenes cambios sin aplicar. Presiona Aplicar filtros.")
        visibles = filtrar_espacios(espacios, reservas, **aplicados)
        piso_aplicado = aplicados.get("piso")
        filtros = [ubicacion({"piso": piso_aplicado}) if piso_aplicado is not None else "Todos los pisos"]
        caracteristicas_aplicadas = list(aplicados.get("equipos", ()))
        if aplicados.get("accesibilidad"):
            caracteristicas_aplicadas.append("ruta_accesible")
        if aplicados.get("reconfigurable"):
            caracteristicas_aplicadas.append("reconfigurable")
        if caracteristicas_aplicadas:
            filtros.append("Caracteristicas: " + ", ".join(CARACTERISTICAS_CATALOGO[r]
                                                           for r in caracteristicas_aplicadas))
        if aplicados.get("privacidad"):
            filtros.append("Privacidad minima: " + aplicados["privacidad"])
        if aplicados.get("fecha"):
            filtros.append(f"Disponibles el {aplicados['fecha']:%d/%m/%Y}, "
                           f"de {aplicados['inicio']:%H:%M} a {aplicados['fin']:%H:%M}, segun las reservas ficticias.")
        else:
            filtros.append("Sin filtrar por disponibilidad.")
        resumen_filtros = escape(" \xb7 ".join(filtros))
        st.markdown(f'<div class="aura-resumen"><strong>{len(visibles)} de {len(espacios)} espacios</strong>'
                    f' \xb7 {resumen_filtros}</div>', unsafe_allow_html=True)
        if not visibles:
            st.info("No hay espacios que coincidan con estos filtros. Proba cambiar alguna seleccion.")
        for comienzo in range(0, len(visibles), 2):
            columnas = st.columns(2)
            for indice, espacio in enumerate(visibles[comienzo:comienzo + 2]):
                with columnas[indice], st.container(key=f"aura_espacio_{espacio['id_espacio']}"):
                    st.subheader(espacio["nombre"])
                    st.caption(f"{espacio['tipo'].capitalize()} \xb7 {ubicacion(espacio)} \xb7 {espacio['id_espacio']}")
                    st.write(f"Capacidad: **{espacio['capacidad']} personas**")
                    if aplicados.get("fecha"):
                        st.markdown('<span class="aura-estado aura-recomendada">Sin reservas en este horario</span>',
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
        if isinstance(hecho, (Solicitud, Espacio, Reserva, Preferencia)):
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
    st.session_state["ver_razonamiento"] = (resultado["opciones"][0]["id_espacio"]
                                           if resultado["opciones"] else sorted(resultado["espacios"])[0])
    st.session_state.pop("ver_descartado", None)


def ubicacion(espacio):
    piso = espacio["piso"]
    return "Planta baja" if piso == 0 else f"Subsuelo \xb7 Piso \u2212{abs(piso)}" if piso < 0 else f"Piso {piso}"


def mostrar_caracteristicas(espacio):
    etiquetas = [ETIQUETAS[r] for r in EQUIPOS if espacio.get(r) is True]
    if not etiquetas:
        etiquetas.append("Sin equipos audiovisuales")
    etiquetas.append("Reconfigurable" if espacio.get("reconfigurable") is True else "Sin permiso para mover mesas y sillas")
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
        st.markdown(f'<div class="aura-primera">{"PRIMERA OPCION" if numero == 1 else "ALTERNATIVA " + str(numero - 1)}</div>',
                    unsafe_allow_html=True)
        st.subheader(espacio["nombre"])
        clase = "aura-recomendada" if opcion["estado"] == "recomendada" else "aura-observaciones"
        st.markdown(f'<span class="aura-estado {clase}">{ESTADOS[opcion["estado"]]}</span>',
                    unsafe_allow_html=True)
        st.write(f"**{ubicacion(espacio)}** \xb7 Codigo: {codigo}")
        st.write(f"Capacidad: **{espacio['capacidad']} personas**")
        st.write(f"Lugares sobrantes: **{opcion['holgura']}**")
        if opcion["preferencias_totales"]:
            st.write(f"Preferencias cumplidas: **{opcion['preferencias_cumplidas']} de {opcion['preferencias_totales']}**")
        mostrar_caracteristicas(espacio)
        cumplidas = []
        for hecho in r["derivados"]:
            datos = hecho["datos"]
            if (hecho["tipo"] == "EvaluacionPreferencia" and datos["id_espacio"] == codigo
                    and datos["cumple"]):
                criterio = datos["criterio"]
                cumplidas.append("privacidad minima " + r["solicitud"]["privacidad_deseable"]
                                  if criterio == "privacidad" else NOMBRES[criterio])
        if cumplidas:
            introduccion = ("Cumple tu preferencia opcional" if opcion["preferencias_totales"] == 1 else
                            "Cumple esta preferencia opcional" if len(cumplidas) == 1 else
                            "Cumple estas preferencias opcionales")
            st.success(f"{introduccion}: {', '.join(cumplidas)}. Por eso se prioriza.")
        for aviso in r["observaciones"]:
            if aviso["id_espacio"] == codigo:
                st.warning(aviso["motivo"])
        with st.expander("Ver por que es una opcion"):
            for h in r["comprobaciones"]:
                if h["id_espacio"] == codigo:
                    st.write("\u2713 " + h["motivo"])


def mostrar_flujo():
    """Guia general; la tabla posterior conserva la ejecucion real de la consulta."""
    st.caption("Flujo general de evaluacion")
    st.html('''
        <div class="aura-flujo" role="group" aria-label="Flujo general de evaluacion">
            <div class="aura-flujo-caja aura-flujo-inicio">Formulario, espacios y reservas registradas</div>
            <div class="aura-flujo-conector aura-flujo-entrada"><span class="aura-flujo-flecha" aria-hidden="true">\u2192</span></div>
            <div class="aura-flujo-caja aura-flujo-pregunta">\xbfCumple los requisitos obligatorios?</div>
            <div class="aura-flujo-conector aura-flujo-si">Si<span class="aura-flujo-flecha" aria-hidden="true">\u2192</span></div>
            <div class="aura-flujo-caja aura-flujo-preferencias">Evaluar preferencias opcionales y observaciones</div>
            <div class="aura-flujo-conector aura-flujo-salida"><span class="aura-flujo-flecha" aria-hidden="true">\u2192</span></div>
            <div class="aura-flujo-caja aura-flujo-fin">Clasificar y ordenar recomendaciones</div>
            <div class="aura-flujo-conector aura-flujo-no">No<span class="aura-flujo-flecha" aria-hidden="true">\u2193</span></div>
            <div class="aura-flujo-caja aura-flujo-descartar">Descartar aula</div>
        </div>
    ''')
    st.caption("**Criterio de orden final:** primero se priorizan las aulas con mas preferencias "
               "opcionales cumplidas y, despues, las que tienen menor cantidad de lugares sobrantes.")


def mostrar_resultado(r):
    s, espacios = r["solicitud"], r["espacios"]
    st.subheader("Resultado de tu busqueda")
    fecha = datetime.strptime(s["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")
    st.write(f"**{s['tipo_actividad']}** \xb7 {s['asistentes']} personas \xb7 "
             f"{fecha} \xb7 {s['hora_inicio'][:5]} a {s['hora_fin'][:5]}")
    st.caption("Resultado de la ultima consulta ejecutada. Si cambias los datos, presiona Buscar espacios.")
    st.caption("La disponibilidad se calcula con las reservas ficticias registradas. Esta consulta no reserva el espacio.")
    if not r["opciones"]:
        st.warning("Ningun espacio cumple todos los requisitos obligatorios.")
        st.caption("Revisa los espacios descartados para conocer los motivos.")
    else:
        st.caption("Orden: mas preferencias cumplidas y luego menos lugares sobrantes.")
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
                filas.append({"Espacio": espacios[codigo]["nombre"], "Ubicacion": ubicacion(espacios[codigo]),
                              "Motivos": " ".join(motivos)})
            st.dataframe(filas, hide_index=True, width="stretch")
            codigo = st.selectbox("Ver explicacion de un espacio descartado", descartados,
                                  format_func=lambda c: f"{espacios[c]['nombre']} \xb7 {ubicacion(espacios[c])}",
                                  key="ver_descartado")
            for h in r["comprobaciones"]:
                if h["id_espacio"] == codigo and not h["cumple"]:
                    st.write("\u2022 " + h["motivo"])
        else:
            st.write("No se descarto ningun espacio.")
    with st.expander("Ver como llego a la conclusion"):
        codigo = st.selectbox("Espacio para consultar el razonamiento", sorted(espacios),
                              format_func=lambda c: f"{espacios[c]['nombre']} \xb7 {ubicacion(espacios[c])}",
                              key="ver_razonamiento")
        st.code("\n".join(f"{p['regla']}: {p['motivo']}" for p in r["traza"] if p["id_espacio"] == codigo),
                language=None)
        mostrar_flujo()
        st.write("Reglas activadas en orden de ejecucion.")
        st.dataframe(r["traza"], hide_index=True, width="stretch")


def mostrar_pie():
    st.divider()
    st.caption("AURA recomienda aulas y espacios. No realiza reservas.")


def mostrar_interfaz():
    st.set_page_config(page_title="AURA \xb7 Recomendacion de espacios",
                       page_icon=str(LOGO) if LOGO.is_file() else "\U0001f3eb",
                       layout="wide", initial_sidebar_state="auto")
    aplicar_estilo()
    try:
        espacios, reservas = cargar_catalogo()
    except (OSError, ValueError) as error:
        st.error(f"No se pudo cargar el catalogo: {error}")
        mostrar_pie()
        st.stop()
    fechas = sorted({r["fecha"] for r in reservas})
    hoy = fecha_actual()
    fechas_vigentes = [f for f in fechas if f >= hoy]
    fecha_inicial = fechas_vigentes[0] if fechas_vigentes else hoy
    datos = mostrar_formulario_completo(fecha_inicial)
    mostrar_encabezado(espacios, fechas)
    if not reservas:
        st.info("No hay reservas ficticias registradas. Todos los espacios se consideran disponibles "
                "por horario; se evaluan sus caracteristicas segun lo que solicites.")
    elif not fechas_vigentes:
        st.info("Las reservas ficticias cargadas corresponden a fechas pasadas. Podes consultar otras fechas: "
                "si no hay reservas que se superpongan, el espacio se considera disponible.")
    if datos is not None:
        st.session_state.pop("resultado", None)
        try:
            solicitud = crear_solicitud(**datos)
            with st.spinner("Buscando espacios para tu actividad\u2026"):
                motor = evaluar(espacios, solicitud, reservas)
                guardar_resultado(motor, espacios, solicitud)
        except ValueError as error:
            st.error(str(error))
    if "resultado" in st.session_state:
        st.button("Volver a ver todas las aulas", on_click=volver_al_catalogo,
                   key="volver_catalogo", icon=":material/arrow_back:")
        mostrar_resultado(st.session_state["resultado"])
    else:
        mostrar_catalogo(espacios, reservas, fecha_inicial)
    mostrar_pie()


if __name__ == "__main__":
    mostrar_interfaz()
