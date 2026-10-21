
# Experta 1.9.4 usa frozendict 1.2, que necesita este alias en Python 3.11.
import collections
import collections.abc
from datetime import date, time

collections.Mapping = collections.abc.Mapping

from experta import AS, MATCH, NOT, TEST, Fact, KnowledgeEngine, Rule
from cargar_datos import EQUIPAMIENTO, unir_franjas

NIVELES = {None: 0, "baja": 1, "media": 2, "alta": 3}
NOMBRES = {"pantalla": "TV/pantalla", "camara": "cámara",
           "amplificacion_voz": "amplificación de voz",
           "reconfigurable": "permiso para mover mesas y sillas"}
CRITERIOS = ("capacidad", "disponibilidad", "equipamiento", "accesibilidad",
             "privacidad", "reconfiguracion")


class Solicitud(Fact):
    """Datos de una única consulta."""


class Espacio(Fact):
    """Características declaradas de un espacio."""


class Horario(Fact):
    """Franja libre declarada, no una reserva."""


class Comprobacion(Fact):
    """Resultado de revisar una condición obligatoria."""


class Preseleccion(Fact):
    """Resultado conjunto de las seis comprobaciones."""


class AjusteCapacidad(Fact):
    """Lugares sobrantes y existencia de exceso de capacidad."""


class Preferencia(Fact):
    """Condición deseable que no descarta."""


class EvaluacionPreferencia(Fact):
    """Resultado de una preferencia para un espacio viable."""


class ResumenPreferencias(Fact):
    """Cantidad de preferencias cumplidas."""


class Observacion(Fact):
    """Aviso sobre un espacio viable."""


class Clasificacion(Fact):
    """Conclusión final de un espacio."""


class Justificacion(Fact):
    """Regla activada y explicación de lo que concluyó."""


def hechos(motor, clase, codigo=None):
    return [h for h in motor.facts.values() if isinstance(h, clase)
            and (codigo is None or h.get("id_espacio") == codigo)]


def cumple_preferencia(espacio, criterio, valor):
    if criterio == "privacidad":
        return NIVELES[espacio["privacidad"]] >= NIVELES[valor]
    return espacio[criterio] is True


