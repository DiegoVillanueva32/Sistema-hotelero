"""Capa de persistencia MySQL con el modelo del DER del documento Momento 2.

Tablas del modelo: rol, usuario, tipo_habitacion, estado_habitacion, habitacion,
huesped, reserva, estancia, pago, factura, personal_limpieza, limpieza, auditoria.

Tablas auxiliares que se conservan: turno, historial_turnos, notificaciones,
fechas_salida, habitaciones_noshow, configuracion.

Las tablas antiguas (habitaciones, pagos, ...) se leen una sola vez, si el modelo
nuevo está vacío, para importar los datos existentes. No se borran.
"""
import configparser
import datetime
import os
import re
import secrets
from pathlib import Path

import mysql.connector

from app.persistence import legacy
from app.core.habitacion import Habitacion

CONFIG_PATH = Path(__file__).resolve().parents[2] / "database.ini"

TIPOS = {"Doble": (2, 150000.0), "Familiar": (4, 200000.0), "Normal": (2, 100000.0)}
ESTADOS = ["Disponible", "Ocupado", "Reserva", "En limpieza", "Pendiente", "Mantenimiento"]
ROLES = [("Recepcionista", "Atiende check-in, check-out y reservas"),
         ("Administrador", "Administra tarifas, reportes y mantenimiento"),
         ("Limpieza", "Personal de limpieza")]

