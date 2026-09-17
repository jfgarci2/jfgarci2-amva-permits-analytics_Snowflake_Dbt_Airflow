"""SGC_Modificado v0–v7 (DAX Power BI) → grupo de trabajo.

Cadena oficial AMVA. No persiste PII: FUNCIONARIO solo se usa en memoria
para las listas de Firmas de v7.

v0  LOOKUPVALUE(LIMITE_TAREAS) no está en el extracto; se usa ESTADOSGC
    de DECIDE como el SGC nativo de la tarea (mismo rol).
v1  ID_DEPENDENCIA (FUNCIONARIO_DEPENDENCIA) no está en el extracto.
    Las Firmas las cubre v7 por nombre de funcionario.
v2  Tarea + Dependencia_Nombre: sin tabla de dependencia, se omite.
v3–v5  mapeo por TAREA si el valor anterior viene vacío + normalización.
v6  Archivo Envía / Finalizar+proceso. Sin Dominio_Nuevos_EstadoSGC.
v7  prioridad: Firmas por funcionario, tareas pedidas, luego v6.

Nombres canónicos (v4 + v5 hyphen):
  Atención al ciudadano
  Atención al usuario
  Gestión Jurídica - Ambiental
  Gestión Control - Ambiental
  Gestión documental
  Usuario
"""
from __future__ import annotations

import re
import unicodedata

EN_DASH = "\u2013"

G_ATENCION = "Atención al ciudadano"
G_USUARIO_AT = "Atención al usuario"
G_JURIDICA = "Gestión Jurídica - Ambiental"
G_CONTROL = "Gestión Control - Ambiental"
G_DOC = "Gestión documental"
G_USUARIO = "Usuario"

_FIRMAS_JURIDICA = {
    "ALEJANDRO VASQUEZ CAMPUZANO",
    "ANA MARGARITA GIRALDO POSADA",
    "ANA MARIA ROLDAN ORTIZ",
    "ANDRES ARBELAEZ MARTINEZ",
    "DAVID SOTO GONZALEZ",
    "DIANA MARCELA URIBE QUINTERO",
    "DIANA MARIA MONTOYA VELILLA",
    "GERMAN GUSTAVO LONDONO GAVIRIA",
    "JULIAN ANDRES RESTREPO MUNOZ",
    "LICETH MARIANA RAMIREZ CALVO",
    "LUISA FERNANDA MARTINEZ VALDERRAMA",
    "MATEO MOLINA RODRIGUEZ",
    "SANDRA MARCELA GARCIA VALLEJO",
    "YANELLY GARCIA GIRALDO",
}
_FIRMAS_CONTROL = {
    "CATALINA CASTANO CASTRILLON",
    "DIEGO ALONSO BETANCUR ESTRADA",
    "HECTOR JAIRO VELEZ JIMENEZ",
    "JAIME NICOLAS ZEA MUNOZ",
    "JUAN DAVID GUZMAN BRAVO",
    "MARIA EDILIA ARBOLEDA GOMEZ",
    "MARIANA RODRIGUEZ ORTEGA",
    "OBED JULIAN ARANGO LOZANO",
    "SALOMON LONDONO LOPEZ",
    "SARA BERNAL ARANGO",
    "SEBASTIAN PENA ALZATE",
}
_FIRMAS_ATENCION = {
    "EVELYN TATIANA RODRIGUEZ CASTILLO",
    "SEBASTIAN MEDINA DURANGO",
}
_FIRMAS_USUARIO_AT = {"JORGE ENRIQUE ESTRADA CORREA"}

_V6_FINALIZAR_PROC = {
    "GESTION DE AUTORIDAD - EVALUACION",
    "DERECHOS DE PETICION GENERAL",
    "OFICIOS RECIBIDOS AMBIENTALES GENERAL",
    "ATENCION QUEJAS GENERAL",
    "SANCIONATORIOS",
}

