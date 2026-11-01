# persistencia.py
"""
Capa de persistencia con MySQL/MariaDB.
Guarda y restaura TODO el estado del GestorHotel.
"""
import configparser
import datetime
import hmac
import os
from pathlib import Path
import re

import mysql.connector

from app.core.habitacion import Habitacion

CONFIG_PATH = Path(__file__).resolve().parents[2] / "database.ini"


def _configuracion_mysql():
    config = configparser.ConfigParser(interpolation=None)
    if CONFIG_PATH.exists():
        config.read(CONFIG_PATH, encoding="utf-8")
    seccion = config["mysql"] if config.has_section("mysql") else {}
    configuracion = {
        "host": os.getenv("HOTEL_DB_HOST", seccion.get("host", "127.0.0.1")),
        "port": int(os.getenv("HOTEL_DB_PORT", seccion.get("port", "3306"))),
        "user": os.getenv("HOTEL_DB_USER", seccion.get("user", "root")),
        "password": os.getenv("HOTEL_DB_PASSWORD", seccion.get("password", "")),
        "database": os.getenv(
            "HOTEL_DB_NAME", seccion.get("database", "sistema_hotelero")),
    }
    ssl_ca = os.getenv("HOTEL_DB_SSL_CA", "").strip()
    if ssl_ca:
        configuracion["ssl_ca"] = ssl_ca
        configuracion["ssl_verify_cert"] = True
        configuracion["ssl_verify_identity"] = True
    return configuracion


def validar_password_admin(password_ingresada):
    """Valida el acceso administrativo sin registrar ni mostrar la contraseña."""
    if not isinstance(password_ingresada, str):
        return False
    password_ingresada = password_ingresada.strip()

    config = configparser.ConfigParser(interpolation=None)
    if CONFIG_PATH.exists():
        config.read(CONFIG_PATH, encoding="utf-8")

    password_admin = os.getenv("HOTEL_ADMIN_PASSWORD")
    if not password_admin and config.has_section("admin"):
        password_admin = config.get("admin", "password", fallback="")
    if not password_admin:
        password_admin = _configuracion_mysql()["password"]
    if not password_admin:
        password_admin = "admin123"
    if password_admin:
        password_admin = password_admin.strip()

    if not password_admin:
        return False

    try:
        return hmac.compare_digest(password_ingresada, password_admin)
    except TypeError:
        return False


def _conectar(sin_base=False):
    config = _configuracion_mysql()
    if sin_base:
        config.pop("database")
    return mysql.connector.connect(**config)


def _fecha_desde_bd(valor):
    if valor is None or isinstance(valor, datetime.date):
        return valor
    return datetime.date.fromisoformat(valor)


def _fecha_hora_desde_bd(valor):
    if valor is None or isinstance(valor, datetime.datetime):
        return valor
    return datetime.datetime.fromisoformat(valor)


def _fecha_hora_para_bd(valor):
    return valor.strftime("%Y-%m-%d %H:%M:%S") if valor else None


def _consultar_todos(cursor, consulta, parametros=None):
    cursor.execute(consulta, parametros or ())
    return cursor.fetchall()


def _consultar_uno(cursor, consulta, parametros=None):
    cursor.execute(consulta, parametros or ())
    return cursor.fetchone()