class MotorAulas(KnowledgeEngine):
    def __init__(self):
        self.traza = []
        super().__init__()

    def reset(self, **datos):
        self.traza.clear()
        super().reset(**datos)

    def registrar(self, regla, codigo, motivo):
        paso = {"regla": regla, "id_espacio": codigo, "motivo": motivo}
        self.declare(Justificacion(**paso))
        self.traza.append(paso)

    def comprobar(self, regla, codigo, criterio, cumple, motivo):
        self.declare(Comprobacion(id_espacio=codigo, criterio=criterio,
                                 cumple=cumple, motivo=motivo))
        self.registrar(regla, codigo, motivo)

    def concluir(self, regla, codigo, estado, motivo):
        self.declare(Clasificacion(id_espacio=codigo, estado=estado, motivo=motivo))
        self.registrar(regla, codigo, motivo)

    # R01-R02: capacidad obligatoria. Fuente: brief, RF-03.
    @Rule(Solicitud(asistentes=MATCH.n), Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap),
          TEST(lambda cap, n: cap >= n),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="capacidad")))
    def capacidad_suficiente(self, c, cap, n):
        self.comprobar("R01", c, "capacidad", True,
                       f"Alcanzan los lugares: capacidad {cap}, asistentes {n}.")

    @Rule(Solicitud(asistentes=MATCH.n), Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap),
          TEST(lambda cap, n: cap < n),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="capacidad")))
    def capacidad_insuficiente(self, c, cap, n):
        self.comprobar("R02", c, "capacidad", False,
                       f"Faltan {n - cap} lugares: capacidad {cap}, asistentes {n}.")

    # R03-R04: toda la actividad debe entrar en una franja libre. RF-03.
    # MATCH une los datos del mismo espacio y fecha. TEST realiza la comparación.
    @Rule(Solicitud(fecha=MATCH.fecha, hora_inicio=MATCH.inicio, hora_fin=MATCH.fin),
          Espacio(id_espacio=MATCH.c),
          Horario(id_espacio=MATCH.c, fecha=MATCH.fecha,
                  hora_inicio=MATCH.desde, hora_fin=MATCH.hasta),
          TEST(lambda desde, hasta, inicio, fin: desde <= inicio and fin <= hasta),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="disponibilidad")), salience=10)
    def horario_confirmado(self, c, fecha, inicio, fin, desde, hasta):
        self.comprobar("R03", c, "disponibilidad", True,
                       f"El {fecha:%d/%m/%Y}, {inicio:%H:%M}–{fin:%H:%M} entra "
                       f"en la franja libre {desde:%H:%M}–{hasta:%H:%M}.")

    # La prioridad menor permite buscar primero todas las coincidencias de R03.
    @Rule(Solicitud(fecha=MATCH.fecha, hora_inicio=MATCH.inicio, hora_fin=MATCH.fin),
          Espacio(id_espacio=MATCH.c),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="disponibilidad")), salience=-10)
    def horario_no_confirmado(self, c, fecha, inicio, fin):
        self.comprobar("R04", c, "disponibilidad", False,
                       f"No hay una franja libre confirmada para el {fecha:%d/%m/%Y} "
                       f"de {inicio:%H:%M} a {fin:%H:%M}.")

    # R05-R06: todos los equipos obligatorios, sin inferirlos por modalidad. RF-03.
    @Rule(Solicitud(equipamiento_obligatorio=MATCH.req), AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, req: all(e[recurso] is True for recurso in req)),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="equipamiento")))
    def equipos_presentes(self, c, req):
        detalle = ", ".join(NOMBRES[r] for r in req) if req else "ninguno solicitado"
        self.comprobar("R05", c, "equipamiento", True,
                       "Cumple el equipamiento obligatorio: " + detalle + ".")

    @Rule(Solicitud(equipamiento_obligatorio=MATCH.req), AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, req: any(e[recurso] is not True for recurso in req)),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="equipamiento")))
    def equipos_faltantes(self, c, e, req):
        faltan = ", ".join(NOMBRES[r] for r in req if e[r] is not True)
        self.comprobar("R06", c, "equipamiento", False, "Falta equipamiento obligatorio: " + faltan + ".")

    # R07-R09: accesibilidad. Solo restringe si se pide; debe estar confirmada. RF-05.
    @Rule(Solicitud(requiere_accesibilidad=False), Espacio(id_espacio=MATCH.c),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad")))
    def acceso_no_requerido(self, c):
        self.comprobar("R07", c, "accesibilidad", True, "No se solicitó ruta accesible; no restringe.")

    @Rule(Solicitud(requiere_accesibilidad=True), Espacio(id_espacio=MATCH.c, ruta_accesible=True),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad")))
    def acceso_confirmado(self, c):
        self.comprobar("R08", c, "accesibilidad", True, "La ruta accesible solicitada está confirmada.")

    @Rule(Solicitud(requiere_accesibilidad=True), Espacio(id_espacio=MATCH.c, ruta_accesible=MATCH.ruta),
          TEST(lambda ruta: ruta is not True),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad")))
    def acceso_no_confirmado(self, c, ruta):
        detalle = "está pendiente de confirmar" if ruta is None else "no está disponible"
        self.comprobar("R09", c, "accesibilidad", False, "La ruta accesible requerida " + detalle + ".")

    # R10-R11: privacidad mínima. RF-03; se interpreta baja < media < alta.
    @Rule(Solicitud(privacidad_obligatoria=MATCH.req), Espacio(id_espacio=MATCH.c, privacidad=MATCH.nivel),
          TEST(lambda nivel, req: NIVELES[nivel] >= NIVELES[req]),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="privacidad")))
    def privacidad_suficiente(self, c, nivel, req):
        motivo = f"Privacidad {nivel}: alcanza el mínimo {req}." if req else "No se pidió privacidad mínima; no restringe."
        self.comprobar("R10", c, "privacidad", True, motivo)

    @Rule(Solicitud(privacidad_obligatoria=MATCH.req), Espacio(id_espacio=MATCH.c, privacidad=MATCH.nivel),
          TEST(lambda nivel, req: NIVELES[nivel] < NIVELES[req]),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="privacidad")))
    def privacidad_insuficiente(self, c, nivel, req):
        self.comprobar("R11", c, "privacidad", False, f"Privacidad {nivel}: no alcanza el mínimo {req}.")

    # R12-R13: nuevo criterio pedido por el usuario. No se infiere disposición ni preparación.
    @Rule(Solicitud(requiere_reconfiguracion=MATCH.req), Espacio(id_espacio=MATCH.c, reconfigurable=MATCH.permiso),
          TEST(lambda req, permiso: not req or permiso),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="reconfiguracion")))
    def reconfiguracion_compatible(self, c, req):
        motivo = "Se permite mover mesas y sillas." if req else "No se pidió mover mesas y sillas; no restringe."
        self.comprobar("R12", c, "reconfiguracion", True, motivo)

    @Rule(Solicitud(requiere_reconfiguracion=True), Espacio(id_espacio=MATCH.c, reconfigurable=False),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="reconfiguracion")))
    def reconfiguracion_incompatible(self, c):
        self.comprobar("R13", c, "reconfiguracion", False, "Se necesita mover mesas y sillas, pero el espacio no lo permite.")

    # R14-R15: nivel 2. Juntan los resultados de las reglas anteriores. RF-03/RF-04.
    @Rule(Comprobacion(id_espacio=MATCH.c, criterio="capacidad", cumple=True),
          Comprobacion(id_espacio=MATCH.c, criterio="disponibilidad", cumple=True),
          Comprobacion(id_espacio=MATCH.c, criterio="equipamiento", cumple=True),
          Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad", cumple=True),
          Comprobacion(id_espacio=MATCH.c, criterio="privacidad", cumple=True),
          Comprobacion(id_espacio=MATCH.c, criterio="reconfiguracion", cumple=True),
          NOT(Preseleccion(id_espacio=MATCH.c)))
    def cumple_obligatorio(self, c):
        self.declare(Preseleccion(id_espacio=c, cumple=True))
        self.registrar("R14", c, "Cumple las seis comprobaciones obligatorias.")

    @Rule(Comprobacion(id_espacio=MATCH.c, criterio="capacidad", cumple=MATCH.a),
          Comprobacion(id_espacio=MATCH.c, criterio="disponibilidad", cumple=MATCH.b),
          Comprobacion(id_espacio=MATCH.c, criterio="equipamiento", cumple=MATCH.d),
          Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad", cumple=MATCH.e),
          Comprobacion(id_espacio=MATCH.c, criterio="privacidad", cumple=MATCH.f),
          Comprobacion(id_espacio=MATCH.c, criterio="reconfiguracion", cumple=MATCH.g),
          TEST(lambda a, b, d, e, f, g: not all((a, b, d, e, f, g))),
          NOT(Preseleccion(id_espacio=MATCH.c)))
    def incumple_obligatorio(self, c):
        faltan = ", ".join(h["criterio"] for h in hechos(self, Comprobacion, c) if not h["cumple"])
        self.declare(Preseleccion(id_espacio=c, cumple=False))
        self.registrar("R15", c, "No cumple las condiciones de: " + faltan + ".")

    # R16-R18: exceso de capacidad. El brief usa MÁS del 50 %, sin descartar. RF-08.
    @Rule(Comprobacion(id_espacio=MATCH.c, criterio="capacidad", cumple=True),
          Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap), Solicitud(asistentes=MATCH.n),
          TEST(lambda cap, n: cap * 2 <= n * 3), NOT(AjusteCapacidad(id_espacio=MATCH.c)))
    def capacidad_ajustada(self, c, cap, n):
        self.declare(AjusteCapacidad(id_espacio=c, holgura=cap - n, exceso=False))
        self.registrar("R16", c, f"Sobran {cap - n} lugares; no supera el 50 % de exceso.")

    @Rule(Comprobacion(id_espacio=MATCH.c, criterio="capacidad", cumple=True),
          Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap), Solicitud(asistentes=MATCH.n),
          TEST(lambda cap, n: cap * 2 > n * 3), NOT(AjusteCapacidad(id_espacio=MATCH.c)))
    def capacidad_excesiva(self, c, cap, n):
        self.declare(AjusteCapacidad(id_espacio=c, holgura=cap - n, exceso=True))
        self.registrar("R17", c, f"Sobran {cap - n} lugares; supera el 50 % de exceso.")

    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), AjusteCapacidad(id_espacio=MATCH.c, exceso=True),
          NOT(Observacion(id_espacio=MATCH.c, criterio="exceso")))
    def avisar_exceso(self, c):
        motivo = "La capacidad supera en más del 50 % la cantidad de asistentes."
        self.declare(Observacion(id_espacio=c, criterio="exceso", motivo=motivo))
        self.registrar("R18", c, motivo)

    # R19-R21: preferencias explícitas; ninguna compensa un requisito obligatorio. RF-04/RF-07.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), Preferencia(criterio=MATCH.criterio, valor=MATCH.valor),
          AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, criterio, valor: cumple_preferencia(e, criterio, valor)),
          NOT(EvaluacionPreferencia(id_espacio=MATCH.c, criterio=MATCH.criterio)))
    def preferencia_presente(self, c, e, criterio, valor):
        self.declare(EvaluacionPreferencia(id_espacio=c, criterio=criterio, cumple=True))
        nombre = f"privacidad mínima {valor}" if criterio == "privacidad" else NOMBRES[criterio]
        self.registrar("R19", c, "Cumple la preferencia: " + nombre + ".")

    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), Preferencia(criterio=MATCH.criterio, valor=MATCH.valor),
          AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, criterio, valor: not cumple_preferencia(e, criterio, valor)),
          NOT(EvaluacionPreferencia(id_espacio=MATCH.c, criterio=MATCH.criterio)))
    def preferencia_ausente(self, c, e, criterio, valor):
        nombre = f"privacidad mínima {valor}" if criterio == "privacidad" else NOMBRES[criterio]
        motivo = "No cumple la preferencia: " + nombre + ". Sigue siendo una opción viable."
        self.declare(EvaluacionPreferencia(id_espacio=c, criterio=criterio, cumple=False))
        self.declare(Observacion(id_espacio=c, criterio="preferencia:" + criterio, motivo=motivo))
        self.registrar("R20", c, motivo)

    # La prioridad -20 deja terminar las evaluaciones antes de contarlas.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True),
          NOT(ResumenPreferencias(id_espacio=MATCH.c)), salience=-20)
    def contar_preferencias(self, c):
        evaluadas, total = hechos(self, EvaluacionPreferencia, c), len(hechos(self, Preferencia))
        if len(evaluadas) != total:
            raise RuntimeError("Faltan preferencias por evaluar.")
        cumplidas = sum(h["cumple"] for h in evaluadas)
        self.declare(ResumenPreferencias(id_espacio=c, cumplidas=cumplidas, total=total))
        self.registrar("R21", c, f"Cumple {cumplidas} de {total} preferencias.")

    # R22-R24: nivel 3, clasificación final a partir de hechos derivados. RF-04.
    # -30 asegura que se registraron los avisos y el resumen de preferencias.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=False),
          NOT(Clasificacion(id_espacio=MATCH.c)), salience=-30)
    def descartar(self, c):
        self.concluir("R22", c, "descartada", "No cumple todos los requisitos obligatorios.")

    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), AjusteCapacidad(id_espacio=MATCH.c),
          ResumenPreferencias(id_espacio=MATCH.c), Observacion(id_espacio=MATCH.c),
          NOT(Clasificacion(id_espacio=MATCH.c)), salience=-30)
    def compatible_con_avisos(self, c):
        self.concluir("R23", c, "compatible_con_observaciones", "Cumple lo obligatorio y tiene observaciones.")

    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), AjusteCapacidad(id_espacio=MATCH.c),
          ResumenPreferencias(id_espacio=MATCH.c), NOT(Observacion(id_espacio=MATCH.c)),
          NOT(Clasificacion(id_espacio=MATCH.c)), salience=-30)
    def recomendar(self, c):
        self.concluir("R24", c, "recomendada", "Cumple lo obligatorio y no tiene observaciones.")


