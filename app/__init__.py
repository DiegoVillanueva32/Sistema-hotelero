import os
import datetime

from flask import Flask

from app.persistence.persistencia import cargar_estado, guardar_estado, inicializar_bd
from app.core.gestor_hotel import GestorHotel


def create_app(config=None):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        instance_relative_config=True,
    )
    from app.seguridad import clave_secreta, csrf_token, es_admin, validar_csrf

    app.config.update(
        SECRET_KEY=clave_secreta(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("HOTEL_COOKIE_SECURE", "1") == "1",
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)

    gestor = GestorHotel()
    app.extensions["gestor_hotel"] = gestor

    try:
        inicializar_bd()
        cargar_estado(gestor)
        gestor.actualizar_estados_reservas()
        guardar_estado(gestor)
        app.extensions["database_available"] = True
    except Exception as exc:
        app.extensions["database_available"] = False
        app.extensions["database_error"] = str(exc)

    from app.routes.main import bp
    app.register_blueprint(bp)

    def hora_espanola(valor):
        if not valor:
            return "—"
        if isinstance(valor, str):
            try:
                valor = datetime.datetime.fromisoformat(valor)
            except ValueError:
                try:
                    valor = datetime.datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return valor
        hora = valor.hour % 12 or 12
        periodo = "a.m." if valor.hour < 12 else "p.m."
        return f"{hora}:{valor.minute:02d} {periodo}"

    def fecha_espanola(valor):
        if not valor:
            return "—"
        if isinstance(valor, str):
            try:
                valor = datetime.datetime.fromisoformat(valor)
            except ValueError:
                return valor[:10] if len(valor) >= 10 else valor
        return valor.strftime("%d/%m/%Y")

    app.jinja_env.filters["hora_espanola"] = hora_espanola
    app.jinja_env.filters["fecha_espanola"] = fecha_espanola

    @app.context_processor
    def shared_context():
        return {
            "database_available": app.extensions["database_available"],
            "database_error": app.extensions.get("database_error"),
            "csrf_token": csrf_token,
            "es_admin": es_admin,
        }

    @app.before_request
    def proteger_formularios():
        return validar_csrf()

    @app.after_request
    def cabeceras_seguridad(respuesta):
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        respuesta.headers.setdefault("Referrer-Policy", "same-origin")
        respuesta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'")
        return respuesta

    return app