DDL = [
    """CREATE TABLE IF NOT EXISTS rol (
        id_rol INT PRIMARY KEY AUTO_INCREMENT,
        nombre VARCHAR(50) NOT NULL UNIQUE,
        descripcion VARCHAR(150)
    )""",
    """CREATE TABLE IF NOT EXISTS usuario (
        id_usuario INT PRIMARY KEY AUTO_INCREMENT,
        nombre VARCHAR(100) NOT NULL,
        correo VARCHAR(120) NOT NULL UNIQUE,
        contrasena VARCHAR(255) NOT NULL,
        id_rol INT NOT NULL,
        activo BOOLEAN NOT NULL DEFAULT TRUE,
        fecha_creacion DATETIME NOT NULL,
        FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
    )""",
    """CREATE TABLE IF NOT EXISTS tipo_habitacion (
        id_tipo INT PRIMARY KEY AUTO_INCREMENT,
        nombre VARCHAR(50) NOT NULL UNIQUE,
        capacidad_max INT NOT NULL,
        tarifa_base DECIMAL(10,2) NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS estado_habitacion (
        id_estado INT PRIMARY KEY AUTO_INCREMENT,
        nombre VARCHAR(50) NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS habitacion (
        id_habitacion INT PRIMARY KEY,
        numero VARCHAR(10) NOT NULL UNIQUE,
        piso INT NOT NULL,
        id_tipo INT NOT NULL,
        id_estado INT NOT NULL,
        precio_noche DECIMAL(10,2) NOT NULL,
        descripcion VARCHAR(200) NULL,
        FOREIGN KEY (id_tipo) REFERENCES tipo_habitacion(id_tipo),
        FOREIGN KEY (id_estado) REFERENCES estado_habitacion(id_estado)
    )""",
    """CREATE TABLE IF NOT EXISTS huesped (
        id_huesped INT PRIMARY KEY AUTO_INCREMENT,
        documento VARCHAR(20) NOT NULL UNIQUE,
        nombre VARCHAR(100) NOT NULL,
        telefono VARCHAR(20) NULL,
        correo VARCHAR(120) NULL,
        es_frecuente BOOLEAN NOT NULL DEFAULT FALSE,
        en_lista_negra BOOLEAN NOT NULL DEFAULT FALSE,
        observaciones TEXT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS reserva (
        id_reserva INT PRIMARY KEY AUTO_INCREMENT,
        id_huesped INT NOT NULL,
        id_habitacion INT NOT NULL,
        fecha_inicio DATE NOT NULL,
        fecha_fin DATE NOT NULL,
        hora_limite TIME NOT NULL,
        estado VARCHAR(20) NOT NULL,
        id_usuario_crea INT NOT NULL,
        fecha_creacion DATETIME NOT NULL,
        FOREIGN KEY (id_huesped) REFERENCES huesped(id_huesped),
        FOREIGN KEY (id_habitacion) REFERENCES habitacion(id_habitacion),
        FOREIGN KEY (id_usuario_crea) REFERENCES usuario(id_usuario)
    )""",
    """CREATE TABLE IF NOT EXISTS estancia (
        id_estancia INT PRIMARY KEY AUTO_INCREMENT,
        id_reserva INT NULL,
        id_huesped INT NOT NULL,
        id_habitacion INT NOT NULL,
        fecha_checkin DATETIME NOT NULL,
        fecha_checkout DATETIME NULL,
        estado VARCHAR(20) NOT NULL,
        id_usuario_checkin INT NOT NULL,
        id_usuario_checkout INT NULL,
        FOREIGN KEY (id_reserva) REFERENCES reserva(id_reserva),
        FOREIGN KEY (id_huesped) REFERENCES huesped(id_huesped),
        FOREIGN KEY (id_habitacion) REFERENCES habitacion(id_habitacion),
        FOREIGN KEY (id_usuario_checkin) REFERENCES usuario(id_usuario),
        FOREIGN KEY (id_usuario_checkout) REFERENCES usuario(id_usuario)
    )""",
    """CREATE TABLE IF NOT EXISTS pago (
        id_pago INT PRIMARY KEY AUTO_INCREMENT,
        id_estancia INT NOT NULL,
        monto DECIMAL(10,2) NOT NULL,
        metodo_pago VARCHAR(20) NOT NULL,
        fecha_pago DATETIME NOT NULL,
        id_usuario_registra INT NOT NULL,
        FOREIGN KEY (id_estancia) REFERENCES estancia(id_estancia),
        FOREIGN KEY (id_usuario_registra) REFERENCES usuario(id_usuario)
    )""",
    """CREATE TABLE IF NOT EXISTS factura (
        id_factura INT PRIMARY KEY AUTO_INCREMENT,
        id_pago INT NOT NULL UNIQUE,
        numero_factura VARCHAR(30) NOT NULL UNIQUE,
        subtotal DECIMAL(10,2) NOT NULL,
        descuento DECIMAL(10,2) NOT NULL,
        total DECIMAL(10,2) NOT NULL,
        fecha_emision DATETIME NOT NULL,
        FOREIGN KEY (id_pago) REFERENCES pago(id_pago)
    )""",
    """CREATE TABLE IF NOT EXISTS personal_limpieza (
        id_personal INT PRIMARY KEY AUTO_INCREMENT,
        id_usuario INT NOT NULL UNIQUE,
        nombre VARCHAR(100) NOT NULL,
        asignadas_hoy INT NOT NULL DEFAULT 0,
        limite_diario INT NOT NULL DEFAULT 7,
        disponible BOOLEAN NOT NULL DEFAULT TRUE,
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
    )""",
    """CREATE TABLE IF NOT EXISTS limpieza (
        id_limpieza INT PRIMARY KEY AUTO_INCREMENT,
        id_habitacion INT NOT NULL,
        id_personal INT NOT NULL,
        fecha_asignacion DATE NOT NULL,
        hora_inicio DATETIME NULL,
        hora_fin DATETIME NULL,
        estado VARCHAR(20) NOT NULL,
        observaciones TEXT NULL,
        FOREIGN KEY (id_habitacion) REFERENCES habitacion(id_habitacion),
        FOREIGN KEY (id_personal) REFERENCES personal_limpieza(id_personal)
    )""",
    """CREATE TABLE IF NOT EXISTS auditoria (
        id_log INT PRIMARY KEY AUTO_INCREMENT,
        id_usuario INT NOT NULL,
        accion VARCHAR(50) NOT NULL,
        entidad VARCHAR(50) NOT NULL,
        id_entidad INT NOT NULL DEFAULT 0,
        fecha_hora DATETIME NOT NULL,
        detalle TEXT NULL,
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
    )""",
    """CREATE TABLE IF NOT EXISTS motivos_mantenimiento (
        id_habitacion VARCHAR(10) PRIMARY KEY, motivo TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS notificaciones (
        id INT PRIMARY KEY AUTO_INCREMENT, mensaje TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS habitaciones_noshow (
        id_habitacion VARCHAR(10) PRIMARY KEY
    )""",
    """CREATE TABLE IF NOT EXISTS fechas_salida_estancia (
        id_habitacion VARCHAR(10) PRIMARY KEY, fecha DATETIME
    )""",
    """CREATE TABLE IF NOT EXISTS turno (
        id INT PRIMARY KEY, abierto TINYINT, recepcionista VARCHAR(255),
        hora_apertura DATETIME, hora_cierre DATETIME,
        checkins INT, checkouts INT
    )""",
    """CREATE TABLE IF NOT EXISTS historial_turnos (
        id INT PRIMARY KEY AUTO_INCREMENT,
        recepcionista VARCHAR(255), hora_apertura DATETIME, hora_cierre DATETIME,
        checkins INT, checkouts INT
    )""",
    """CREATE TABLE IF NOT EXISTS configuracion (
        clave VARCHAR(100) PRIMARY KEY, valor VARCHAR(255) NOT NULL
    )""",
]

