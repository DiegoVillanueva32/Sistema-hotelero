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
    "scrypt:32768:8:1$ZkvyeA5EZpevYawa$396b608d955c9f1a3d9a9f9ad5f684fc4774f75f69b98eb1d42b83f12a072bbedaa58b38e75f38a03f4388dd1e8bc7d8077f16b67d244599ce6eb7e99c453c9a"
)
ADMIN_PASSWORD_HASH = (
    "scrypt:32768:8:1$I3HXmovzjoLm8gPa$c41deffe2e4bf26e40c57cb7407745b19aa65b0152984d1d5279ba5ce7b544fcb6e23ce6f4cf3dbe89ac02832ef6344153a6298489e7df0a4ad889a061993787"
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