def inicializar_bd():
    """Crea las tablas si no existen."""
    nombre_bd = _configuracion_mysql()["database"]
    if not re.fullmatch(r"[A-Za-z0-9_]+", nombre_bd):
        raise ValueError("El nombre de la base solo puede contener letras, números y _.")

    servidor = _conectar(sin_base=True)
    cursor_servidor = servidor.cursor()
    cursor_servidor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{nombre_bd}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    servidor.commit()
    cursor_servidor.close()
    servidor.close()

    conn = _conectar()
    c = conn.cursor()
    esquema = """
    CREATE TABLE IF NOT EXISTS habitaciones (
        id VARCHAR(10) PRIMARY KEY, piso INT, tipo VARCHAR(30), precio DECIMAL(12,2),
        estado VARCHAR(30), huesped_nombre VARCHAR(255), huesped_doc VARCHAR(50),
        empleado_limpieza VARCHAR(50), fecha_entrada DATE, fecha_salida DATE,
        hora_inicio_limpieza DATETIME, hora_fin_limpieza DATETIME
    );
    CREATE TABLE IF NOT EXISTS motivos_mantenimiento (
        id_habitacion VARCHAR(10) PRIMARY KEY, motivo TEXT
    );
    CREATE TABLE IF NOT EXISTS lista_negra (
        doc VARCHAR(50) PRIMARY KEY, motivo TEXT
    );
    CREATE TABLE IF NOT EXISTS clientes_frecuentes (
        doc VARCHAR(50) PRIMARY KEY, visitas INT
    );
    CREATE TABLE IF NOT EXISTS fechas_salida (
        id_habitacion VARCHAR(10) PRIMARY KEY, fecha DATETIME
    );
    CREATE TABLE IF NOT EXISTS notificaciones (
        id INT PRIMARY KEY AUTO_INCREMENT, mensaje TEXT
    );
    CREATE TABLE IF NOT EXISTS habitaciones_noshow (
        id_habitacion VARCHAR(10) PRIMARY KEY
    );
    CREATE TABLE IF NOT EXISTS turno (
        id INT PRIMARY KEY,
        abierto TINYINT, recepcionista VARCHAR(255),
        hora_apertura DATETIME, hora_cierre DATETIME,
        checkins INT, checkouts INT
    );
    CREATE TABLE IF NOT EXISTS historial_reservas (
        id INT PRIMARY KEY AUTO_INCREMENT,
        id_habitacion VARCHAR(10), huesped_nombre VARCHAR(255), huesped_doc VARCHAR(50),
        tipo VARCHAR(30), precio DECIMAL(12,2), fecha_entrada VARCHAR(32),
        fecha_salida VARCHAR(32), estado_final VARCHAR(50), fecha_registro VARCHAR(32)
    );
    CREATE TABLE IF NOT EXISTS pagos (
        id INT PRIMARY KEY AUTO_INCREMENT,
        id_habitacion VARCHAR(10), huesped VARCHAR(255), doc VARCHAR(50),
        monto DECIMAL(12,2), metodo VARCHAR(50), fecha VARCHAR(32),
        monto_base DECIMAL(12,2) NOT NULL DEFAULT 0,
        descuento DECIMAL(12,2) NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS empleados_limpieza (
        nombre VARCHAR(50) PRIMARY KEY, habitaciones_asignadas INT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS historial_turnos (
        id INT PRIMARY KEY AUTO_INCREMENT,
        recepcionista VARCHAR(255), hora_apertura DATETIME, hora_cierre DATETIME,
        checkins INT, checkouts INT
    );
    CREATE TABLE IF NOT EXISTS auditoria (
        id INT PRIMARY KEY AUTO_INCREMENT,
        fecha DATETIME NOT NULL, usuario VARCHAR(255) NOT NULL,
        accion VARCHAR(100) NOT NULL, id_habitacion VARCHAR(10), detalle TEXT
    );
    CREATE TABLE IF NOT EXISTS configuracion (
        clave VARCHAR(100) PRIMARY KEY, valor VARCHAR(255) NOT NULL
    );
    """
    for sentencia in esquema.split(";"):
        if sentencia.strip():
            c.execute(sentencia)
    c.execute("SHOW COLUMNS FROM pagos")
    columnas_pagos = {fila[0] for fila in c.fetchall()}
    if "monto_base" not in columnas_pagos:
        c.execute("ALTER TABLE pagos ADD COLUMN monto_base DECIMAL(12,2) NOT NULL DEFAULT 0")
        c.execute("UPDATE pagos SET monto_base=monto")
    if "descuento" not in columnas_pagos:
        c.execute("ALTER TABLE pagos ADD COLUMN descuento DECIMAL(12,2) NOT NULL DEFAULT 0")
    conn.commit()
    c.close()
    conn.close()


