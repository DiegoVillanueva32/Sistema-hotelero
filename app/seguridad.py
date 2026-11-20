"""Autenticación, roles y protección CSRF.

Las contraseñas nunca se guardan en texto plano: en el código solo existen
hashes generados con werkzeug (scrypt). Se pueden reemplazar por variables de
entorno con hash (HOTEL_RECEPCION_PASSWORD_HASH / HOTEL_ADMIN_PASSWORD_HASH).
"""
import functools
import hmac
import os
import secrets

from flask import abort, flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash

ROL_ADMINISTRADOR = "administrador"
ROL_RECEPCIONISTA = "recepcionista"

# Hashes de las contraseñas vigentes (scrypt). Nunca se guardan en texto plano.
RECEPCION_PASSWORD_HASH = (
    "scrypt:32768:8:1$13HM4MgVtK5dKWXl$f52a104544411a18512592b9b58778ef54842235c704dc46da2892101e911adc0c0ce9d75b6cf765973088e4795ff708676c14fcceda8714827a02302d06d8c2"
)
ADMIN_PASSWORD_HASH = (
    "scrypt:32768:8:1$CkotU3yqDNMvxFSJ$e60c1b20cc9c82f0dafc66d4a107cab0d6dbb989fe6aaa182bcfd866e8472d28151e2b76abb4ec9becd4fe1d60cdeec192e031163bb14871efa638b624a55d97"
)


def _hash_recepcion():
    return os.getenv("HOTEL_RECEPCION_PASSWORD_HASH", RECEPCION_PASSWORD_HASH)


def _hash_admin():
    return os.getenv("HOTEL_ADMIN_PASSWORD_HASH", ADMIN_PASSWORD_HASH)


def _verificar(hash_guardado, password):
    if not isinstance(password, str) or not password:
        return False
    try:
        return check_password_hash(hash_guardado, password)
    except (ValueError, TypeError):
        return False


def rol_por_password(password):
    """Devuelve el rol asociado a la contraseña, o None si no coincide."""
    if _verificar(_hash_admin(), password):
        return ROL_ADMINISTRADOR
    if _verificar(_hash_recepcion(), password):
        return ROL_RECEPCIONISTA
    return None


def es_password_admin(password):
    return _verificar(_hash_admin(), password)


def es_admin():
    return session.get("rol") == ROL_ADMINISTRADOR


def solo_admin(vista):
    """Restringe una vista a sesiones con rol administrador."""
    @functools.wraps(vista)
    def envoltorio(*args, **kwargs):
        if not es_admin():
            flash("Esta acción requiere iniciar sesión como administrador.", "error")
            return redirect(url_for("main.dashboard"))
        return vista(*args, **kwargs)
    return envoltorio


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validar_csrf():
    if request.method != "POST":
        return None
    enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    esperado = session.get("csrf_token", "")
    if not esperado or not enviado or not hmac.compare_digest(enviado, esperado):
        abort(400, description="Token de seguridad inválido. Recarga la página e inténtalo de nuevo.")
    return None


def clave_secreta():
    """Clave de sesión: HOTEL_SECRET_KEY si existe; si no, el secreto compartido
    guardado en la base (válido entre instancias). Sin base, una clave aleatoria."""
    if os.getenv("HOTEL_SECRET_KEY"):
        return os.getenv("HOTEL_SECRET_KEY")
    try:
        from app.persistence.persistencia import obtener_secreto_sesion
        return obtener_secreto_sesion()
    except Exception:
        return secrets.token_hex(32)
