# El motor parte de los hechos de la consulta y aplica reglas que declaran
# nuevos hechos. Esos resultados pueden activar otras reglas. Así funciona
# el encadenamiento hacia adelante.

import collections
import collections.abc
from datetime import date, time

# Este alias permite importar Experta en Python 3.11.
collections.Mapping = collections.abc.Mapping

from experta import AS, MATCH, NOT, TEST, Fact, KnowledgeEngine, Rule
from cargar_datos import EQUIPAMIENTO, se_superponen

# Los números permiten comparar la privacidad del aula con el mínimo pedido.
NIVELES = {None: 0, "baja": 1, "media": 2, "alta": 3}
NOMBRES = {"pantalla": "TV/pantalla", "camara": "cámara",
           "amplificacion_voz": "amplificación de voz",
           "reconfigurable": "permiso para mover mesas y sillas"}
CRITERIOS = ("capacidad", "disponibilidad", "equipamiento", "accesibilidad",
             "privacidad", "reconfiguracion")


# Cada clase Fact identifica un tipo de hecho y sus campos se cargan como
# datos con nombre. evaluar() carga Solicitud, Espacio, Reserva y Preferencia.
# Los demás tipos de hechos se declaran al ejecutar las reglas.
class Solicitud(Fact):
    """Datos de una única consulta."""


class Espacio(Fact):
    """Características declaradas de un espacio."""


class Reserva(Fact):
    """Reserva ya registrada que ocupa un espacio en una fecha y un intervalo."""


class Comprobacion(Fact):
    """Resultado de revisar una condición obligatoria."""


class Preseleccion(Fact):
    """Resultado conjunto de las seis comprobaciones."""


class AjusteCapacidad(Fact):
    """Lugares sobrantes e indicador de ocupación inferior al 50 %."""


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
    # Recupera los hechos de un tipo. Si recibe un código, filtra por aula.
    return [h for h in motor.facts.values() if isinstance(h, clase)
            and (codigo is None or h.get("id_espacio") == codigo)]


def cumple_preferencia(espacio, criterio, valor):
    # La privacidad se compara con un mínimo. Los demás criterios piden True.
    if criterio == "privacidad":
        return NIVELES[espacio["privacidad"]] >= NIVELES[valor]
    return espacio[criterio] is True