# Tablas en orden de borrado seguro (hijas primero).
TABLAS_DER = ["factura", "pago", "limpieza", "estancia", "reserva", "personal_limpieza",
              "auditoria", "huesped", "habitacion", "usuario"]


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
        "database": os.getenv("HOTEL_DB_NAME", seccion.get("database", "sistema_hotelero")),
    }
    ssl_ca = os.getenv("HOTEL_DB_SSL_CA", "").strip()
    if ssl_ca:
        configuracion["ssl_ca"] = ssl_ca
        configuracion["ssl_verify_cert"] = True
        configuracion["ssl_verify_identity"] = True
    return configuracion


def _conectar(sin_base=False):
    config = _configuracion_mysql()
    if sin_base:
        config.pop("database")
    return mysql.connector.connect(**config)


def _fecha_hora_para_bd(valor):
    return valor.strftime("%Y-%m-%d %H:%M:%S") if valor else None


def _fecha_hora(texto):
    if not texto or texto == "—":
        return None
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(str(texto), formato)
        except ValueError:
            continue
    return None


def inicializar_bd():
    """Crea la base, el modelo DER y los datos semilla. Importa datos antiguos una vez."""
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

    conn_prev = _conectar()
    cur_prev = conn_prev.cursor()
    cur_prev.execute("SHOW TABLES LIKE 'auditoria'")
    if cur_prev.fetchone():
        cur_prev.execute("SHOW COLUMNS FROM auditoria")
        columnas = {fila[0] for fila in cur_prev.fetchall()}
        if "usuario" in columnas:  # forma antigua: se conserva con otro nombre
            cur_prev.execute("RENAME TABLE auditoria TO auditoria_legacy")
            conn_prev.commit()
    cur_prev.close()
    conn_prev.close()

    legacy.inicializar_bd()  # tablas antiguas (solo lectura para la importación)

    conn = _conectar()
    c = conn.cursor()
    for sentencia in DDL:
        c.execute(sentencia)
    for nombre, descripcion in ROLES:
        c.execute("INSERT IGNORE INTO rol (nombre, descripcion) VALUES (%s,%s)", (nombre, descripcion))
    for nombre in ESTADOS:
        c.execute("INSERT IGNORE INTO estado_habitacion (nombre) VALUES (%s)", (nombre,))
    for nombre, (capacidad, tarifa) in TIPOS.items():
        c.execute("INSERT IGNORE INTO tipo_habitacion (nombre, capacidad_max, tarifa_base) "
                  "VALUES (%s,%s,%s)", (nombre, capacidad, tarifa))
    conn.commit()
    c.close()
    conn.close()


def _mapa(cursor, consulta):
    cursor.execute(consulta)
    return {fila[0]: fila[1] for fila in cursor.fetchall()}


def _usuario_id(cursor, nombre, rol, cache):
    """Devuelve el id de usuario para un nombre, creándolo si no existe."""
    nombre = (nombre or "Sistema").strip() or "Sistema"
    if nombre in cache:
        return cache[nombre]
    cursor.execute("SELECT id_rol FROM rol WHERE nombre=%s", (rol,))
    id_rol = cursor.fetchone()[0]
    slug = re.sub(r"[^a-z0-9]+", ".", nombre.lower()).strip(".") or "sistema"
    correo = f"{slug}@hotel.local"
    n = 1
    while True:
        cursor.execute("SELECT id_usuario, nombre FROM usuario WHERE correo=%s", (correo,))
        fila = cursor.fetchone()
        if fila is None:
            break
        if fila[1] == nombre:
            cache[nombre] = fila[0]
            return fila[0]
        n += 1
        correo = f"{slug}{n}@hotel.local"
    # Sin contraseña de acceso: estos usuarios solo identifican a quien hizo cada acción.
    cursor.execute(
        "INSERT INTO usuario (nombre, correo, contrasena, id_rol, activo, fecha_creacion) "
        "VALUES (%s,%s,%s,%s,TRUE,%s)",
        (nombre, correo, "SIN_ACCESO", id_rol, _fecha_hora_para_bd(datetime.datetime.now())))
    cache[nombre] = cursor.lastrowid
    return cache[nombre]


def _huesped_id(cursor, documento, nombre, telefono, cache):
    if not documento or documento == "—":
        documento = "SIN-DOC"
    if documento in cache:
        return cache[documento]
    cursor.execute("INSERT INTO huesped (documento, nombre, telefono) VALUES (%s,%s,%s)",
                   (documento, nombre or "Sin nombre", telefono))
    cache[documento] = cursor.lastrowid
    return cache[documento]