# v3: TAREA exacta (tras trim). DAX es case-insensitive.
_V3 = {
    "archivo digitaliza": G_DOC,
    "archivo inicial": G_DOC,
    "atu revisa documentos e inicia tramite": G_DOC,
    "digitalizar documentos": G_DOC,
    "elaborar auto de inicio": G_DOC,
    "elaborar documento": G_CONTROL,
    "enviar documento al usuario y esperar respuesta": G_USUARIO,
    "enviar informe al usuario y esperar respuesta": G_USUARIO,
    "esperar requerimientos": G_USUARIO,
    "esperar respuesta del usuario": G_USUARIO,
    "evaluacion de la pqrsd": G_DOC,
    "fin": G_DOC,
    "finaliza tramite": G_DOC,
    "finalizar": G_DOC,
    "finalizar el tramite": G_JURIDICA,
    "finalizar tramite (control y vigilancia)": G_DOC,
    "firma subdirector ambiental": G_JURIDICA,
    "generar valor del tramite": G_DOC,
    "imprimir documento": G_JURIDICA,
    "incio recepcion pqrsd": G_DOC,
    "notificacion auto de requerimiento o resolucion": G_ATENCION,
    "personal tecnico atencion ciudadana (flora, salvoconductos, industrias forestales, decomisos)": G_CONTROL,
    "personal tecnico comercio y servicios": G_CONTROL,
    "personal tecnico de industria, comercio y servicios": G_CONTROL,
    "personal tecnico fuentes moviles": G_CONTROL,
    "personal tecnico industria": G_CONTROL,
    "personal tecnico infraestructura": G_CONTROL,
    "personal tecnico quejas": G_CONTROL,
    "personal tecnico quejas fauna": G_CONTROL,
    "profesional de enlace industria": G_CONTROL,
    "profesional de enlace quejas": G_CONTROL,
    "profesional enlace atencion ciudadana (flora, salvoconductos, industrias forestales, decomisos)": G_CONTROL,
    "profesional enlace fauna": G_CONTROL,
    "profesional enlace fuentes moviles": G_CONTROL,
    "profesional enlace gestion biodiversidad": G_CONTROL,
    "profesional enlace gestion de riesgos": G_CONTROL,
    "profesional enlace gestion recurso hidrico": G_CONTROL,
    "profesional enlace industria": G_CONTROL,
    "profesional enlace industria, comercio y servicios": G_CONTROL,
    "profesional enlace infraestructura": G_CONTROL,
    "profesional enlace quejas": G_CONTROL,
    "radicar informe": G_CONTROL,
    "radicar y digitalizar": G_DOC,
    "radicar y digitalizar el documento": G_DOC,
    "realizar informe": G_CONTROL,
    "realizar visita": G_CONTROL,
    "recibe auxiliares administrativas": G_ATENCION,
    "recibe jefes, lideres o directores": G_JURIDICA,
    "recibe profesionales, tecnicos o contratistas": G_CONTROL,
    "reparto sancionatorios": G_JURIDICA,
    "reparto tecnico o juridico": G_JURIDICA,
    "revisar el documento": G_JURIDICA,
    "revisar informe": G_CONTROL,
    "revision documento": G_ATENCION,
    "seleccionar plantilla y elaborar documento": G_JURIDICA,
    "solicitar informacion adicional": G_DOC,
    "verificar informacion suministrada": G_JURIDICA,
    "espera actuacion tecnica": G_CONTROL,
}

_V5_EXTRA = {
    "finalizar el tramite": G_JURIDICA,
    "profesional enlace atencion ciudadana (flora, salvoconductos, industrias forestales, decomisos)": G_JURIDICA,
}