def validar_solicitud(s):
    """RF-01: si falta un dato indispensable, no se inicia la inferencia."""
    if type(s.get("asistentes")) is not int or s["asistentes"] <= 0:
        raise ValueError("Completá la cantidad de asistentes con un entero mayor que cero.")
    if not isinstance(s.get("tipo_actividad"), str) or not s["tipo_actividad"].strip():
        raise ValueError("Completá el nombre de la actividad.")
    if s.get("modalidad") not in ("presencial", "hibrida"):
        raise ValueError("Elegí modalidad presencial o híbrida.")
    if type(s.get("fecha")) is not date:
        raise ValueError("Completá una fecha válida.")
    horas = (s.get("hora_inicio"), s.get("hora_fin"))
    if any(type(h) is not time or h.tzinfo is not None for h in horas):
        raise ValueError("Completá horas válidas, sin zona horaria.")
    if horas[0] >= horas[1]:
        raise ValueError("La actividad debe terminar después del inicio, dentro del mismo día.")
    for campo in ("requiere_accesibilidad", "requiere_reconfiguracion", "prefiere_reconfiguracion"):
        if type(s.get(campo, False)) is not bool:
            raise ValueError(f"{campo}: se espera True o False.")
    for campo in ("equipamiento_obligatorio", "equipamiento_deseable"):
        lista = s.get(campo, [])
        if not isinstance(lista, (list, tuple)) or any(r not in EQUIPAMIENTO for r in lista):
            raise ValueError(f"{campo}: usá una lista de pantalla, camara o amplificacion_voz.")
    if set(s.get("equipamiento_obligatorio", [])) & set(s.get("equipamiento_deseable", [])):
        raise ValueError("Un equipo debe ser obligatorio o preferido; no ambas cosas.")
    if s.get("requiere_reconfiguracion") and s.get("prefiere_reconfiguracion"):
        raise ValueError("Mover mesas y sillas debe ser obligatorio o preferido; no ambas cosas.")
    for campo in ("privacidad_obligatoria", "privacidad_deseable"):
        if s.get(campo) is not None and (not isinstance(s[campo], str) or s[campo] not in NIVELES):
            raise ValueError(f"{campo}: elegí baja, media, alta o sin requisito.")


