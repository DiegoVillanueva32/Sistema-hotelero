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
    app.config.update(
        SECRET_KEY=os.getenv("HOTEL_SECRET_KEY", "desarrollo-cambiar-en-produccion"),
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

    app.jinja_env.filters["hora_espanola"] = hora_espanola

    @app.context_processor
    def shared_context():
        return {
            "database_available": app.extensions["database_available"],
            "database_error": app.extensions.get("database_error"),
        }

    return app