# KnowledgeEngine administra los hechos y las reglas que pueden ejecutarse.
class MotorAulas(KnowledgeEngine):
    def __init__(self):
        self.traza = []
        super().__init__()

    def reset(self, **datos):
        # Cada consulta empieza con la memoria del motor reiniciada y la traza vacía.
        self.traza.clear()
        super().reset(**datos)

    def registrar(self, regla, codigo, motivo):
        # Guarda el número de la regla y su motivo para poder explicar el resultado.
        paso = {"regla": regla, "id_espacio": codigo, "motivo": motivo}
        self.declare(Justificacion(**paso))
        self.traza.append(paso)

    def comprobar(self, regla, codigo, criterio, cumple, motivo):
        # Declara una Comprobacion que luego pueden leer R14 y R15.
        self.declare(Comprobacion(id_espacio=codigo, criterio=criterio,
                                 cumple=cumple, motivo=motivo))
        self.registrar(regla, codigo, motivo)

    def concluir(self, regla, codigo, estado, motivo):
        # Guarda la clasificación final que deciden R22, R23 o R24.
        self.declare(Clasificacion(id_espacio=codigo, estado=estado, motivo=motivo))
        self.registrar(regla, codigo, motivo)

    # Cómo leer una regla de Experta
    #
    # @Rule reúne las condiciones. Cuando se cumplen todas, la regla queda lista.
    # Al ejecutarla, Experta llama al método que está debajo del decorador.
    # MATCH guarda el valor de un campo. Repetir MATCH.c exige que coincida
    # el código del aula en los hechos que lo usan.
    # AS.e << Espacio(...) guarda todo el hecho Espacio en e.
    # TEST evalúa una condición de Python usando los valores capturados.
    # NOT exige que todavía no exista un hecho que coincida con ese patrón.
    # salience ordena las reglas que están listas. El valor por defecto es 0
    # y los valores más altos tienen prioridad. R01 a R24 identifican las reglas.
    # self.declare agrega un hecho que otras reglas pueden usar.

    # Comprobaciones obligatorias (R01 a R13)
    # NOT(Comprobacion(...)) evita repetir el resultado del mismo criterio y aula.

    # R01. Confirma que el aula tiene lugar para todos los asistentes.
    # MATCH.n toma la cantidad de asistentes y MATCH.cap la capacidad del aula.
    # Si hay 25 asistentes y 30 lugares, cap >= n y se registra cumple=True.
    @Rule(Solicitud(asistentes=MATCH.n), Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap),
          TEST(lambda cap, n: cap >= n),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="capacidad")))
    def capacidad_suficiente(self, c, cap, n):
        self.comprobar("R01", c, "capacidad", True,
                       f"Alcanzan los lugares: capacidad {cap}, asistentes {n}.")

    # R02. Detecta que al aula le faltan lugares para el grupo.
    # Si cap < n, registra cumple=False. La diferencia n - cap indica cuántos faltan.
    @Rule(Solicitud(asistentes=MATCH.n), Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap),
          TEST(lambda cap, n: cap < n),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="capacidad")))
    def capacidad_insuficiente(self, c, cap, n):
        self.comprobar("R02", c, "capacidad", False,
                       f"Faltan {n - cap} lugares: capacidad {cap}, asistentes {n}.")

    # R03. Marca el aula como disponible para el horario pedido.
    # Con prioridad -10, queda detrás de R04 cuando ambas están listas.
    # Si sigue sin una Comprobacion de disponibilidad, registra cumple=True.
    @Rule(Solicitud(fecha=MATCH.fecha, hora_inicio=MATCH.inicio, hora_fin=MATCH.fin),
          Espacio(id_espacio=MATCH.c),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="disponibilidad")), salience=-10)
    def disponible_sin_superposicion(self, c, fecha, inicio, fin):
        self.comprobar("R03", c, "disponibilidad", True,
                       f"No hay reservas registradas que se superpongan el {fecha:%d/%m/%Y} "
                       f"de {inicio:%H:%M} a {fin:%H:%M}.")

    # R04. Marca el aula como ocupada por una reserva que se cruza con el turno.
    # Busca una reserva del mismo espacio y fecha. TEST verifica si los horarios
    # se superponen. Su prioridad 10 le permite registrar cumple=False antes
    # de R03. Ese hecho hace que el NOT de R03 deje de cumplirse.
    # Si una reserva termina justo al inicio de la actividad, ambos intervalos
    # son compatibles.
    @Rule(Solicitud(fecha=MATCH.fecha, hora_inicio=MATCH.inicio, hora_fin=MATCH.fin),
          Espacio(id_espacio=MATCH.c),
          Reserva(id_espacio=MATCH.c, fecha=MATCH.fecha,
                  hora_inicio=MATCH.desde, hora_fin=MATCH.hasta),
          TEST(lambda desde, hasta, inicio, fin: se_superponen(inicio, fin, desde, hasta)),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="disponibilidad")), salience=10)
    def ocupada_por_reserva(self, c, fecha, inicio, fin, desde, hasta):
        self.comprobar("R04", c, "disponibilidad", False,
                       f"La actividad del {fecha:%d/%m/%Y}, {inicio:%H:%M}–{fin:%H:%M}, "
                       f"se superpone con una reserva registrada de {desde:%H:%M} a {hasta:%H:%M}.")

    # R05. Confirma que el aula tiene todo el equipamiento obligatorio.
    # all() comprueba que cada equipo de req figure como True en el aula.
    # Con una lista vacía, la comprobación también se cumple.
    @Rule(Solicitud(equipamiento_obligatorio=MATCH.req), AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, req: all(e[recurso] is True for recurso in req)),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="equipamiento")))
    def equipos_presentes(self, c, req):
        detalle = ", ".join(NOMBRES[r] for r in req) if req else "ninguno solicitado"
        self.comprobar("R05", c, "equipamiento", True,
                       "Cumple el equipamiento obligatorio: " + detalle + ".")

    # R06. Detecta que al aula le falta equipamiento obligatorio.
    # any() da True si al menos un equipo de req tiene un valor distinto de True.
    # Registra cumple=False y enumera todos los equipos que faltan.
    @Rule(Solicitud(equipamiento_obligatorio=MATCH.req), AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, req: any(e[recurso] is not True for recurso in req)),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="equipamiento")))
    def equipos_faltantes(self, c, e, req):
        faltan = ", ".join(NOMBRES[r] for r in req if e[r] is not True)
        self.comprobar("R06", c, "equipamiento", False, "Falta equipamiento obligatorio: " + faltan + ".")

    # R07. Da por cumplido el criterio si el usuario deja la accesibilidad sin marcar.
    # Se activa con requiere_accesibilidad=False y registra cumple=True.
    @Rule(Solicitud(requiere_accesibilidad=False), Espacio(id_espacio=MATCH.c),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad")))
    def acceso_no_requerido(self, c):
        self.comprobar("R07", c, "accesibilidad", True, "No se solicitó ruta accesible; no restringe.")

    # R08. Confirma que el aula tiene la ruta accesible que se pidió.
    # Coinciden requiere_accesibilidad=True en la solicitud y ruta_accesible=True
    # en el aula. Registra cumple=True.
    @Rule(Solicitud(requiere_accesibilidad=True), Espacio(id_espacio=MATCH.c, ruta_accesible=True),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad")))
    def acceso_confirmado(self, c):
        self.comprobar("R08", c, "accesibilidad", True, "La ruta accesible solicitada está confirmada.")

    # R09. Marca que el aula incumple el requisito de accesibilidad.
    # Si se pidió una ruta y ruta_accesible difiere de True, registra cumple=False.
    # False indica que está indisponible y None que queda por confirmar.
    @Rule(Solicitud(requiere_accesibilidad=True), Espacio(id_espacio=MATCH.c, ruta_accesible=MATCH.ruta),
          TEST(lambda ruta: ruta is not True),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="accesibilidad")))
    def acceso_no_confirmado(self, c, ruta):
        detalle = "está pendiente de confirmar" if ruta is None else "no está disponible"
        self.comprobar("R09", c, "accesibilidad", False, "La ruta accesible requerida " + detalle + ".")

    # R10. Confirma que el aula alcanza la privacidad mínima solicitada.
    # NIVELES[nivel] >= NIVELES[req] compara los valores numéricos.
    # Si el usuario deja el mínimo sin elegir, req=None equivale a 0.
    @Rule(Solicitud(privacidad_obligatoria=MATCH.req), Espacio(id_espacio=MATCH.c, privacidad=MATCH.nivel),
          TEST(lambda nivel, req: NIVELES[nivel] >= NIVELES[req]),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="privacidad")))
    def privacidad_suficiente(self, c, nivel, req):
        motivo = f"Privacidad {nivel}: alcanza el mínimo {req}." if req else "No se pidió privacidad mínima; no restringe."
        self.comprobar("R10", c, "privacidad", True, motivo)

    # R11. Marca que la privacidad del aula es insuficiente.
    # Si NIVELES[nivel] < NIVELES[req], registra cumple=False.
    @Rule(Solicitud(privacidad_obligatoria=MATCH.req), Espacio(id_espacio=MATCH.c, privacidad=MATCH.nivel),
          TEST(lambda nivel, req: NIVELES[nivel] < NIVELES[req]),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="privacidad")))
    def privacidad_insuficiente(self, c, nivel, req):
        self.comprobar("R11", c, "privacidad", False, f"Privacidad {nivel}: no alcanza el mínimo {req}.")

    # R12. Da por cumplida la comprobación sobre mover mesas y sillas.
    # TEST da True si la consulta deja el requisito sin marcar o si el aula
    # permite moverlas. En cualquiera de esos casos registra cumple=True.
    @Rule(Solicitud(requiere_reconfiguracion=MATCH.req), Espacio(id_espacio=MATCH.c, reconfigurable=MATCH.permiso),
          TEST(lambda req, permiso: not req or permiso),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="reconfiguracion")))
    def reconfiguracion_compatible(self, c, req):
        motivo = "Se permite mover mesas y sillas." if req else "No se pidió mover mesas y sillas; no restringe."
        self.comprobar("R12", c, "reconfiguracion", True, motivo)

    # R13. Detecta que falta el permiso obligatorio para mover mesas y sillas.
    # Con requiere_reconfiguracion=True y reconfigurable=False, registra cumple=False.
    @Rule(Solicitud(requiere_reconfiguracion=True), Espacio(id_espacio=MATCH.c, reconfigurable=False),
          NOT(Comprobacion(id_espacio=MATCH.c, criterio="reconfiguracion")))
    def reconfiguracion_incompatible(self, c):
        self.comprobar("R13", c, "reconfiguracion", False, "Se necesita mover mesas y sillas, pero el espacio no lo permite.")

    # Preselección (R14 y R15)
    # Ambas reglas esperan seis hechos Comprobacion para la misma aula.

    # R14. Marca el aula como viable.
    # Con las seis comprobaciones en True, declara Preseleccion(cumple=True).
    # Ese hecho habilita las reglas de preferencias.
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

    # R15. Marca el aula como inviable si falla algún requisito obligatorio.
    # Con las seis comprobaciones cargadas, not all(...) da True si alguna falló.
    # Declara Preseleccion(cumple=False), que R22 usa para descartar el aula.
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

    # Ajuste de capacidad (R16 a R18)
    # R16 y R17 pueden ejecutarse apenas R01 confirma que alcanzan los lugares.

    # R16. Identifica aulas que se ocuparán al 50 % o más.
    # n * 2 >= cap equivale a n / cap >= 0,5 y evita redondear el porcentaje.
    # Guarda holgura=cap - n y baja_ocupacion=False.
    @Rule(Comprobacion(id_espacio=MATCH.c, criterio="capacidad", cumple=True),
          Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap), Solicitud(asistentes=MATCH.n),
          TEST(lambda cap, n: n * 2 >= cap), NOT(AjusteCapacidad(id_espacio=MATCH.c)))
    def capacidad_ajustada(self, c, cap, n):
        self.declare(AjusteCapacidad(id_espacio=c, holgura=cap - n, baja_ocupacion=False))
        self.registrar("R16", c, f"Se ocuparán {n} de {cap} lugares, el 50 % o más de la capacidad del aula.")

    # R17. Detecta aulas con una ocupación inferior al 50 %.
    # Si n * 2 < cap, los asistentes ocupan menos de la mitad de los lugares.
    # Guarda holgura=cap - n y baja_ocupacion=True.
    # Con 20 asistentes, un aula de 40 lugares activa R16 y una de 41 activa R17.
    @Rule(Comprobacion(id_espacio=MATCH.c, criterio="capacidad", cumple=True),
          Espacio(id_espacio=MATCH.c, capacidad=MATCH.cap), Solicitud(asistentes=MATCH.n),
          TEST(lambda cap, n: n * 2 < cap), NOT(AjusteCapacidad(id_espacio=MATCH.c)))
    def capacidad_con_baja_ocupacion(self, c, cap, n):
        self.declare(AjusteCapacidad(id_espacio=c, holgura=cap - n, baja_ocupacion=True))
        self.registrar("R17", c, f"Se ocuparán {n} de {cap} lugares, menos del 50 % de la capacidad del aula.")

    # R18. Agrega un aviso de baja ocupación para un aula viable.
    # Combina Preseleccion(cumple=True) con AjusteCapacidad(baja_ocupacion=True)
    # y declara una Observacion con criterio="baja_ocupacion".
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), AjusteCapacidad(id_espacio=MATCH.c, baja_ocupacion=True),
          NOT(Observacion(id_espacio=MATCH.c, criterio="baja_ocupacion")))
    def avisar_baja_ocupacion(self, c):
        motivo = "Baja ocupación prevista. Se utilizará menos del 50 % de la capacidad del aula."
        self.declare(Observacion(id_espacio=c, criterio="baja_ocupacion", motivo=motivo))
        self.registrar("R18", c, motivo)

    # Preferencias (R19 a R21)
    # Se evalúan para aulas viables y una vez por cada criterio solicitado.

    # R19. Registra que el aula cumple una preferencia del usuario.
    # Si el aula es viable y cumple_preferencia(...) da True, declara
    # EvaluacionPreferencia con cumple=True para ese criterio.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), Preferencia(criterio=MATCH.criterio, valor=MATCH.valor),
          AS.e << Espacio(id_espacio=MATCH.c),
          TEST(lambda e, criterio, valor: cumple_preferencia(e, criterio, valor)),
          NOT(EvaluacionPreferencia(id_espacio=MATCH.c, criterio=MATCH.criterio)))
    def preferencia_presente(self, c, e, criterio, valor):
        self.declare(EvaluacionPreferencia(id_espacio=c, criterio=criterio, cumple=True))
        nombre = f"privacidad mínima {valor}" if criterio == "privacidad" else NOMBRES[criterio]
        self.registrar("R19", c, "Cumple la preferencia: " + nombre + ".")

    # R20. Registra una observación cuando el aula incumple una preferencia.
    # Si cumple_preferencia(...) da False para un aula viable, declara
    # EvaluacionPreferencia con cumple=False y una Observacion para ese criterio.
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

    # R21. Cuenta cuántas preferencias del usuario cumple el aula.
    # La prioridad -20 deja que R19 y R20 terminen antes de contar.
    # Declara ResumenPreferencias con el total y las cumplidas, incluso si son 0 de 0.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True),
          NOT(ResumenPreferencias(id_espacio=MATCH.c)), salience=-20)
    def contar_preferencias(self, c):
        evaluadas, total = hechos(self, EvaluacionPreferencia, c), len(hechos(self, Preferencia))
        if len(evaluadas) != total:
            raise RuntimeError("Faltan preferencias por evaluar.")
        cumplidas = sum(h["cumple"] for h in evaluadas)
        self.declare(ResumenPreferencias(id_espacio=c, cumplidas=cumplidas, total=total))
        self.registrar("R21", c, f"Cumple {cumplidas} de {total} preferencias.")

    # Clasificación final (R22 a R24)
    # La prioridad -30 deja que se registren el resumen y las observaciones
    # de las aulas viables antes de decidir el estado final.

    # R22. Clasifica el aula como descartada.
    # Lee Preseleccion(cumple=False) de R15. concluir() guarda el estado final.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=False),
          NOT(Clasificacion(id_espacio=MATCH.c)), salience=-30)
    def descartar(self, c):
        self.concluir("R22", c, "descartada", "No cumple todos los requisitos obligatorios.")

    # R23. Clasifica el aula como compatible con observaciones.
    # Pide que el aula sea viable, tenga el ajuste y el resumen calculados
    # y exista al menos una Observacion. El aviso puede venir de R18 o R20.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), AjusteCapacidad(id_espacio=MATCH.c),
          ResumenPreferencias(id_espacio=MATCH.c), Observacion(id_espacio=MATCH.c),
          NOT(Clasificacion(id_espacio=MATCH.c)), salience=-30)
    def compatible_con_avisos(self, c):
        self.concluir("R23", c, "compatible_con_observaciones", "Cumple lo obligatorio y tiene observaciones.")

    # R24. Clasifica el aula como recomendada.
    # Pide que el aula sea viable y tenga el ajuste y el resumen calculados.
    # NOT(Observacion(...)) verifica que tenga cero avisos.
    @Rule(Preseleccion(id_espacio=MATCH.c, cumple=True), AjusteCapacidad(id_espacio=MATCH.c),
          ResumenPreferencias(id_espacio=MATCH.c), NOT(Observacion(id_espacio=MATCH.c)),
          NOT(Clasificacion(id_espacio=MATCH.c)), salience=-30)
    def recomendar(self, c):
        self.concluir("R24", c, "recomendada", "Cumple lo obligatorio y no tiene observaciones.")