def guardar_estado(gestor):
    """Escribe todo el estado del GestorHotel en el modelo DER."""
    conn = _conectar()
    c = conn.cursor()
    c.execute("SET FOREIGN_KEY_CHECKS=0")
    for tabla in TABLAS_DER:
        c.execute(f"DELETE FROM {tabla}")
    c.execute("DELETE FROM motivos_mantenimiento")
    c.execute("DELETE FROM notificaciones")
    c.execute("DELETE FROM habitaciones_noshow")
    c.execute("DELETE FROM fechas_salida_estancia")
    c.execute("DELETE FROM turno")
    c.execute("DELETE FROM historial_turnos")
    c.execute("DELETE FROM configuracion WHERE clave = %s", ("descuento_cliente_frecuente",))
    c.execute("SET FOREIGN_KEY_CHECKS=1")

    ids_tipo = _mapa(c, "SELECT nombre, id_tipo FROM tipo_habitacion")
    ids_estado = _mapa(c, "SELECT nombre, id_estado FROM estado_habitacion")
    cache_usuario, cache_huesped = {}, {}

    turno = gestor.turno_actual
    nombre_turno = turno.get("recepcionista") or "Sistema"
    usuario_turno = _usuario_id(c, nombre_turno, "Recepcionista", cache_usuario)
    for evento in gestor.auditoria:
        _usuario_id(c, evento["usuario"], "Recepcionista", cache_usuario)

    # Personal de limpieza (3 empleados) -> usuario + personal_limpieza
    ids_personal = {}
    for nombre_emp, asignadas in gestor.empleados_limpieza.items():
        id_usr = _usuario_id(c, nombre_emp, "Limpieza", cache_usuario)
        c.execute("INSERT INTO personal_limpieza (id_usuario, nombre, asignadas_hoy, "
                  "limite_diario, disponible) VALUES (%s,%s,%s,7,TRUE)",
                  (id_usr, nombre_emp, asignadas))
        ids_personal[nombre_emp] = c.lastrowid

    # Huéspedes conocidos (ocupaciones, reservas, historial, pagos, listas)
    for hab in gestor.habitaciones.values():
        if hab.huesped_doc:
            _huesped_id(c, hab.huesped_doc, hab.huesped_nombre, hab.huesped_telefono, cache_huesped)
    for doc, motivo in gestor.lista_negra.items():
        _huesped_id(c, doc, "Lista negra", None, cache_huesped)
        c.execute("UPDATE huesped SET en_lista_negra=TRUE, observaciones=%s WHERE documento=%s",
                  (motivo, doc))
    for doc, visitas in gestor.clientes_frecuentes.items():
        _huesped_id(c, doc, None, None, cache_huesped)
        c.execute("UPDATE huesped SET es_frecuente=%s WHERE documento=%s",
                  (visitas > 5, doc))
    for registro in gestor.historial_reservas:
        _huesped_id(c, registro["huesped_doc"], registro["huesped_nombre"], None, cache_huesped)
    for pago in gestor.pagos:
        _huesped_id(c, pago["doc"], pago["huesped"], None, cache_huesped)

    # Habitaciones
    for hab in gestor.habitaciones.values():
        c.execute(
            "INSERT INTO habitacion (id_habitacion, numero, piso, id_tipo, id_estado, "
            "precio_noche, descripcion) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (int(hab.id_habitacion), hab.id_habitacion, hab.piso, ids_tipo[hab.tipo],
             ids_estado[hab.estado], hab.precio,
             gestor.motivos_mantenimiento.get(hab.id_habitacion)))

    # Reservas activas (estado Reserva o Disponible con reserva vigente)
    reserva_por_hab = {}
    for hab in gestor.habitaciones.values():
        if (hab.estado in ("Reserva", "Disponible") and hab.fecha_entrada and hab.fecha_salida
                and hab.huesped_doc):
            c.execute(
                "INSERT INTO reserva (id_huesped, id_habitacion, fecha_inicio, fecha_fin, "
                "hora_limite, estado, id_usuario_crea, fecha_creacion) "
                "VALUES (%s,%s,%s,%s,%s,'Activa',%s,%s)",
                (cache_huesped[hab.huesped_doc], int(hab.id_habitacion), hab.fecha_entrada,
                 hab.fecha_salida, hab.hora_limite + ":00", usuario_turno,
                 _fecha_hora_para_bd(datetime.datetime.now())))
            reserva_por_hab[hab.id_habitacion] = c.lastrowid

    # Estancias: ocupaciones activas y check-outs del historial
    estancia_por_hab_doc = {}
    for hab in gestor.habitaciones.values():
        if hab.estado == "Ocupado" and hab.huesped_doc:
            entrada = hab.fecha_entrada or datetime.date.today()
            c.execute(
                "INSERT INTO estancia (id_reserva, id_huesped, id_habitacion, fecha_checkin, "
                "fecha_checkout, estado, id_usuario_checkin, id_usuario_checkout) "
                "VALUES (%s,%s,%s,%s,NULL,'Activa',%s,NULL)",
                (None, cache_huesped[hab.huesped_doc], int(hab.id_habitacion),
                 _fecha_hora_para_bd(datetime.datetime.combine(entrada, datetime.time(0))),
                 usuario_turno))
            estancia_por_hab_doc[(hab.id_habitacion, hab.huesped_doc)] = c.lastrowid
            if hab.id_habitacion in fechas_salida_de(gestor):
                c.execute("INSERT INTO fechas_salida_estancia VALUES (%s,%s) "
                          "ON DUPLICATE KEY UPDATE fecha=VALUES(fecha)",
                          (hab.id_habitacion, _fecha_hora_para_bd(fechas_salida_de(gestor)[hab.id_habitacion])))

    for registro in gestor.historial_reservas:
        id_hab = registro["id_habitacion"]
        doc = registro["huesped_doc"]
        if doc == "—" or doc is None:
            continue
        entrada = _fecha_hora(registro["fecha_entrada"]) or _fecha_hora(registro["fecha_registro"])
        registrado = _fecha_hora(registro["fecha_registro"]) or datetime.datetime.now()
        if registro["estado_final"] == "Check-out":
            c.execute(
                "INSERT INTO estancia (id_reserva, id_huesped, id_habitacion, fecha_checkin, "
                "fecha_checkout, estado, id_usuario_checkin, id_usuario_checkout) "
                "VALUES (NULL,%s,%s,%s,%s,'Finalizada',%s,%s)",
                (cache_huesped[doc], int(id_hab), _fecha_hora_para_bd(entrada),
                 _fecha_hora_para_bd(registrado), usuario_turno, usuario_turno))
            estancia_por_hab_doc.setdefault((id_hab, doc), c.lastrowid)
        else:
            estado = {"Cancelada": "Cancelada", "No-Show": "No-Show"}.get(
                registro["estado_final"], "Cancelada")
            c.execute(
                "INSERT INTO reserva (id_huesped, id_habitacion, fecha_inicio, fecha_fin, "
                "hora_limite, estado, id_usuario_crea, fecha_creacion) "
                "VALUES (%s,%s,%s,%s,'18:00:00',%s,%s,%s)",
                (cache_huesped[doc], int(id_hab), (entrada or registrado).date(),
                 (_fecha_hora(registro["fecha_salida"]) or registrado).date(), estado,
                 usuario_turno, _fecha_hora_para_bd(registrado)))

    # Pagos y facturas
    for pago in gestor.pagos:
        id_hab, doc = pago["id_habitacion"], pago["doc"]
        id_estancia = estancia_por_hab_doc.get((id_hab, doc))
        if id_estancia is None:
            fecha = _fecha_hora(pago["fecha"]) or datetime.datetime.now()
            c.execute(
                "INSERT INTO estancia (id_reserva, id_huesped, id_habitacion, fecha_checkin, "
                "fecha_checkout, estado, id_usuario_checkin, id_usuario_checkout) "
                "VALUES (NULL,%s,%s,%s,%s,'Finalizada',%s,%s)",
                (cache_huesped.get(doc) or _huesped_id(c, doc or "SIN-DOC", pago["huesped"], None,
                                                      cache_huesped),
                 int(id_hab), _fecha_hora_para_bd(fecha), _fecha_hora_para_bd(fecha),
                 usuario_turno, usuario_turno))
            id_estancia = c.lastrowid
            estancia_por_hab_doc[(id_hab, doc)] = id_estancia
        c.execute(
            "INSERT INTO pago (id_estancia, monto, metodo_pago, fecha_pago, id_usuario_registra) "
            "VALUES (%s,%s,%s,%s,%s)",
            (id_estancia, pago["monto"], pago["metodo"],
             _fecha_hora_para_bd(_fecha_hora(pago["fecha"]) or datetime.datetime.now()),
             usuario_turno))
        id_pago = c.lastrowid
        c.execute(
            "INSERT INTO factura (id_pago, numero_factura, subtotal, descuento, total, fecha_emision) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (id_pago, f"FAC-{id_pago:06d}", pago.get("monto_base", pago["monto"]),
             pago.get("descuento", 0), pago["monto"], _fecha_hora_para_bd(_fecha_hora(pago["fecha"]))))

    # Limpieza (tiempos de cada habitación asignada)
    for hab in gestor.habitaciones.values():
        if hab.empleado_limpieza in ids_personal and hab.hora_inicio_limpieza:
            estado = "Finalizada" if hab.hora_fin_limpieza else "En proceso"
            c.execute(
                "INSERT INTO limpieza (id_habitacion, id_personal, fecha_asignacion, hora_inicio, "
                "hora_fin, estado, observaciones) VALUES (%s,%s,%s,%s,%s,%s,NULL)",
                (int(hab.id_habitacion), ids_personal[hab.empleado_limpieza],
                 hab.hora_inicio_limpieza.date(), _fecha_hora_para_bd(hab.hora_inicio_limpieza),
                 _fecha_hora_para_bd(hab.hora_fin_limpieza), estado))

    # Auditoría
    for evento in gestor.auditoria:
        id_hab = evento["id_habitacion"]
        c.execute(
            "INSERT INTO auditoria (id_usuario, accion, entidad, id_entidad, fecha_hora, detalle) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (_usuario_id(c, evento["usuario"], "Recepcionista", cache_usuario),
             evento["accion"], "habitacion" if id_hab else "general",
             int(id_hab) if id_hab and str(id_hab).isdigit() else 0,
             _fecha_hora_para_bd(_fecha_hora(evento["fecha"])) or _fecha_hora_para_bd(datetime.datetime.now()),
             evento["detalle"]))

    # Auxiliares
    for k, v in gestor.motivos_mantenimiento.items():
        c.execute("INSERT INTO motivos_mantenimiento VALUES (%s,%s)", (k, v))
    for n in gestor.notificaciones:
        c.execute("INSERT INTO notificaciones (mensaje) VALUES (%s)", (n,))
    for h in gestor.habitaciones_noshow:
        c.execute("INSERT IGNORE INTO habitaciones_noshow VALUES (%s)", (h,))
    c.execute("INSERT INTO turno VALUES (1,%s,%s,%s,%s,%s,%s)", (
        1 if turno["abierto"] else 0, turno["recepcionista"],
        _fecha_hora_para_bd(turno["hora_apertura"]), _fecha_hora_para_bd(turno["hora_cierre"]),
        turno["checkins_realizados"], turno["checkouts_realizados"]))
    for t in turno["historial_turnos"]:
        c.execute("INSERT INTO historial_turnos (recepcionista,hora_apertura,hora_cierre,"
                  "checkins,checkouts) VALUES (%s,%s,%s,%s,%s)",
                  (t["recepcionista"], _fecha_hora_para_bd(t["hora_apertura"]),
                   _fecha_hora_para_bd(t["hora_cierre"]), t["checkins_realizados"],
                   t["checkouts_realizados"]))
    c.execute("INSERT INTO configuracion (clave,valor) VALUES (%s,%s) "
              "ON DUPLICATE KEY UPDATE valor=VALUES(valor)",
              ("descuento_cliente_frecuente", str(gestor.descuento_cliente_frecuente)))
    conn.commit()
    c.close()
    conn.close()