def guardar_estado(gestor):
    """Persiste todo el estado del GestorHotel en MySQL."""
    conn = _conectar()
    c = conn.cursor()

    # ---------- Habitaciones ----------
    c.execute("DELETE FROM habitaciones")
    for h in gestor.habitaciones.values():
        c.execute(
            "INSERT INTO habitaciones VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (h.id_habitacion, h.piso, h.tipo, h.precio, h.estado,
             h.huesped_nombre, h.huesped_doc, h.empleado_limpieza,
             h.fecha_entrada.isoformat() if h.fecha_entrada else None,
             h.fecha_salida.isoformat() if h.fecha_salida else None,
             _fecha_hora_para_bd(h.hora_inicio_limpieza),
             _fecha_hora_para_bd(h.hora_fin_limpieza))
        )

    # ---------- Motivos de mantenimiento ----------
    c.execute("DELETE FROM motivos_mantenimiento")
    for k, v in gestor.motivos_mantenimiento.items():
        c.execute("INSERT INTO motivos_mantenimiento VALUES (%s,%s)", (k, v))

    # ---------- Lista negra ----------
    c.execute("DELETE FROM lista_negra")
    for k, v in gestor.lista_negra.items():
        c.execute("INSERT INTO lista_negra VALUES (%s,%s)", (k, v))

    # ---------- Clientes frecuentes ----------
    c.execute("DELETE FROM clientes_frecuentes")
    for k, v in gestor.clientes_frecuentes.items():
        c.execute("INSERT INTO clientes_frecuentes VALUES (%s,%s)", (k, v))

    # ---------- Fechas de salida ----------
    c.execute("DELETE FROM fechas_salida")
    for k, v in gestor.fechas_salida.items():
        c.execute("INSERT INTO fechas_salida VALUES (%s,%s)",
              (k, _fecha_hora_para_bd(v)))

    # ---------- Notificaciones ----------
    c.execute("DELETE FROM notificaciones")
    for n in gestor.notificaciones:
        c.execute("INSERT INTO notificaciones (mensaje) VALUES (%s)", (n,))

    # ---------- Habitaciones liberadas por No-Show ----------
    c.execute("DELETE FROM habitaciones_noshow")
    for h in gestor.habitaciones_noshow:
        c.execute("INSERT INTO habitaciones_noshow VALUES (%s)", (h,))

    # ---------- Turno actual ----------
    t = gestor.turno_actual
    c.execute("DELETE FROM turno")
    c.execute("INSERT INTO turno VALUES (1,%s,%s,%s,%s,%s,%s)", (
        1 if t["abierto"] else 0, t["recepcionista"],
        _fecha_hora_para_bd(t["hora_apertura"]),
        _fecha_hora_para_bd(t["hora_cierre"]),
        t["checkins_realizados"], t["checkouts_realizados"]
    ))

    # ---------- Historial de reservas (RF-30) ----------
    c.execute("DELETE FROM historial_reservas")
    for r in gestor.historial_reservas:
        c.execute(
            "INSERT INTO historial_reservas "
            "(id_habitacion,huesped_nombre,huesped_doc,tipo,precio,"
            " fecha_entrada,fecha_salida,estado_final,fecha_registro) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (r["id_habitacion"], r["huesped_nombre"], r["huesped_doc"],
             r["tipo"], r["precio"],
             r["fecha_entrada"], r["fecha_salida"],
             r["estado_final"], r["fecha_registro"])
        )

    # ---------- Pagos (RF-44) ----------
    c.execute("DELETE FROM pagos")
    for p in gestor.pagos:
        c.execute(
            "INSERT INTO pagos "
            "(id_habitacion,huesped,doc,monto,metodo,fecha,monto_base,descuento) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (p["id_habitacion"], p["huesped"], p["doc"],
             p["monto"], p["metodo"], p["fecha"],
             p.get("monto_base", p["monto"]), p.get("descuento", 0))
        )

    # ---------- Auditoría (RF-50) ----------
    c.execute("DELETE FROM auditoria")
    for evento in gestor.auditoria:
        c.execute(
            "INSERT INTO auditoria (fecha,usuario,accion,id_habitacion,detalle) "
            "VALUES (%s,%s,%s,%s,%s)",
            (evento["fecha"], evento["usuario"], evento["accion"],
             evento["id_habitacion"], evento["detalle"])
        )

    # ---------- Configuración ----------
    c.execute("DELETE FROM configuracion")
    c.execute("INSERT INTO configuracion (clave,valor) VALUES (%s,%s)",
              ("descuento_cliente_frecuente", str(gestor.descuento_cliente_frecuente)))

    # ---------- Empleados de limpieza ----------
    c.execute("DELETE FROM empleados_limpieza")
    for nombre, asignadas in gestor.empleados_limpieza.items():
        c.execute("INSERT INTO empleados_limpieza VALUES (%s,%s)",
                  (nombre, asignadas))

    # ---------- Historial de turnos ----------
    c.execute("DELETE FROM historial_turnos")
    for turno in gestor.turno_actual["historial_turnos"]:
        c.execute(
            "INSERT INTO historial_turnos "
            "(recepcionista,hora_apertura,hora_cierre,checkins,checkouts) "
            "VALUES (%s,%s,%s,%s,%s)",
            (turno["recepcionista"],
             _fecha_hora_para_bd(turno["hora_apertura"]),
             _fecha_hora_para_bd(turno["hora_cierre"]),
             turno["checkins_realizados"], turno["checkouts_realizados"])
        )

    conn.commit()
    conn.close()