_V7_TAREA = {
    "enviar oficio de requerimiento": G_USUARIO,
    "enviar respuesta al usuario": G_USUARIO,
    "fijar aviso concesion de aguas": G_CONTROL,
    "aprobar e imprimir solicitud de requerimiento vital": G_ATENCION,
    "preparar solicitud de requerimientos vital": G_ATENCION,
    "archivo envia (correo electronico o correo certificado)": G_DOC,
    "recepcion solicitud": G_ATENCION,
    "notificar acto administrativo": G_ATENCION,
    "solicitar informacion adicional": G_ATENCION,
    "reliquidar valor del tramite": G_ATENCION,
    "evaluacion de la pqrsd": G_ATENCION,
    "en espera de visita": G_USUARIO,
}


def _txt(value) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # NaN
            return ""
    except Exception:
        pass
    s = str(value).replace("\u00a0", " ").strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return ""
    return s


def _fold(value) -> str:
    s = _txt(value)
    s = s.replace(EN_DASH, "-")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def norm_tarea(value) -> str:
    return _fold(value)


def _fold_name(value) -> str:
    return _fold(value).upper()


def _canon_key(value) -> str:
    s = _fold(value)
    s = s.replace("–", "-").replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalizar_grupo(value) -> str | None:
    """v4 unificación + v5 hyphen + alias v1."""
    s = _txt(value).replace(EN_DASH, "-")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    key = _canon_key(s)
    if "gestion control" in key and "ambiental" in key:
        return G_CONTROL
    if "gestion juridica" in key and "ambiental" in key:
        return G_JURIDICA
    aliases = {
        "atencion al ciudadano": G_ATENCION,
        "gestion atencion al ciudadano": G_ATENCION,
        "atencion al usuario": G_USUARIO_AT,
        "gestion documental": G_DOC,
        "usuario": G_USUARIO,
        "gestion usuario": G_USUARIO,
        "gestion control ambiental": G_CONTROL,
        "gestion juridica ambiental": G_JURIDICA,
    }
    return aliases.get(key, s)


def _v0(estado_sgc) -> str | None:
    return normalizar_grupo(estado_sgc)


def _v3(tarea, valor_anterior) -> str | None:
    if _txt(valor_anterior):
        return normalizar_grupo(valor_anterior)
    return _V3.get(_fold(tarea))


def _v5(tarea, valor_v3) -> str | None:
    va = normalizar_grupo(valor_v3)
    extra = _V5_EXTRA.get(_fold(tarea))
    primer = va or extra
    if not primer and _fold(tarea) == "finalizar el tramite":
        primer = G_JURIDICA
    return normalizar_grupo(primer) if primer else None


def _v6(tarea, proceso, valor_v5) -> str | None:
    orig = normalizar_grupo(valor_v5)
    if orig:
        return orig
    if "archivo envia" in _fold(tarea):
        return G_ATENCION
    if _fold(tarea) == "finalizar el tramite" and _canon_key(proceso) in {
        _canon_key(x) for x in _V6_FINALIZAR_PROC
    }:
        return G_JURIDICA
    return orig


def _v7_prioridad(tarea, funcionario) -> str | None:
    t = _fold(tarea)
    hit = _V7_TAREA.get(t)
    if hit:
        return hit
    if t != "firmas":
        return None
    f = _fold_name(funcionario)
    if not f:
        return None
    if f in _FIRMAS_JURIDICA:
        return G_JURIDICA
    if f in _FIRMAS_CONTROL:
        return G_CONTROL
    if f in _FIRMAS_ATENCION:
        return G_ATENCION
    if f in _FIRMAS_USUARIO_AT:
        return G_USUARIO_AT
    return None


def grupo_trabajo_v7(tarea, proceso=None, funcionario=None, estado_sgc=None) -> str:
    """Grupo de trabajo SGC_Modificado_v7. Vacío → 'Sin grupo'."""
    pri = _v7_prioridad(tarea, funcionario)
    if pri:
        return normalizar_grupo(pri) or "Sin grupo"
    v0 = _v0(estado_sgc)
    v3 = _v3(tarea, v0)
    v5 = _v5(tarea, v3)
    v6 = _v6(tarea, proceso, v5)
    return v6 or "Sin grupo"