def evaluar(espacios, solicitud, horarios):
    """Consulta nueva: los CSV y las consultas anteriores no se modifican."""
    validar_solicitud(solicitud)
    if not espacios:
        raise ValueError("No hay espacios para evaluar.")
    s = dict(solicitud)
    for campo in ("equipamiento_obligatorio", "equipamiento_deseable"):
        s[campo] = tuple(dict.fromkeys(s.get(campo, [])))
    for campo in ("requiere_accesibilidad", "requiere_reconfiguracion", "prefiere_reconfiguracion"):
        s.setdefault(campo, False)
    for campo in ("privacidad_obligatoria", "privacidad_deseable"):
        s.setdefault(campo, None)
    motor = MotorAulas()
    motor.reset()
    motor.declare(Solicitud(**s))
    preferencias = [(r, True) for r in s["equipamiento_deseable"]]
    if s["prefiere_reconfiguracion"]:
        preferencias.append(("reconfigurable", True))
    if s["privacidad_deseable"]:
        preferencias.append(("privacidad", s["privacidad_deseable"]))
    for criterio, valor in preferencias:
        motor.declare(Preferencia(criterio=criterio, valor=valor))
    for espacio in espacios:
        motor.declare(Espacio(**espacio))
    for horario in unir_franjas(horarios):
        motor.declare(Horario(**horario))
    motor.run()
    return motor


def recomendaciones(motor):
    """Más preferencias, menos lugares sobrantes. El código resuelve empates."""
    opciones = []
    for conclusion in hechos(motor, Clasificacion):
        if conclusion["estado"] != "descartada":
            c = conclusion["id_espacio"]
            ajuste, resumen = hechos(motor, AjusteCapacidad, c)[0], hechos(motor, ResumenPreferencias, c)[0]
            opciones.append({"id_espacio": c, "estado": conclusion["estado"], "holgura": ajuste["holgura"],
                             "preferencias_cumplidas": resumen["cumplidas"], "preferencias_totales": resumen["total"]})
    return sorted(opciones, key=lambda h: (-h["preferencias_cumplidas"], h["holgura"], h["id_espacio"]))


def explicar(motor, codigo):
    return [f"{paso['regla']}: {paso['motivo']}" for paso in motor.traza if paso["id_espacio"] == codigo]


CANTIDAD_REGLAS = sum(isinstance(valor, Rule) for valor in MotorAulas.__dict__.values())

if __name__ == "__main__":
    print(f"Motor con {CANTIDAD_REGLAS} reglas. Para ver ejemplos: python demostracion.py")