def cargar_estado(gestor):
    """Restaura el estado del GestorHotel desde MySQL (si existe)."""
    conn = _conectar()
    c = conn.cursor()

    # ---------- Habitaciones ----------
    filas = _consultar_todos(c, "SELECT * FROM habitaciones")
    if filas:
        gestor.habitaciones.clear()
        for fila in filas:
            (id_h, piso, tipo, precio, estado, hn, hd, el,
             fe, fs, hil, hfl) = fila
            hab = Habitacion(id_h, piso, tipo, float(precio))
            hab.estado = estado
            hab.huesped_nombre = hn
            hab.huesped_doc = hd
            hab.empleado_limpieza = el
            hab.fecha_entrada = _fecha_desde_bd(fe)
            hab.fecha_salida = _fecha_desde_bd(fs)
            hab.hora_inicio_limpieza = _fecha_hora_desde_bd(hil)
            hab.hora_fin_limpieza = _fecha_hora_desde_bd(hfl)
            gestor.habitaciones[id_h] = hab

    # ---------- Motivos mantenimiento ----------
    gestor.motivos_mantenimiento = dict(_consultar_todos(
        c, "SELECT id_habitacion, motivo FROM motivos_mantenimiento"))

    # ---------- Lista negra ----------
    gestor.lista_negra = dict(_consultar_todos(
        c, "SELECT doc, motivo FROM lista_negra"))

    # ---------- Clientes frecuentes ----------
    gestor.clientes_frecuentes = dict(_consultar_todos(
        c, "SELECT doc, visitas FROM clientes_frecuentes"))

    # ---------- Fechas de salida ----------
    gestor.fechas_salida = {
        k: _fecha_hora_desde_bd(v)
        for k, v in _consultar_todos(
            c, "SELECT id_habitacion, fecha FROM fechas_salida")
    }

    # ---------- Notificaciones ----------
    gestor.notificaciones = [r[0] for r in _consultar_todos(
        c, "SELECT mensaje FROM notificaciones ORDER BY id")]

    # ---------- Habitaciones No-Show ----------
    gestor.habitaciones_noshow = [r[0] for r in _consultar_todos(
        c, "SELECT id_habitacion FROM habitaciones_noshow")]

    # ---------- Turno ----------
    fila = _consultar_uno(c, "SELECT * FROM turno WHERE id=1")
    if fila:
        _, ab, rec, ha, hc, ci, co = fila
        gestor.turno_actual["abierto"] = bool(ab)
        gestor.turno_actual["recepcionista"] = rec
        gestor.turno_actual["hora_apertura"] = (
            _fecha_hora_desde_bd(ha))
        gestor.turno_actual["hora_cierre"] = (
            _fecha_hora_desde_bd(hc))
        gestor.turno_actual["checkins_realizados"] = ci or 0
        gestor.turno_actual["checkouts_realizados"] = co or 0

    # ---------- Historial de reservas (RF-30) ----------
    gestor.historial_reservas = []
    for r in _consultar_todos(
            c, "SELECT id_habitacion,huesped_nombre,huesped_doc,"
            "tipo,precio,fecha_entrada,fecha_salida,"
            "estado_final,fecha_registro FROM historial_reservas"):
        gestor.historial_reservas.append({
            "id_habitacion": r[0], "huesped_nombre": r[1], "huesped_doc": r[2],
            "tipo": r[3], "precio": float(r[4]) if r[4] is not None else None,
            "fecha_entrada": r[5], "fecha_salida": r[6],
            "estado_final": r[7], "fecha_registro": r[8],
        })

    # ---------- Pagos (RF-44) ----------
    gestor.pagos = []
    for r in _consultar_todos(
            c, "SELECT id_habitacion,huesped,doc,monto,metodo,fecha,monto_base,descuento "
            "FROM pagos ORDER BY id"):
        gestor.pagos.append({
            "id_habitacion": r[0], "huesped": r[1], "doc": r[2],
            "monto": float(r[3]) if r[3] is not None else None,
            "metodo": r[4], "fecha": r[5],
            "monto_base": float(r[6]) if r[6] is not None else float(r[3]),
            "descuento": float(r[7]) if r[7] is not None else 0.0,
        })

    # ---------- Auditoría (RF-50) ----------
    gestor.auditoria = []
    for fecha, usuario, accion, id_habitacion, detalle in _consultar_todos(
            c, "SELECT fecha,usuario,accion,id_habitacion,detalle "
            "FROM auditoria ORDER BY id"):
        gestor.auditoria.append({
            "fecha": fecha.strftime("%Y-%m-%d %H:%M") if fecha else "",
            "usuario": usuario,
            "accion": accion,
            "id_habitacion": id_habitacion,
            "detalle": detalle or "",
        })

    descuento = _consultar_uno(
        c, "SELECT valor FROM configuracion WHERE clave=%s",
        ("descuento_cliente_frecuente",))
    if descuento:
        gestor.descuento_cliente_frecuente = float(descuento[0])

    # ---------- Empleados de limpieza ----------
    empleados = dict(_consultar_todos(
        c, "SELECT nombre, habitaciones_asignadas FROM empleados_limpieza"))
    if empleados:
        gestor.empleados_limpieza = empleados

    # ---------- Historial de turnos ----------
    gestor.turno_actual["historial_turnos"] = []
    for recepcionista, apertura, cierre, checkins, checkouts in _consultar_todos(
            c, "SELECT recepcionista,hora_apertura,hora_cierre,checkins,checkouts "
            "FROM historial_turnos ORDER BY id"):
        gestor.turno_actual["historial_turnos"].append({
            "abierto": False,
            "recepcionista": recepcionista,
            "hora_apertura": _fecha_hora_desde_bd(apertura),
            "hora_cierre": _fecha_hora_desde_bd(cierre),
            "checkins_realizados": checkins or 0,
            "checkouts_realizados": checkouts or 0,
        })

    conn.close()
    return bool(filas)