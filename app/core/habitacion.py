class Habitacion:
    """Representa el objeto individual de cada habitación."""

    def __init__(self, id_habitacion: str, piso: int, tipo: str, precio: float):
        self.id_habitacion = id_habitacion
        self.piso = piso
        self.tipo = tipo
        self.precio = precio
        self.estado = "Disponible"

        self.huesped_nombre = None
        self.huesped_doc = None
        self.empleado_limpieza = None

        # ===== RESERVA (RF-21 / RF-26 / RF-29) =====
        self.fecha_entrada = None    # datetime.date
        self.fecha_salida = None     # datetime.date
        # ===========================================

        # NUEVO RF-38: tiempos de limpieza
        self.hora_inicio_limpieza = None   # datetime.datetime
        self.hora_fin_limpieza = None      # datetime.datetime

    def asignar_huesped(self, nombre, doc, estado, fecha_entrada=None, fecha_salida=None):
        self.huesped_nombre = nombre
        self.huesped_doc = doc
        self.estado = estado
        if fecha_entrada is not None:
            self.fecha_entrada = fecha_entrada
        if fecha_salida is not None:
            self.fecha_salida = fecha_salida

    def liberar_habitacion(self, nuevo_estado="En limpieza"):
        self.huesped_nombre = None
        self.huesped_doc = None
        self.estado = nuevo_estado
        self.fecha_entrada = None
        self.fecha_salida = None
        self.empleado_limpieza = None
        self.hora_inicio_limpieza = None
        self.hora_fin_limpieza = None