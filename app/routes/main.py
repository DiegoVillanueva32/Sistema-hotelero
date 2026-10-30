import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.hotel_service import hotel_service

bp = Blueprint("main", __name__)


def ejecutar_accion(accion, *args, **kwargs):
    try:
        resultado = accion(*args, **kwargs)
        if isinstance(resultado, tuple):
            ok, mensaje = resultado
            flash(mensaje, "success" if ok else "error")
            if ok:
                hotel_service.persistir()
        else:
            hotel_service.persistir()
        return True
    except Exception as exc:
        flash(f"No se pudo completar la operación: {exc}", "error")
        return False


@bp.route("/")
def dashboard():
    gestor = hotel_service.gestor
    habitaciones = list(gestor.consultar_matriz().values())
    estados = {}
    for habitacion in habitaciones:
        estados[habitacion.estado] = estados.get(habitacion.estado, 0) + 1
    return render_template(
        "dashboard.html",
        total=len(habitaciones),
        estados=estados,
        ocupadas=sum(1 for h in habitaciones if h.estado == "Ocupado"),
        reservas=len(gestor.historial_reservas),
        pagos=sum(p["monto"] for p in gestor.obtener_pagos()),
        notifications=gestor.obtener_notificaciones()[:5],
    )


@bp.route("/habitaciones")
def habitaciones():
    gestor = hotel_service.gestor
    piso = request.args.get("piso", "Todos")
    tipo = request.args.get("tipo", "Todos")
    estado = request.args.get("estado", "Todos")
    habitaciones = gestor.consultar_matriz_filtrada(piso, tipo, estado)
    return render_template(
        "habitaciones.html",
        habitaciones=habitaciones,
        piso=piso,
        tipo=tipo,
        estado=estado,
    )


@bp.route("/habitaciones/<id_habitacion>", methods=["POST"])
def accion_habitacion(id_habitacion):
    accion = request.form.get("accion")
    gestor = hotel_service.gestor
    if accion == "mantenimiento":
        ejecutar_accion(gestor.poner_en_mantenimiento, id_habitacion, request.form.get("motivo", ""))
    elif accion == "finalizar_mantenimiento":
        ejecutar_accion(gestor.quitar_mantenimiento, id_habitacion, True)
    elif accion == "asignar_limpieza":
        ejecutar_accion(gestor.asignar_limpieza, id_habitacion, request.form.get("empleado", "Empleado 1"))
    elif accion == "finalizar_limpieza":
        ejecutar_accion(gestor.finalizar_limpieza, id_habitacion)
    return redirect(url_for("main.habitaciones", piso=request.args.get("piso", "Todos")))


@bp.route("/checkin", methods=["GET", "POST"])
def checkin():
    gestor = hotel_service.gestor
    if request.method == "POST":
        hora = datetime.datetime.now().hour
        ejecutar_accion(
            gestor.procesar_checkin,
            request.form.get("habitacion", ""),
            request.form.get("nombre", "").strip(),
            request.form.get("documento", "").strip(),
            hora,
            request.form.get("administrador") == "1",
        )
        return redirect(url_for("main.checkin"))
    disponibles = [h for h in gestor.consultar_matriz().values() if h.estado in ("Disponible", "Reserva")]
    return render_template("checkin.html", habitaciones=disponibles)


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    gestor = hotel_service.gestor
    if request.method == "POST":
        ejecutar_accion(gestor.procesar_checkout, request.form.get("habitacion", ""))
        return redirect(url_for("main.checkout"))
    ocupadas = [h for h in gestor.consultar_matriz().values() if h.estado == "Ocupado"]
    return render_template("checkout.html", habitaciones=ocupadas)


@bp.route("/reservas", methods=["GET", "POST"])
def reservas():
    gestor = hotel_service.gestor
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "crear":
            entrada = request.form.get("fecha_entrada") or None
            salida = request.form.get("fecha_salida") or None
            fecha_entrada = datetime.date.fromisoformat(entrada) if entrada else None
            fecha_salida = datetime.date.fromisoformat(salida) if salida else None
            ejecutar_accion(
                gestor.crear_reserva,
                request.form.get("habitacion", ""),
                request.form.get("nombre", "").strip(),
                request.form.get("documento", "").strip(),
                fecha_entrada,
                fecha_salida,
            )
        elif accion == "cancelar":
            ejecutar_accion(gestor.cancelar_reserva, request.form.get("habitacion", ""))
        elif accion == "noshow":
            ejecutar_accion(gestor.procesar_no_show)
        return redirect(url_for("main.reservas"))

    disponibles = [h for h in gestor.consultar_matriz().values() if h.estado in ("Disponible", "Reserva")]
    return render_template(
        "reservas.html",
        habitaciones=disponibles,
        reservas=gestor.obtener_historial_reservas(),
    )


@bp.route("/limpieza", methods=["GET", "POST"])
def limpieza():
    gestor = hotel_service.gestor
    if request.method == "POST":
        accion = request.form.get("accion")
        id_habitacion = request.form.get("habitacion", "")
        if accion == "asignar":
            ejecutar_accion(gestor.asignar_limpieza, id_habitacion, request.form.get("empleado", "Empleado 1"))
        elif accion == "automatico":
            ejecutar_accion(gestor.asignar_limpieza_automatica)
        elif accion == "finalizar":
            ejecutar_accion(gestor.finalizar_limpieza, id_habitacion)
        return redirect(url_for("main.limpieza"))

    en_limpieza = [h for h in gestor.consultar_matriz().values() if h.estado == "En limpieza"]
    return render_template(
        "limpieza.html",
        habitaciones=en_limpieza,
        empleados=gestor.empleados_limpieza,
        hoja=gestor.hoja_trabajo_limpieza(),
    )


@bp.route("/pagos", methods=["GET", "POST"])
def pagos():
    gestor = hotel_service.gestor
    if request.method == "POST":
        ejecutar_accion(
            gestor.registrar_pago,
            request.form.get("habitacion", ""),
            float(request.form.get("monto", "0") or 0),
            request.form.get("metodo", "Efectivo"),
        )
        return redirect(url_for("main.pagos"))
    ocupadas = [h for h in gestor.consultar_matriz().values() if h.estado == "Ocupado"]
    return render_template("pagos.html", habitaciones=ocupadas, pagos=gestor.obtener_pagos())
