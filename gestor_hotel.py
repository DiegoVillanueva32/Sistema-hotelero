import datetime
from habitacion import Habitacion


class GestorHotel:
    """Maneja la lógica de los requerimientos funcionales y sus operaciones."""

    def __init__(self):
        self.habitaciones = {}
        self.empleados_limpieza = {"Empleado 1": 0, "Empleado 2": 0, "Empleado 3": 0}
        self.motivos_mantenimiento = {}

        self.fechas_salida = {}
        self.lista_negra = {}
        self.clientes_frecuentes = {}
        self.turno_actual = {
            "abierto": False, "recepcionista": None,
            "hora_apertura": None, "hora_cierre": None,
            "checkins_realizados": 0, "checkouts_realizados": 0,
            "historial_turnos": []
        }
        self.notificaciones = []
        self.habitaciones_noshow = []

        # 🔥 NUEVO RF-30 / RF-44
        self.historial_reservas = []   # lista de dicts
        self.pagos = []                # lista de dicts
        self.auditoria = []
        self.descuento_cliente_frecuente = 10.0

        self._inicializar_habitaciones()

    # ============================================================
    # Inicialización
    # ============================================================
    def _inicializar_habitaciones(self):
        for piso in range(1, 6):
            for num in range(1, 11):
                id_hab = f"{piso}{num:02d}"
                if num == 9:
                    tipo, precio = "Doble", 150000.0
                elif num == 10:
                    tipo, precio = "Familiar", 200000.0
                else:
                    tipo, precio = "Normal", 100000.0
                self.habitaciones[id_hab] = Habitacion(id_hab, piso, tipo, precio)

    # ============================================================
    # Utilidades
    # ============================================================
    def validar_entero_positivo(self, valor_input, nombre_campo):
        if not isinstance(valor_input, str):
            return False, f"El campo '{nombre_campo}' no es válido."
        valor_clean = valor_input.strip()
        if not valor_clean.isdigit():
            return False, (f"El campo '{nombre_campo}' debe contener ÚNICAMENTE "
                           f"números enteros positivos.")
        return True, valor_clean

    def obtener_habitacion(self, id_hab):
        valido, id_clean = self.validar_entero_positivo(id_hab, "ID Habitación")
        if not valido:
            return None
        return self.habitaciones.get(id_clean)

    def consultar_matriz(self):
        return self.habitaciones

    def _usuario_actual(self):
        return self.turno_actual.get("recepcionista") or "Recepcionista sin turno"

    def _registrar_auditoria(self, accion, id_habitacion=None, detalle=""):
        self.auditoria.append({
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": self._usuario_actual(),
            "accion": accion,
            "id_habitacion": id_habitacion,
            "detalle": detalle,
        })

    def _auditar_cambio_estado(self, habitacion, estado_anterior, detalle=""):
        if estado_anterior != habitacion.estado:
            self._registrar_auditoria(
                "Cambio de estado",
                habitacion.id_habitacion,
                f"{estado_anterior} -> {habitacion.estado}. {detalle}".strip()
            )

    def obtener_auditoria(self):
        return list(self.auditoria)

    def consultar_matriz_filtrada(self, piso=None, tipo=None, estado=None):
        return self.filtro_general(piso or "Todos", tipo or "Todos", estado or "Todos")

    def _tiene_reserva_pendiente(self, habitacion, hoy=None):
        hoy = hoy or datetime.date.today()
        return (
            habitacion.estado in ("Reserva", "Disponible")
            and habitacion.fecha_entrada
            and habitacion.fecha_salida
            and habitacion.fecha_salida > hoy
            and (habitacion.huesped_nombre or habitacion.huesped_doc)
        )

    def _reserva_cubre_fecha(self, habitacion, fecha):
        return (
            habitacion.estado in ("Reserva", "Disponible")
            and habitacion.fecha_entrada
            and habitacion.fecha_salida
            and habitacion.fecha_entrada <= fecha < habitacion.fecha_salida
            and (habitacion.huesped_nombre or habitacion.huesped_doc)
        )

    def actualizar_estados_reservas(self, hoy=None):
        """Refleja si una reserva corresponde a hoy sin perder sus fechas futuras."""
        hoy = hoy or datetime.date.today()
        for habitacion in self.habitaciones.values():
            if not self._tiene_reserva_pendiente(habitacion, hoy):
                continue
            estado_anterior = habitacion.estado
            habitacion.estado = (
                "Reserva" if habitacion.fecha_entrada <= hoy < habitacion.fecha_salida
                else "Disponible")
            self._auditar_cambio_estado(habitacion, estado_anterior,
                                        "Actualización automática de reserva")

    # ============================================================
    # RF-06 / RF-07: Mantenimiento
    # ============================================================
    def poner_en_mantenimiento(self, id_hab, motivo):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        motivo_clean = motivo.strip()
        if not motivo_clean:
            return False, "Debe especificar un motivo o razón."
        estado_anterior = hab.estado
        hab.estado = "Mantenimiento"
        self.motivos_mantenimiento[id_hab] = motivo_clean
        self._auditar_cambio_estado(hab, estado_anterior, f"Mantenimiento: {motivo_clean}")
        return True, f"Habitación {id_hab} puesta en Mantenimiento.\nMotivo: '{motivo_clean}'"

    def quitar_mantenimiento(self, id_hab, autorizado_admin=False):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        if not autorizado_admin:
            return False, "Solo un administrador puede finalizar el mantenimiento."
        estado_anterior = hab.estado
        hab.liberar_habitacion("Disponible")
        self.motivos_mantenimiento.pop(id_hab, None)
        self._auditar_cambio_estado(hab, estado_anterior, "Mantenimiento finalizado")
        return True, f"Mantenimiento finalizado. Habitación {id_hab} pasa a 'Disponible'."

    # ============================================================
    # RF-11 / RF-12 / RF-13: Check-in
    # ============================================================
    def procesar_checkin(self, id_hab, nombre, doc, hora_actual, autorizado_admin=False):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."

        hoy = datetime.date.today()
        self.actualizar_estados_reservas(hoy)
        if self._tiene_reserva_pendiente(hab, hoy) and not self._reserva_cubre_fecha(hab, hoy):
            return False, f"La habitación tiene una reserva desde {hab.fecha_entrada}."

        motivo_ln = self.lista_negra.get(doc.strip())
        if motivo_ln:
            return False, (f"⚠️ CLIENTE EN LISTA NEGRA.\n"
                           f"Motivo: {motivo_ln}\nRegistro bloqueado.")

        if hora_actual < 10 and not autorizado_admin:
            return False, "Check-in permitido solo desde las 10:00 AM."

        if hab.estado not in ["Disponible", "Reserva"]:
            return False, f"No se puede hacer Check-in. Estado actual: '{hab.estado}'."

        estado_anterior = hab.estado
        hab.asignar_huesped(nombre, doc, "Ocupado")
        self._auditar_cambio_estado(hab, estado_anterior, f"Check-in de {nombre}")
        self._registrar_auditoria("Check-in", id_hab, f"Huésped: {nombre}; documento: {doc}")
        self.fechas_salida[id_hab] = datetime.datetime.now() + datetime.timedelta(days=1)

        if self.turno_actual["abierto"]:
            self.turno_actual["checkins_realizados"] += 1

        self.clientes_frecuentes[doc] = self.clientes_frecuentes.get(doc, 0) + 1

        msg_extra = " (EARLY CHECK-IN autorizado)" if hora_actual < 10 and autorizado_admin else ""
        return True, f"Check-in exitoso en habitación {hab.id_habitacion} para {nombre} (Doc: {doc}).{msg_extra}"

    # ============================================================
    # RF-14 / RF-15: Check-out
    # ============================================================
    def procesar_checkout(self, id_hab):
        hab = self.obtener_habitacion(id_hab)
        if not hab or hab.estado != "Ocupado":
            return False, "La habitación no existe o no está ocupada."

        estado_anterior = hab.estado
        # 🔥 RF-30: guardar en historial ANTES de liberar
        self._registrar_historial(
            hab, estado_final="Check-out",
            fecha_entrada=str(hab.fecha_entrada) if hab.fecha_entrada else "—",
            fecha_salida=str(datetime.date.today())
        )

        estado_limpieza = (
            "Pendiente" if self._contar_asignaciones_limpieza_hoy() >= 21
            else "En limpieza"
        )
        hab.liberar_habitacion(estado_limpieza)
        self._auditar_cambio_estado(hab, estado_anterior, "Check-out")
        self._registrar_auditoria("Check-out", id_hab, f"Estado resultante: {estado_limpieza}")
        self.fechas_salida.pop(id_hab, None)

        if self.turno_actual["abierto"]:
            self.turno_actual["checkouts_realizados"] += 1

        return True, (f"Check-out exitoso. Habitación {hab.id_habitacion} pasa a "
                  f"'{estado_limpieza}'.")

    def habitaciones_sin_checkout(self):
        return [h.id_habitacion for h in self.habitaciones.values() if h.estado == "Ocupado"]

    # ============================================================
    # RF-16: Búsqueda
    # ============================================================
    def buscar_huesped(self, criterio):
        criterio = criterio.strip().lower()
        resultados = []
        for hab in self.habitaciones.values():
            if hab.huesped_nombre or hab.huesped_doc:
                nom = (hab.huesped_nombre or "").lower()
                doc = (hab.huesped_doc or "").lower()
                if criterio in nom or criterio in doc:
                    resultados.append((hab.id_habitacion, hab.huesped_nombre,
                                       hab.huesped_doc, hab.estado))
        return resultados

    # ============================================================
    # RF-21 / RF-22: Reservas
    # ============================================================
    def _contar_reservas_por_tipo(self, tipo):
        hoy = datetime.date.today()
        return sum(1 for h in self.habitaciones.values()
                   if h.tipo == tipo and self._tiene_reserva_pendiente(h, hoy))

    def crear_reserva(self, id_hab, nombre, doc, fecha_entrada=None, fecha_salida=None):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        self.actualizar_estados_reservas()
        if hab.estado != "Disponible":
            return False, f"La habitación no está disponible (Estado: {hab.estado})."
        if self._tiene_reserva_pendiente(hab):
            return False, (f"La habitación ya tiene una reserva vigente del "
                           f"{hab.fecha_entrada} al {hab.fecha_salida}.")

        if not fecha_entrada or not fecha_salida:
            return False, "Debe especificar la fecha de entrada y de salida."

        try:
            f_entrada = datetime.datetime.strptime(fecha_entrada.strip(), "%Y-%m-%d").date()
            f_salida = datetime.datetime.strptime(fecha_salida.strip(), "%Y-%m-%d").date()
        except ValueError:
            return False, "Formato de fecha inválido. Use AAAA-MM-DD (ej: 2026-04-15)."

        hoy = datetime.date.today()
        if f_entrada < hoy:
            return False, f"La fecha de entrada ({f_entrada}) no puede ser anterior a hoy ({hoy})."
        if f_salida <= f_entrada:
            return False, "La fecha de salida debe ser POSTERIOR a la fecha de entrada."

        capacidad = {"Doble": 5, "Familiar": 5, "Normal": 40}
        reservas_actuales = self._contar_reservas_por_tipo(hab.tipo)
        if reservas_actuales >= capacidad[hab.tipo]:
            return False, (f"No hay más cupos para tipo "
                           f"{hab.tipo} (límite: {capacidad[hab.tipo]}).")

        estado_anterior = hab.estado
        hab.asignar_huesped(nombre, doc, "Reserva",
                            fecha_entrada=f_entrada, fecha_salida=f_salida)
        self._auditar_cambio_estado(hab, estado_anterior, "Reserva creada")

        noches = (f_salida - f_entrada).days
        return True, (f"Reserva creada en habitación {hab.id_habitacion}\n"
                      f"Huésped: {nombre} (Doc: {doc})\n"
                      f"Entrada: {f_entrada}\nSalida:  {f_salida}\nNoches:  {noches}")

    # ============================================================
    # RF-23 / RF-24 / RF-25: No-Show
    # ============================================================
    def procesar_no_show(self):
        liberadas = []
        hoy = datetime.date.today()
        self.actualizar_estados_reservas(hoy)
        for hab in self.habitaciones.values():
            if (hab.estado == "Reserva" and hab.fecha_entrada
                    and hab.fecha_entrada <= hoy):
                # 🔥 RF-30
                self._registrar_historial(
                    hab, estado_final="No-Show",
                    fecha_entrada=str(hab.fecha_entrada) if hab.fecha_entrada else "—",
                    fecha_salida=str(hab.fecha_salida) if hab.fecha_salida else "—"
                )
                estado_anterior = hab.estado
                hab.liberar_habitacion("Disponible")
                self._auditar_cambio_estado(hab, estado_anterior, "Liberada por No-Show")
                self._registrar_auditoria("No-Show", hab.id_habitacion)
                liberadas.append(hab.id_habitacion)

        if liberadas:
            msg_notif = (f"🔔 {len(liberadas)} habitación(es) liberada(s) por No-Show: "
                         f"{', '.join(liberadas)}")
            self.notificaciones.append(msg_notif)
            self.habitaciones_noshow = liberadas.copy()
            return f"Se liberaron {len(liberadas)} reservas No-Show: {', '.join(liberadas)}"
        return "No hay reservas pendientes de No-Show."

    def obtener_notificaciones(self):
        return list(self.notificaciones)

    def limpiar_notificaciones(self):
        self.notificaciones.clear()

    # ============================================================
    # RF-28: Cancelar Reserva
    # ============================================================
    def cancelar_reserva(self, id_hab, ahora=None):
        hab = self.obtener_habitacion(id_hab)
        if not hab or not self._tiene_reserva_pendiente(hab):
            return False, "La habitación no tiene una reserva activa."
        ahora = ahora or datetime.datetime.now()
        limite = datetime.datetime.combine(hab.fecha_entrada, datetime.time(18, 0))
        if ahora > limite:
            return False, ("La reserva solo puede cancelarse antes de la hora límite "
                           f"({limite:%Y-%m-%d %H:%M}).")
        estado_anterior = hab.estado
        # 🔥 RF-30
        self._registrar_historial(
            hab, estado_final="Cancelada",
            fecha_entrada=str(hab.fecha_entrada) if hab.fecha_entrada else "—",
            fecha_salida=str(hab.fecha_salida) if hab.fecha_salida else "—"
        )
        hab.liberar_habitacion("Disponible")
        self._auditar_cambio_estado(hab, estado_anterior, "Reserva cancelada")
        return True, f"Reserva de la habitación {id_hab} cancelada exitosamente."

    # ============================================================
    # RF-31 a RF-40: Limpieza
    # ============================================================
    def _contar_asignaciones_limpieza_hoy(self, empleado=None):
        hoy = datetime.date.today()
        return sum(
            1 for hab in self.habitaciones.values()
            if hab.empleado_limpieza
            and (empleado is None or hab.empleado_limpieza == empleado)
            and hab.hora_inicio_limpieza
            and hab.hora_inicio_limpieza.date() == hoy
        )

    def _contar_limpieza_empleado(self, empleado):
        return self._contar_asignaciones_limpieza_hoy(empleado)

    def asignar_limpieza(self, id_habitacion, empleado):
        hab = self.obtener_habitacion(id_habitacion)
        if not hab:
            return False, "La habitación no existe."
        if empleado not in self.empleados_limpieza:
            return False, "El empleado seleccionado no es válido."
        if hab.estado not in ("En limpieza", "Pendiente"):
            return False, "La habitación debe estar pendiente o en estado 'En limpieza'."
        if hab.empleado_limpieza and hab.hora_inicio_limpieza:
            return False, "La habitación ya fue asignada a limpieza hoy."
        if self._contar_asignaciones_limpieza_hoy() >= 21:
            estado_anterior = hab.estado
            hab.estado = "Pendiente"
            self._auditar_cambio_estado(hab, estado_anterior, "Cola por límite diario")
            return False, "Alerta: límite diario de 21 asignaciones alcanzado. Habitación en cola Pendiente."
        if self._contar_limpieza_empleado(empleado) >= 7:
            estado_anterior = hab.estado
            hab.estado = "Pendiente"
            self._auditar_cambio_estado(hab, estado_anterior, f"Cola por límite de {empleado}")
            return False, f"Alerta: {empleado} ya tiene 7 asignaciones hoy. Habitación en cola Pendiente."
        estado_anterior = hab.estado
        hab.estado = "En limpieza"
        hab.empleado_limpieza = empleado
        hab.hora_inicio_limpieza = datetime.datetime.now()
        hab.hora_fin_limpieza = None
        self.empleados_limpieza[empleado] = self._contar_limpieza_empleado(empleado)
        self._auditar_cambio_estado(hab, estado_anterior, f"Asignada a {empleado}")
        return True, f"Habitación {id_habitacion} en proceso de limpieza por {empleado}."

    def asignar_limpieza_automatica(self):
        for hab in self.habitaciones.values():
            if hab.estado == "En limpieza" and hab.empleado_limpieza:
                estado_anterior = hab.estado
                hab.hora_fin_limpieza = datetime.datetime.now()
                hab.estado = "Disponible"
                self._auditar_cambio_estado(
                    hab, estado_anterior, "Limpieza finalizada por auto-limpieza")

        pendientes = [h for h in self.habitaciones.values()
                      if h.estado in ("En limpieza", "Pendiente")
                      and not h.empleado_limpieza]
        self.empleados_limpieza = {
            empleado: self._contar_limpieza_empleado(empleado)
            for empleado in self.empleados_limpieza
        }
        asignadas = 0
        for hab in pendientes:
            if self._contar_asignaciones_limpieza_hoy() >= 21:
                estado_anterior = hab.estado
                hab.estado = "Pendiente"
                self._auditar_cambio_estado(hab, estado_anterior, "Cola por límite diario")
                continue
            disponibles = [empleado for empleado, cantidad in self.empleados_limpieza.items()
                           if cantidad < 7]
            if not disponibles:
                estado_anterior = hab.estado
                hab.estado = "Pendiente"
                self._auditar_cambio_estado(hab, estado_anterior, "Cola por límite de personal")
                continue
            empleado = min(disponibles, key=self.empleados_limpieza.get)
            hab.empleado_limpieza = empleado
            self.empleados_limpieza[empleado] += 1
            hab.hora_inicio_limpieza = datetime.datetime.now()
            hab.hora_fin_limpieza = None
            estado_anterior = hab.estado
            hab.estado = "En limpieza"
            self._auditar_cambio_estado(hab, estado_anterior,
                                        f"Asignación automática a {empleado}")
            asignadas += 1
        return asignadas

    def finalizar_limpieza(self, id_habitacion):
        hab = self.obtener_habitacion(id_habitacion)
        if not hab:
            return False, "La habitación no existe."
        if hab.estado != "En limpieza":
            return False, f"La habitación {id_habitacion} no está en proceso de limpieza."
        # 🔥 RF-38
        if not hab.hora_inicio_limpieza:
            hab.hora_inicio_limpieza = datetime.datetime.now()
        estado_anterior = hab.estado
        hab.hora_fin_limpieza = datetime.datetime.now()
        hab.estado = "Disponible"
        self._auditar_cambio_estado(hab, estado_anterior, "Limpieza finalizada")
        return True, f"La habitación {id_habitacion} ha finalizado su limpieza y ahora está DISPONIBLE."

    # ============================================================
    # RF-08 / RF-09: Reasignación
    # ============================================================
    def reasignar_habitacion(self, id_origen, id_destino):
        hab_origen = self.obtener_habitacion(id_origen)
        hab_destino = self.obtener_habitacion(id_destino)
        if not hab_origen or not hab_destino:
            return False, "IDs de habitación no válidos."
        if hab_origen.estado != "Ocupado":
            return False, "La habitación de origen debe estar 'Ocupada'."
        if hab_destino.estado != "Disponible":
            return False, "La habitación de destino debe estar 'Disponible'."
        if hab_origen.tipo != hab_destino.tipo:
            return False, f"Deben ser de la misma categoría ({hab_origen.tipo} vs {hab_destino.tipo})."

        estado_destino_anterior = hab_destino.estado
        hab_destino.asignar_huesped(
            hab_origen.huesped_nombre, hab_origen.huesped_doc, "Ocupado",
            fecha_entrada=hab_origen.fecha_entrada,
            fecha_salida=hab_origen.fecha_salida
        )
        estado_limpieza = (
            "Pendiente" if self._contar_asignaciones_limpieza_hoy() >= 21
            else "En limpieza"
        )
        hab_origen.liberar_habitacion(estado_limpieza)
        self._auditar_cambio_estado(hab_destino, estado_destino_anterior,
                        f"Huésped reasignado desde {id_origen}")
        self._auditar_cambio_estado(hab_origen, "Ocupado", "Huésped reasignado")

        if id_origen in self.fechas_salida:
            self.fechas_salida[id_destino] = self.fechas_salida.pop(id_origen)

        return True, (f"Huésped reasignado de {id_origen} a {id_destino}. "
                  f"Origen pasa a '{estado_limpieza}'.")

    # ============================================================
    # RF-42 / RF-43
    # ============================================================
    def actualizar_tarifa(self, tipo, nuevo_precio):
        if tipo not in ["Doble", "Familiar", "Normal"]:
            return False, "Tipo de habitación no válido."
        try:
            precio_num = float(nuevo_precio)
        except (ValueError, TypeError):
            return False, "Precio inválido."
        if precio_num <= 0:
            return False, "El precio debe ser mayor a 0."
        for hab in self.habitaciones.values():
            if hab.tipo == tipo:
                hab.precio = precio_num
        return True, f"Tarifa de {tipo} actualizada a ${precio_num:,.2f}"

    def calcular_costo_estadia(self, id_hab, noches):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        if noches <= 0:
            return False, "El número de noches debe ser mayor a 0."
        total = hab.precio * noches
        return True, (f"Habitación {hab.id_habitacion} ({hab.tipo})\n"
                      f"Tarifa por noche: ${hab.precio:,.2f}\n"
                      f"Noches: {noches}\n"
                      f"TOTAL A PAGAR: ${total:,.2f}")

    def configurar_descuento_frecuente(self, porcentaje):
        try:
            porcentaje = float(porcentaje)
        except (TypeError, ValueError):
            return False, "El porcentaje debe ser numérico."
        if not 0 <= porcentaje <= 100:
            return False, "El porcentaje debe estar entre 0 y 100."
        self.descuento_cliente_frecuente = porcentaje
        self._registrar_auditoria(
            "Configuración de descuento frecuente",
            detalle=f"Porcentaje: {porcentaje:g}%"
        )
        return True, f"Descuento para clientes frecuentes actualizado a {porcentaje:g}%."

    def calcular_descuento_frecuente(self, doc, monto):
        try:
            monto = float(monto)
        except (TypeError, ValueError):
            return 0.0
        if self.clientes_frecuentes.get(str(doc).strip(), 0) < 2:
            return 0.0
        return round(monto * self.descuento_cliente_frecuente / 100, 2)

    def reporte_ocupacion_diaria(self, fecha=None):
        fecha = fecha or datetime.date.today()
        if isinstance(fecha, str):
            try:
                fecha = datetime.date.fromisoformat(fecha)
            except ValueError:
                raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from None
        self.actualizar_estados_reservas(fecha)
        pisos = {}
        tipos = {}
        ocupadas = 0
        for habitacion in self.habitaciones.values():
            ocupada = habitacion.estado == "Ocupado"
            ocupadas += int(ocupada)
            piso = pisos.setdefault(habitacion.piso, {"ocupadas": 0, "total": 0})
            piso["total"] += 1
            piso["ocupadas"] += int(ocupada)
            tipo = tipos.setdefault(habitacion.tipo, {"ocupadas": 0, "total": 0})
            tipo["total"] += 1
            tipo["ocupadas"] += int(ocupada)
        total = len(self.habitaciones)
        return {
            "fecha": fecha.isoformat(),
            "ocupadas": ocupadas,
            "total": total,
            "porcentaje": (ocupadas / total * 100) if total else 0.0,
            "pisos": {
                piso: {**datos, "porcentaje": datos["ocupadas"] / datos["total"] * 100}
                for piso, datos in sorted(pisos.items())
            },
            "tipos": {
                tipo: {**datos, "porcentaje": datos["ocupadas"] / datos["total"] * 100}
                for tipo, datos in sorted(tipos.items())
            },
        }

    def reporte_ingresos(self, fecha_inicio, fecha_fin):
        try:
            inicio = (fecha_inicio if isinstance(fecha_inicio, datetime.date)
                      else datetime.date.fromisoformat(str(fecha_inicio)))
            fin = (fecha_fin if isinstance(fecha_fin, datetime.date)
                   else datetime.date.fromisoformat(str(fecha_fin)))
        except ValueError:
            raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from None
        if fin < inicio:
            raise ValueError("La fecha final no puede ser anterior a la inicial.")
        pagos = []
        for pago in self.pagos:
            fecha_pago = datetime.datetime.fromisoformat(pago["fecha"]).date()
            if inicio <= fecha_pago <= fin:
                pagos.append(dict(pago))
        por_metodo = {}
        for pago in pagos:
            por_metodo[pago["metodo"]] = por_metodo.get(pago["metodo"], 0.0) + pago["monto"]
        return {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "total": sum(pago["monto"] for pago in pagos),
            "por_metodo": por_metodo,
            "pagos": pagos,
        }

    # ============================================================
    # RF-46: Dashboard
    # ============================================================
    def obtener_resumen_indicadores(self):
        self.actualizar_estados_reservas()
        conteo = {"Disponible": 0, "Ocupado": 0, "Reserva": 0,
              "En limpieza": 0, "Pendiente": 0, "Mantenimiento": 0}
        for hab in self.habitaciones.values():
            if hab.estado in conteo:
                conteo[hab.estado] += 1
        return conteo

    def filtro_general(self, piso="Todos", tipo="Todos", estado="Todos"):
        resultado = []
        for hab in self.habitaciones.values():
            if piso != "Todos" and str(hab.piso) != str(piso):
                continue
            if tipo != "Todos" and hab.tipo != tipo:
                continue
            if estado != "Todos" and hab.estado != estado:
                continue
            resultado.append(hab)
        return resultado

    # ============================================================
    # RF-17: Extender Estancia
    # ============================================================
    def extender_estancia(self, id_hab, noches_extra):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        if hab.estado != "Ocupado":
            return False, f"La habitación {id_hab} no está ocupada (Estado: {hab.estado})."
        if noches_extra <= 0:
            return False, "Las noches adicionales deben ser mayores a 0."

        reservas_conflicto = [h.id_habitacion for h in self.habitaciones.values()
                              if h.id_habitacion == id_hab and h.estado == "Reserva"]
        if reservas_conflicto:
            return False, ("Existen reservas posteriores en esta habitación. "
                           "No se puede extender la estancia.")

        fecha_actual = self.fechas_salida.get(id_hab, datetime.datetime.now())
        nueva_fecha = fecha_actual + datetime.timedelta(days=noches_extra)
        self.fechas_salida[id_hab] = nueva_fecha

        return True, (f"✅ Estancia extendida para {hab.huesped_nombre}.\n\n"
                      f"Habitación: {id_hab}\n"
                      f"Noches adicionales: {noches_extra}\n"
                      f"Nueva fecha de salida: {nueva_fecha.strftime('%Y-%m-%d')}")

    # ============================================================
    # RF-18: Lista Negra / Clientes Frecuentes
    # ============================================================
    def marcar_lista_negra(self, doc, motivo):
        doc_clean = doc.strip()
        if not doc_clean or not doc_clean.isdigit():
            return False, "Documento inválido (solo números)."
        motivo_clean = motivo.strip()
        if not motivo_clean:
            return False, "Debe especificar un motivo."
        self.lista_negra[doc_clean] = motivo_clean
        return True, f"Documento {doc_clean} marcado en LISTA NEGRA.\nMotivo: {motivo_clean}"

    def quitar_lista_negra(self, doc):
        doc_clean = doc.strip()
        if doc_clean in self.lista_negra:
            motivo = self.lista_negra.pop(doc_clean)
            return True, f"Documento {doc_clean} removido de lista negra.\n(Motivo anterior: {motivo})"
        return False, f"El documento {doc_clean} no está en la lista negra."

    def consultar_antecedente(self, doc):
        doc_clean = doc.strip()
        esta_ln = doc_clean in self.lista_negra
        motivo = self.lista_negra.get(doc_clean, "")
        visitas = self.clientes_frecuentes.get(doc_clean, 0)
        return esta_ln, motivo, visitas

    def obtener_lista_negra(self):
        return dict(self.lista_negra)

    def obtener_clientes_frecuentes(self, minimo_visitas=2):
        return {doc: v for doc, v in self.clientes_frecuentes.items()
                if v >= minimo_visitas}

    def marcar_cliente_frecuente(self, doc, visitas=3):
        doc_clean = doc.strip()
        if not doc_clean or not doc_clean.isdigit():
            return False, "Documento inválido (solo números)."
        if visitas < 2:
            return False, "Un cliente frecuente debe tener al menos 2 visitas."
        self.clientes_frecuentes[doc_clean] = visitas
        return True, f"Documento {doc_clean} marcado como CLIENTE FRECUENTE ({visitas} visitas)."

    # ============================================================
    # RF-19: Turno
    # ============================================================
    def abrir_turno(self, nombre_recepcionista):
        if self.turno_actual["abierto"]:
            return False, (f"Ya hay un turno ABIERTO por "
                           f"{self.turno_actual['recepcionista']}.")
        nombre = nombre_recepcionista.strip()
        if not nombre:
            return False, "Debe ingresar el nombre del recepcionista."
        self.turno_actual["abierto"] = True
        self.turno_actual["recepcionista"] = nombre
        self.turno_actual["hora_apertura"] = datetime.datetime.now()
        self.turno_actual["checkins_realizados"] = 0
        self.turno_actual["checkouts_realizados"] = 0
        self.turno_actual["hora_cierre"] = None
        return True, (f"✅ Turno ABIERTO por {nombre} a las "
                      f"{self.turno_actual['hora_apertura'].strftime('%H:%M:%S')}.")

    def cerrar_turno(self):
        if not self.turno_actual["abierto"]:
            return False, "No hay un turno abierto para cerrar."
        arqueo = self.generar_arqueo()
        self.turno_actual["hora_cierre"] = datetime.datetime.now()
        self.turno_actual["historial_turnos"].append(dict(self.turno_actual))
        nombre = self.turno_actual["recepcionista"]
        self.turno_actual["abierto"] = False
        return True, f"Turno CERRADO por {nombre}.\n\n{arqueo}"

    # ============================================================
    # RF-20: Arqueo
    # ============================================================
    def generar_arqueo(self):
        t = self.turno_actual
        if not t["abierto"]:
            return "⚠️ No hay un turno activo en este momento."
        apertura = (t["hora_apertura"].strftime("%Y-%m-%d %H:%M:%S")
                    if t["hora_apertura"] else "N/A")
        total = t["checkins_realizados"] + t["checkouts_realizados"]
        return (
            "═══════════════════════════════════════\n"
            "         ARQUEO DE TURNO\n"
            "═══════════════════════════════════════\n"
            f"Recepcionista:     {t['recepcionista']}\n"
            f"Hora de apertura:  {apertura}\n"
            "───────────────────────────────────────\n"
            f"Check-ins realizados:  {t['checkins_realizados']}\n"
            f"Check-outs realizados: {t['checkouts_realizados']}\n"
            f"Total transacciones:   {total}\n"
            "═══════════════════════════════════════"
        )

    def obtener_historial_turnos(self):
        return list(self.turno_actual["historial_turnos"])

    # ============================================================
    # RF-25: Venta Presencial No-Show
    # ============================================================
    def asignacion_presencial_noshow(self, id_hab, nombre, doc):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        if id_hab not in self.habitaciones_noshow:
            return False, ("Esta habitación no fue liberada recientemente por No-Show. "
                           "Ejecute primero el proceso de No-Show.")
        if hab.estado != "Disponible":
            return False, f"La habitación no está disponible (Estado: {hab.estado})."

        nombre = nombre.strip()
        doc = doc.strip()
        if not nombre:
            return False, "Debe ingresar el nombre del cliente presencial."
        if not doc or not doc.isdigit():
            return False, "Debe ingresar el documento (solo números)."

        motivo_ln = self.lista_negra.get(doc)
        if motivo_ln:
            return False, (f"⚠️ CLIENTE EN LISTA NEGRA.\n"
                           f"Motivo: {motivo_ln}\nRegistro bloqueado.")

        estado_anterior = hab.estado
        hab.asignar_huesped(nombre, doc, "Ocupado")
        self._auditar_cambio_estado(hab, estado_anterior, f"Venta No-Show a {nombre}")
        self._registrar_auditoria(
            "Check-in presencial No-Show", id_hab,
            f"Huésped: {nombre}; documento: {doc}")
        self.fechas_salida[id_hab] = datetime.datetime.now() + datetime.timedelta(days=1)

        if self.turno_actual["abierto"]:
            self.turno_actual["checkins_realizados"] += 1
        self.clientes_frecuentes[doc] = self.clientes_frecuentes.get(doc, 0) + 1

        self.habitaciones_noshow.remove(id_hab)
        return True, (f"✅ VENTA PRESENCIAL EXITOSA.\n"
                      f"Habitación {id_hab} asignada a {nombre} (Doc: {doc}).")

    def obtener_habitaciones_noshow(self):
        return list(self.habitaciones_noshow)

    # ============================================================
    # RF-26: Comprobante de Reserva
    # ============================================================
    def generar_comprobante_reserva(self, id_hab):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        self.actualizar_estados_reservas()
        if not self._tiene_reserva_pendiente(hab):
            return False, f"La habitación no tiene reserva activa (Estado: {hab.estado})."

        ahora = datetime.datetime.now()

        if hab.fecha_entrada and hab.fecha_salida:
            f_entrada_str = hab.fecha_entrada.strftime("%Y-%m-%d")
            f_salida_str = hab.fecha_salida.strftime("%Y-%m-%d")
            noches = (hab.fecha_salida - hab.fecha_entrada).days
            total = hab.precio * noches
        else:
            f_entrada_str = "—"
            f_salida_str = "—"
            noches = 0
            total = 0.0

        if hab.fecha_entrada:
            limite = datetime.datetime.combine(hab.fecha_entrada, datetime.time(18, 0))
        else:
            limite = ahora + datetime.timedelta(hours=6)

        comprobante = (
            "═════════════════════════════════════════\n"
            "        COMPROBANTE DE RESERVA\n"
            "        SISTEMA HOTELERO UCC\n"
            "═════════════════════════════════════════\n"
            f"Fecha de emisión: {ahora.strftime('%Y-%m-%d %H:%M')}\n"
            f"N° de Reserva:    RES-{id_hab}-{ahora.strftime('%H%M%S')}\n"
            "─────────────────────────────────────────\n"
            f"Huésped:          {hab.huesped_nombre}\n"
            f"Documento:        {hab.huesped_doc}\n"
            f"Habitación:       {hab.id_habitacion}   (Piso {hab.piso})\n"
            f"Tipo:             {hab.tipo}\n"
            f"Tarifa por noche: ${hab.precio:,.0f}\n"
            "─────────────────────────────────────────\n"
            f"Fecha de entrada: {f_entrada_str}\n"
            f"Fecha de salida:  {f_salida_str}\n"
            f"Noches:           {noches}\n"
            f"TOTAL ESTIMADO:   ${total:,.0f}\n"
            "─────────────────────────────────────────\n"
            f"⏰ Fecha límite de llegada: {limite.strftime('%Y-%m-%d %H:%M')}\n"
            "─────────────────────────────────────────\n"
            "CONDICIONES DEL HOSPEDAJE:\n"
            " • Presentarse antes de la hora límite.\n"
            " • Si no llega, se aplicará No-Show.\n"
            " • Presentar documento original al Check-in.\n"
            " • Check-in permitido desde las 10:00 AM.\n"
            " • Tarifa exclusiva por hospedaje.\n"
            "═════════════════════════════════════════"
        )
        return True, comprobante

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-27: Proyección de disponibilidad (30 / 60 / 90 días)
    # ══════════════════════════════════════════════════════════════
    def proyectar_disponibilidad(self, dias=30):
        """
        Devuelve una lista de tuplas (fecha, {tipo: disponibles}) para los
        próximos `dias` días, calculando las reservas activas.
        """
        hoy = datetime.date.today()
        totales = {"Doble": 5, "Familiar": 5, "Normal": 40}
        proyeccion = []
        for i in range(dias):
            dia = hoy + datetime.timedelta(days=i)
            ocupados = {"Doble": 0, "Familiar": 0, "Normal": 0}
            for h in self.habitaciones.values():
                if self._reserva_cubre_fecha(h, dia):
                    ocupados[h.tipo] += 1
                elif h.estado == "Ocupado":
                    # habitación ocupada hoy cuenta para el día actual
                    if i == 0:
                        ocupados[h.tipo] += 1
            disponibles = {t: totales[t] - ocupados[t] for t in totales}
            proyeccion.append((dia, disponibles))
        return proyeccion

    def obtener_reservas_en_fecha(self, fecha):
        """Devuelve las habitaciones con reserva activa para una fecha."""
        return [
            habitacion for habitacion in self.habitaciones.values()
            if self._reserva_cubre_fecha(habitacion, fecha)
        ]

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-29: Modificar fechas de una reserva
    # ══════════════════════════════════════════════════════════════
    def modificar_fechas_reserva(self, id_hab, nueva_entrada, nueva_salida):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        self.actualizar_estados_reservas()
        if not self._tiene_reserva_pendiente(hab):
            return False, f"La habitación no tiene reserva activa (Estado: {hab.estado})."

        try:
            f_entrada = datetime.datetime.strptime(nueva_entrada.strip(), "%Y-%m-%d").date()
            f_salida = datetime.datetime.strptime(nueva_salida.strip(), "%Y-%m-%d").date()
        except ValueError:
            return False, "Formato de fecha inválido. Use AAAA-MM-DD."

        hoy = datetime.date.today()
        if f_entrada < hoy:
            return False, "La nueva fecha de entrada no puede ser anterior a hoy."
        if f_salida <= f_entrada:
            return False, "La nueva fecha de salida debe ser POSTERIOR a la de entrada."

        estado_anterior = hab.estado
        hab.fecha_entrada = f_entrada
        hab.fecha_salida = f_salida
        hab.estado = "Reserva" if f_entrada <= hoy < f_salida else "Disponible"
        self._auditar_cambio_estado(hab, estado_anterior, "Fechas de reserva modificadas")
        noches = (f_salida - f_entrada).days
        return True, (f"✅ Fechas actualizadas para la habitación {id_hab}.\n"
                      f"Nueva entrada: {f_entrada}\n"
                      f"Nueva salida:  {f_salida}\n"
                      f"Noches: {noches}")

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-30: Histórico de reservas
    # ══════════════════════════════════════════════════════════════
    def _registrar_historial(self, hab, estado_final, fecha_entrada, fecha_salida):
        self.historial_reservas.append({
            "id_habitacion": hab.id_habitacion,
            "huesped_nombre": hab.huesped_nombre or "—",
            "huesped_doc": hab.huesped_doc or "—",
            "tipo": hab.tipo,
            "precio": hab.precio,
            "fecha_entrada": str(fecha_entrada),
            "fecha_salida": str(fecha_salida),
            "estado_final": estado_final,
            "fecha_registro": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def obtener_historial_reservas(self, filtro_doc=None):
        if filtro_doc:
            filtro = filtro_doc.strip().lower()
            return [r for r in self.historial_reservas
                    if filtro in (r["huesped_doc"] or "").lower()
                    or filtro in (r["huesped_nombre"] or "").lower()]
        return list(self.historial_reservas)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-38 / RF-39: Tiempos y hoja de trabajo de limpieza
    # ══════════════════════════════════════════════════════════════
    def hoja_trabajo_limpieza(self):
        """
        Devuelve un dict {empleado: [lista de habitaciones asignadas hoy]}
        incluyendo las que están 'En limpieza' y las finalizadas en el turno.
        """
        resultado = {"Empleado 1": [], "Empleado 2": [], "Empleado 3": []}
        for h in self.habitaciones.values():
            if h.empleado_limpieza in resultado:
                resultado[h.empleado_limpieza].append({
                    "id": h.id_habitacion,
                    "estado": h.estado,
                    "inicio": (h.hora_inicio_limpieza.strftime("%H:%M:%S")
                               if h.hora_inicio_limpieza else "—"),
                    "fin": (h.hora_fin_limpieza.strftime("%H:%M:%S")
                            if h.hora_fin_limpieza else "—"),
                })
        return resultado

    def reporte_tiempos_limpieza(self):
        """RF-38: lista de habitaciones con hora inicio/fin de limpieza."""
        filas = []
        for h in self.habitaciones.values():
            if h.hora_inicio_limpieza:
                filas.append({
                    "id": h.id_habitacion,
                    "empleado": h.empleado_limpieza or "Sin asignar",
                    "inicio": h.hora_inicio_limpieza.strftime("%Y-%m-%d %H:%M:%S"),
                    "fin": (h.hora_fin_limpieza.strftime("%Y-%m-%d %H:%M:%S")
                            if h.hora_fin_limpieza else "En curso"),
                })
        return filas

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-44: Registro de cobro y método de pago
    # ══════════════════════════════════════════════════════════════
    def registrar_pago(self, id_hab, monto, metodo):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        if metodo not in ["Efectivo", "Tarjeta", "Transferencia"]:
            return False, "Método de pago inválido."
        try:
            monto_num = float(monto)
        except (ValueError, TypeError):
            return False, "Monto inválido (debe ser numérico)."
        if monto_num <= 0:
            return False, "El monto debe ser mayor a 0."

        descuento = self.calcular_descuento_frecuente(hab.huesped_doc, monto_num)
        total = round(monto_num - descuento, 2)
        pago = {
            "id_habitacion": hab.id_habitacion,
            "huesped": hab.huesped_nombre or "—",
            "doc": hab.huesped_doc or "—",
            "monto_base": monto_num,
            "descuento": descuento,
            "monto": total,
            "metodo": metodo,
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.pagos.append(pago)
        self._registrar_auditoria(
            "Pago", hab.id_habitacion,
            f"Huésped: {pago['huesped']}; base: {monto_num:.2f}; "
            f"descuento: {descuento:.2f}; total: {total:.2f}; método: {metodo}"
        )
        return True, (f"✅ Pago registrado correctamente.\n\n"
                      f"Habitación: {hab.id_habitacion}\n"
                      f"Huésped:    {pago['huesped']}\n"
                      f"Subtotal:   ${monto_num:,.0f}\n"
                      f"Descuento:  ${descuento:,.0f}\n"
                      f"Total:      ${total:,.0f}\n"
                      f"Método:     {metodo}\n"
                      f"Fecha:      {pago['fecha']}")

    def obtener_pagos(self):
        return list(self.pagos)

    def buscar_ultimo_pago(self, id_hab):
        for p in reversed(self.pagos):
            if p["id_habitacion"] == id_hab:
                return p
        return None

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-45: Comprobante de pago
    # ══════════════════════════════════════════════════════════════
    def generar_comprobante_pago(self, id_hab):
        hab = self.obtener_habitacion(id_hab)
        if not hab:
            return False, "Habitación no encontrada o ID inválido."
        pago = self.buscar_ultimo_pago(id_hab)
        if not pago:
            return False, f"No hay pagos registrados para la habitación {id_hab}."

        comprobante = (
            "═════════════════════════════════════════\n"
            "        COMPROBANTE DE PAGO\n"
            "        SISTEMA HOTELERO UCC\n"
            "═════════════════════════════════════════\n"
            f"N° Recibo:   PAG-{id_hab}-{pago['fecha'].replace(':','').replace(' ','')[-6:]}\n"
            f"Fecha:       {pago['fecha']}\n"
            "─────────────────────────────────────────\n"
            f"Huésped:     {pago['huesped']}\n"
            f"Documento:   {pago['doc']}\n"
            f"Habitación:  {hab.id_habitacion}   (Piso {hab.piso})\n"
            f"Tipo:        {hab.tipo}\n"
            "─────────────────────────────────────────\n"
            f"Método de pago:  {pago['metodo']}\n"
            f"Subtotal:        ${pago.get('monto_base', pago['monto']):,.0f}\n"
            f"Descuento:       ${pago.get('descuento', 0):,.0f}\n"
            f"MONTO PAGADO:    ${pago['monto']:,.0f}\n"
            "═════════════════════════════════════════\n"
            "   Gracias por su preferencia.\n"
            "   Este recibo ampara únicamente el\n"
            "   cobro de la estancia.\n"
            "═════════════════════════════════════════"
        )
        return True, comprobante