def validar_solicitud(s):
    """Verifica los datos de la consulta antes de cargar los hechos."""
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


def evaluar(espacios, solicitud, reservas):
    """Evalúa requisitos y reservas existentes sin modificar los datos ni reservar."""
    validar_solicitud(solicitud)
    if not espacios:
        raise ValueError("No hay espacios para evaluar.")
    # Prepara los campos que las reglas esperan leer en la solicitud.
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
    # Convierte cada preferencia elegida en un hecho Preferencia separado.
    preferencias = [(r, True) for r in s["equipamiento_deseable"]]
    if s["prefiere_reconfiguracion"]:
        preferencias.append(("reconfigurable", True))
    if s["privacidad_deseable"]:
        preferencias.append(("privacidad", s["privacidad_deseable"]))
    for criterio, valor in preferencias:
        motor.declare(Preferencia(criterio=criterio, valor=valor))
    # Carga los datos del catálogo y las reservas como hechos del motor.
    for espacio in espacios:
        motor.declare(Espacio(**espacio))
    for reserva in reservas:
        motor.declare(Reserva(**reserva))
    # Ejecuta las reglas y sigue usando los hechos nuevos hasta agotar las activaciones.
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
    # Python ordena las opciones ya clasificadas. Prioriza más preferencias
    # cumplidas y, en empate, menos lugares sobrantes. El código de aula desempata al final.
    return sorted(opciones, key=lambda h: (-h["preferencias_cumplidas"], h["holgura"], h["id_espacio"]))


def explicar(motor, codigo):
    # Devuelve las reglas que se activaron para un aula con el motivo de cada paso.
    return [f"{paso['regla']}: {paso['motivo']}" for paso in motor.traza if paso["id_espacio"] == codigo]


# Cuenta los métodos de MotorAulas que fueron decorados con @Rule.
CANTIDAD_REGLAS = sum(isinstance(valor, Rule) for valor in MotorAulas.__dict__.values())

if __name__ == "__main__":
    print(f"Motor con {CANTIDAD_REGLAS} reglas. Abrí la interfaz con: python -m streamlit run interfaz.py")