def fechas_salida_de(gestor):
    return gestor.fechas_salida


def cargar_estado(gestor):
    """Restaura el GestorHotel. Si el modelo DER está vacío, importa los datos antiguos."""
    conn = _conectar()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM habitacion")
    hay_der = c.fetchone()[0] > 0
    c.close()
    conn.close()
    if not hay_der:
        importado = legacy.cargar_estado(gestor)
        if importado:
            guardar_estado(gestor)  # migra a DER; las tablas antiguas se conservan
        return importado
    _cargar_der(gestor)
    return True


def _cargar_der(gestor):
    conn = _conectar()
    c = conn.cursor()
    c.execute(
        "SELECT h.id_habitacion, h.numero, h.piso, t.nombre, e.nombre, h.precio_noche, h.descripcion "
        "FROM habitacion h JOIN tipo_habitacion t ON t.id_tipo=h.id_tipo "
        "JOIN estado_habitacion e ON e.id_estado=h.id_estado ORDER BY h.id_habitacion")
    filas = c.fetchall()
    gestor.habitaciones.clear()
    gestor.motivos_mantenimiento = {}
    for _, numero, piso, tipo, estado, precio, descripcion in filas:
        hab = Habitacion(numero, piso, tipo, float(precio))
        hab.estado = estado
        gestor.habitaciones[numero] = hab
        if estado == "Mantenimiento" and descripcion:
            gestor.motivos_mantenimiento[numero] = descripcion

    # Reserva activa por habitación
    c.execute(
        "SELECT r.id_habitacion, hu.nombre, hu.documento, hu.telefono, r.fecha_inicio, "
        "r.fecha_fin, r.hora_limite FROM reserva r JOIN huesped hu ON hu.id_huesped=r.id_huesped "
        "WHERE r.estado='Activa'")
    for id_hab, nombre, doc, tel, fi, ff, hl in c.fetchall():
        hab = gestor.habitaciones.get(str(id_hab))
        if hab is None:
            continue
        hab.huesped_nombre, hab.huesped_doc, hab.huesped_telefono = nombre, doc, tel
        hab.fecha_entrada, hab.fecha_salida = fi, ff
        hab.hora_limite = str(hl)[:5]

    # Estancia activa por habitación (ocupación)
    c.execute(
        "SELECT e.id_habitacion, hu.nombre, hu.documento, hu.telefono, e.fecha_checkin "
        "FROM estancia e JOIN huesped hu ON hu.id_huesped=e.id_huesped WHERE e.estado='Activa'")
    for id_hab, nombre, doc, tel, fecha_in in c.fetchall():
        hab = gestor.habitaciones.get(str(id_hab))
        if hab is None:
            continue
        hab.huesped_nombre, hab.huesped_doc, hab.huesped_telefono = nombre, doc, tel
        hab.fecha_entrada = fecha_in.date()
    c.execute("SELECT id_habitacion, fecha FROM fechas_salida_estancia")
    gestor.fechas_salida = {str(k): v for k, v in c.fetchall()}
    for hab in gestor.habitaciones.values():
        if hab.id_habitacion in gestor.fechas_salida and hab.estado == "Ocupado":
            hab.fecha_salida = gestor.fechas_salida[hab.id_habitacion].date()

    # Limpieza (último registro por habitación)
    c.execute(
        "SELECT l.id_habitacion, p.nombre, l.hora_inicio, l.hora_fin FROM limpieza l "
        "JOIN personal_limpieza p ON p.id_personal=l.id_personal ORDER BY l.id_limpieza")
    for id_hab, empleado, inicio, fin in c.fetchall():
        hab = gestor.habitaciones.get(str(id_hab))
        if hab is not None:
            hab.empleado_limpieza = empleado
            hab.hora_inicio_limpieza = inicio
            hab.hora_fin_limpieza = fin

    # Histórico de reservas (canceladas, no-show y check-outs)
    gestor.historial_reservas = []
    c.execute(
        "SELECT r.id_habitacion, hu.nombre, hu.documento, t.nombre, h.precio_noche, "
        "r.fecha_inicio, r.fecha_fin, r.estado, r.fecha_creacion FROM reserva r "
        "JOIN huesped hu ON hu.id_huesped=r.id_huesped JOIN habitacion h ON h.id_habitacion=r.id_habitacion "
        "JOIN tipo_habitacion t ON t.id_tipo=h.id_tipo WHERE r.estado <> 'Activa' ORDER BY r.id_reserva")
    for id_hab, nombre, doc, tipo, precio, fi, ff, estado, creada in c.fetchall():
        gestor.historial_reservas.append({
            "id_habitacion": str(id_hab), "huesped_nombre": nombre, "huesped_doc": doc,
            "tipo": tipo, "precio": float(precio), "fecha_entrada": str(fi),
            "fecha_salida": str(ff), "estado_final": estado,
            "fecha_registro": creada.strftime("%Y-%m-%d %H:%M")})
    c.execute(
        "SELECT e.id_habitacion, hu.nombre, hu.documento, t.nombre, h.precio_noche, "
        "e.fecha_checkin, e.fecha_checkout FROM estancia e "
        "JOIN huesped hu ON hu.id_huesped=e.id_huesped JOIN habitacion h ON h.id_habitacion=e.id_habitacion "
        "JOIN tipo_habitacion t ON t.id_tipo=h.id_tipo WHERE e.estado='Finalizada' ORDER BY e.id_estancia")
    for id_hab, nombre, doc, tipo, precio, fin_in, fin_out in c.fetchall():
        gestor.historial_reservas.append({
            "id_habitacion": str(id_hab), "huesped_nombre": nombre, "huesped_doc": doc,
            "tipo": tipo, "precio": float(precio), "fecha_entrada": str(fin_in.date()),
            "fecha_salida": str(fin_out.date()) if fin_out else "—", "estado_final": "Check-out",
            "fecha_registro": (fin_out or fin_in).strftime("%Y-%m-%d %H:%M")})

    # Pagos con factura
    gestor.pagos = []
    c.execute(
        "SELECT e.id_habitacion, hu.nombre, hu.documento, p.monto, p.metodo_pago, p.fecha_pago, "
        "f.subtotal, f.descuento FROM pago p JOIN estancia e ON e.id_estancia=p.id_estancia "
        "JOIN huesped hu ON hu.id_huesped=e.id_huesped LEFT JOIN factura f ON f.id_pago=p.id_pago "
        "ORDER BY p.id_pago")
    for id_hab, nombre, doc, monto, metodo, fecha, subtotal, descuento in c.fetchall():
        gestor.pagos.append({
            "id_habitacion": str(id_hab), "huesped": nombre, "doc": doc,
            "monto_base": float(subtotal) if subtotal is not None else float(monto),
            "descuento": float(descuento) if descuento is not None else 0.0,
            "monto": float(monto), "metodo": metodo,
            "fecha": fecha.strftime("%Y-%m-%d %H:%M")})

    # Huéspedes: lista negra y clientes frecuentes
    c.execute("SELECT documento, observaciones FROM huesped WHERE en_lista_negra=TRUE")
    gestor.lista_negra = {doc: (obs or "") for doc, obs in c.fetchall()}
    c.execute("SELECT documento FROM huesped WHERE es_frecuente=TRUE")
    gestor.clientes_frecuentes = {doc: 6 for (doc,) in c.fetchall()}

    # Personal de limpieza
    c.execute("SELECT nombre, asignadas_hoy FROM personal_limpieza")
    empleados = dict(c.fetchall())
    if empleados:
        gestor.empleados_limpieza = empleados

    # Auditoría
    gestor.auditoria = []
    c.execute(
        "SELECT a.fecha_hora, u.nombre, a.accion, a.entidad, a.id_entidad, a.detalle "
        "FROM auditoria a JOIN usuario u ON u.id_usuario=a.id_usuario ORDER BY a.id_log")
    for fecha, usuario, accion, entidad, id_entidad, detalle in c.fetchall():
        gestor.auditoria.append({
            "fecha": fecha.strftime("%Y-%m-%d %H:%M"), "usuario": usuario, "accion": accion,
            "id_habitacion": str(id_entidad) if entidad == "habitacion" else None,
            "detalle": detalle or ""})

    # Auxiliares
    c.execute("SELECT mensaje FROM notificaciones ORDER BY id")
    gestor.notificaciones = [r[0] for r in c.fetchall()]
    c.execute("SELECT id_habitacion FROM habitaciones_noshow")
    gestor.habitaciones_noshow = [r[0] for r in c.fetchall()]
    c.execute("SELECT abierto, recepcionista, hora_apertura, hora_cierre, checkins, checkouts "
              "FROM turno WHERE id=1")
    fila = c.fetchone()
    if fila:
        ab, rec, ha, hc, ci, co = fila
        gestor.turno_actual["abierto"] = bool(ab)
        gestor.turno_actual["recepcionista"] = rec
        gestor.turno_actual["hora_apertura"] = ha
        gestor.turno_actual["hora_cierre"] = hc
        gestor.turno_actual["checkins_realizados"] = ci or 0
        gestor.turno_actual["checkouts_realizados"] = co or 0
    c.execute("SELECT recepcionista, hora_apertura, hora_cierre, checkins, checkouts "
              "FROM historial_turnos ORDER BY id")
    gestor.turno_actual["historial_turnos"] = [
        {"abierto": False, "recepcionista": r, "hora_apertura": a, "hora_cierre": b,
         "checkins_realizados": ci or 0, "checkouts_realizados": co or 0}
        for r, a, b, ci, co in c.fetchall()]
    c.execute("SELECT valor FROM configuracion WHERE clave=%s", ("descuento_cliente_frecuente",))
    fila = c.fetchone()
    if fila:
        gestor.descuento_cliente_frecuente = float(fila[0])
    c.close()
    conn.close()


def obtener_secreto_sesion():
    """Clave de sesión compartida por todas las instancias: se crea una sola vez en la base."""
    conn = _conectar()
    c = conn.cursor()
    c.execute("INSERT IGNORE INTO configuracion (clave,valor) VALUES (%s,%s)",
              ("session_secret", secrets.token_hex(32)))
    conn.commit()
    c.execute("SELECT valor FROM configuracion WHERE clave=%s", ("session_secret",))
    valor = c.fetchone()[0]
    c.close()
    conn.close()
    return valor
