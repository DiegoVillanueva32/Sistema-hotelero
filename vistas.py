import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import datetime

from gestor_hotel import GestorHotel
from persistencia import guardar_estado
from reportes import exportar_reporte



class VistaPrincipal(tk.Tk):

    def __init__(self, gestor: GestorHotel):
        super().__init__()
        self.gestor = gestor
        self.title("Sistema Recepción Hotel")
        # Maximizar la ventana sin cubrir la barra de tareas (Windows)
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)

        self.minsize(1000, 650)
        self.configure(bg="#f4f6f9")

        self.filtro_piso = tk.StringVar(value="Todos")
        self.filtro_tipo = tk.StringVar(value="Todos")
        self.filtro_estado = tk.StringVar(value="Todos")

        # Header
        header = tk.Frame(self, bg="#dbeafe", height=40)
        header.pack(fill="x", side="top")
        tk.Label(header, text="🏨 Sistema Gestión Hotelera - Recepción",
                 font=("Helvetica", 12, "bold"), bg="#dbeafe",
                 fg="#1e3a8a").pack(side="left", padx=15, pady=8)

        # Panel indicadores
        self.panel_indicadores = tk.Frame(self, bg="#e2e8f0")
        self.panel_indicadores.pack(fill="x", padx=10, pady=5)
        self.lbl_indicadores = tk.Label(self.panel_indicadores, text="",
                                        font=("Helvetica", 9, "bold"),
                                        bg="#e2e8f0", fg="#334155")
        self.lbl_indicadores.pack(pady=4)

        main_panel = tk.Frame(self, bg="#f4f6f9")
        main_panel.pack(fill="both", expand=True, padx=10, pady=10)

        # ==========================================================
        # 🔥 NUEVO: Panel de Secciones (7 botones grandes)
        # ==========================================================
        contenedor_secciones = tk.LabelFrame(
            main_panel, text=" Secciones ",
            bg="#ffffff", font=("Helvetica", 11, "bold"))
        contenedor_secciones.pack(side="left", fill="y", padx=10, pady=5)

        SECCIONES = [
            ("Habitaciones", "#dbeafe", [
                ("Ver Matriz Completa",              self.reiniciar_filtros),
                ("Mantenimiento",                    self.req_mantenimiento),
                ("Reasignar Habitación",             self.req_reasignar),
                ("Filtro: Dobles",                   lambda: self._filtrar_por_tipo("Doble")),
                ("Filtro: Familiares",               lambda: self._filtrar_por_tipo("Familiar")),
                ("Filtro: Normales",                 lambda: self._filtrar_por_tipo("Normal")),
            ]),
            ("Recepción", "#dcfce7", [
                ("Check-in",                         self.req_checkin),
                ("Check-out",                        self.req_checkout),
                ("Alerta Check-out 12PM",            self.req_alerta_checkout),
                ("Búsqueda Huéspedes",               self.req_buscar_huesped),
                ("Extender Estancia",                self.req_extender_estancia),
            ]),
            ("Reservas", "#fef3c7", [
                ("Crear Reserva",                    self.req_reserva),
                ("Cancelar Reserva",                 self.req_cancelar_reserva),
                ("Comprobante Reserva",              self.req_comprobante_reserva),
                ("Liberar No-Show",                  self.req_noshow),
                ("Venta Presencial No-Show",         self.req_venta_presencial),
                ("Calendario Disponibilidad",        self.req_calendario),
                ("Modificar Fechas Reserva",         self.req_modificar_fechas),
                ("Histórico de Reservas",            self.req_historico),
            ]),
            ("Limpieza", "#a5f3fc", [
                ("Asignar Limpieza",                self.req_limpieza),
                ("Auto-Limpieza",                   self.req_asignacion_automatica_limpieza),
                ("Hoja de Trabajo",                 self.req_hoja_trabajo),
                ("Reporte Tiempos",                 self.req_reporte_tiempos),
            ]),
            ("Facturación", "#bbf7d0", [
                ("Configurar Tarifas",              self.req_configurar_tarifas),
                ("Descuento Cliente Frecuente",     self.req_configurar_descuento),
                ("Cálculo de Estancia",             self.req_calcular_estancia),
                ("Registrar Pago",                  self.req_registrar_pago),
                ("Comprobante de Pago",             self.req_comprobante_pago),
                ("Reporte de Ingresos",              self.req_reporte_ingresos),
            ]),
            ("Clientes", "#fce7f3", [
                ("Lista Negra / Frecuentes",         self.req_lista_negra),
                ("Notificaciones",                   self.req_notificaciones),
            ]),
            ("Administración", "#e9d5ff", [
                ("Turno Recepcionista",              self.req_turno),
                ("Arqueo de Turno",                  self.req_arqueo),
                ("Reporte de Ocupación",             self.req_reporte_ocupacion),
                ("Auditoría de Transacciones",       self.req_auditoria),
                ("Guardar cambios en la base de datos", self.guardar_manualmente),
            ]),
        ]

        for titulo, color, acciones in SECCIONES:
            tk.Button(contenedor_secciones, text=titulo,
                      width=24, height=2,
                      font=("Helvetica", 10, "bold"),
                      bg=color, relief="solid", bd=1, anchor="w", padx=12,
                      command=lambda t=titulo, c=color, a=acciones:
                          self._abrir_seccion(t, c, a)
                      ).pack(pady=5, padx=10, fill="x")

        # ==========================================================
        # Panel matriz
        # ==========================================================
        self.panel_matriz = tk.LabelFrame(
            main_panel,
            text=" Matriz General por Tipo y Estado ",
            bg="#ffffff", font=("Helvetica", 10, "bold"))
        self.panel_matriz.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        self.actualizar_matriz()
        self.after(5000, self._actualizar_indicadores_vivos)

        # Auto-guardado cada 15 s
        self.after(15000, self._auto_guardar)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_aplicacion)

    # ============================================================
    # Secciones (ventanas emergentes con botones internos)
    # ============================================================
    def _abrir_seccion(self, titulo, color, acciones):
        win = tk.Toplevel(self)
        win.title(titulo)
        win.configure(bg="#f4f6f9")
        win.geometry("560x440")
        win.transient(self)

        tk.Label(win, text=titulo, font=("Helvetica", 13, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(14, 10))

        frame = tk.Frame(win, bg="#f4f6f9")
        frame.pack(padx=15, pady=5, fill="both", expand=True)

        for i, (texto, cmd) in enumerate(acciones):
            fila, col = divmod(i, 2)
            tk.Button(frame, text=texto, width=28, height=2,
                      bg=color, activebackground="#ffffff",
                      font=("Helvetica", 9, "bold"),
                      relief="solid", bd=1, wraplength=200,
                      command=cmd).grid(row=fila, column=col,
                                        padx=6, pady=6, sticky="nsew")
        for c in range(2):
            frame.columnconfigure(c, weight=1)

        tk.Button(win, text="Cerrar", command=win.destroy,
                  bg="#e2e8f0", width=14).pack(pady=12)

    # ============================================================
    # Persistencia
    # ============================================================
    def _persistir(self, avisar_error=False):
        try:
            guardar_estado(self.gestor)
            return True
        except Exception as e:
            print(f"[Persistencia] Error al guardar ({type(e).__name__}): {e}")
            if avisar_error:
                messagebox.showerror("Error de persistencia", str(e))
            return False

    def guardar_manualmente(self):
        if self._persistir(avisar_error=True):
            messagebox.showinfo("Persistencia", "Todos los cambios se guardaron correctamente.")

    def _cerrar_aplicacion(self):
        if self._persistir(avisar_error=True):
            self.destroy()
        elif messagebox.askyesno(
                "Cerrar sin guardar", "No se pudieron guardar los cambios. ¿Cerrar de todos modos?"):
            self.destroy()

    def _auto_guardar(self):
        self._persistir()
        self.after(15000, self._auto_guardar)

    # ============================================================
    # Helpers
    # ============================================================
    def enlazar_navegacion_enter(self, lista_entries, boton_final):
        for i in range(len(lista_entries)):
            entry = lista_entries[i]
            if i < len(lista_entries) - 1:
                siguiente = lista_entries[i + 1]
                entry.bind("<Return>", lambda e, nxt=siguiente: nxt.focus_set())
            else:
                entry.bind("<Return>", lambda e: boton_final.invoke())

    def reiniciar_filtros(self):
        self.filtro_piso.set("Todos")
        self.filtro_tipo.set("Todos")
        self.filtro_estado.set("Todos")
        self.actualizar_matriz()
        self.lbl_indicadores.config(
            text="✅ Filtros reiniciados. Mostrando todas las 50 habitaciones.")
        self.after(2000, self._restaurar_indicadores)

    def _restaurar_indicadores(self):
        ind = self.gestor.obtener_resumen_indicadores()
        self.lbl_indicadores.config(
            text=(f"📊 Estado General: Disponibles: {ind['Disponible']} | "
                  f"Ocupadas: {ind['Ocupado']} | Reservas: {ind['Reserva']} | "
                  f"En Limpieza: {ind['En limpieza']} | Pendientes: {ind['Pendiente']} | "
                  f"Mantenimiento: {ind['Mantenimiento']}"))

    def _actualizar_indicadores_vivos(self):
        if not self.winfo_exists():
            return
        self._restaurar_indicadores()
        self.after(5000, self._actualizar_indicadores_vivos)

    def _filtrar_por_tipo(self, tipo):
        if self.filtro_tipo.get() == tipo:
            self.filtro_tipo.set("Todos")
        else:
            self.filtro_tipo.set(tipo)
        self.filtro_piso.set("Todos")
        self.filtro_estado.set("Todos")
        self.actualizar_matriz()

    # ============================================================
    # Matriz
    # ============================================================
    def actualizar_matriz(self):
        for widget in self.panel_matriz.winfo_children():
            widget.destroy()

        colores_estado = {
            "Disponible": "#86efac", "Ocupado": "#fca5a5",
            "Reserva": "#fef08a", "En limpieza": "#a5f3fc",
            "Pendiente": "#fdba74", "Mantenimiento": "#93c5fd"
        }
        tipo_tag = {"Doble": "DOBLE", "Familiar": "FAM", "Normal": "NORM"}

        frame_filtros = tk.Frame(self.panel_matriz, bg="#ffffff")
        frame_filtros.grid(row=0, column=0, columnspan=11, pady=6, sticky="ew")

        tk.Label(frame_filtros, text="Filtro Piso:", bg="#ffffff").pack(side="left", padx=2)
        ttk.Combobox(frame_filtros, textvariable=self.filtro_piso,
                     values=["Todos"] + [str(i) for i in range(1, 6)],
                     width=6, state="readonly").pack(side="left", padx=2)
        tk.Label(frame_filtros, text="Tipo:", bg="#ffffff").pack(side="left", padx=2)
        ttk.Combobox(frame_filtros, textvariable=self.filtro_tipo,
                     values=["Todos", "Doble", "Familiar", "Normal"],
                     width=10, state="readonly").pack(side="left", padx=2)
        tk.Label(frame_filtros, text="Estado:", bg="#ffffff").pack(side="left", padx=2)
        ttk.Combobox(frame_filtros, textvariable=self.filtro_estado,
                     values=["Todos", "Disponible", "Ocupado", "Reserva",
                             "En limpieza", "Pendiente", "Mantenimiento"],
                     width=12, state="readonly").pack(side="left", padx=2)

        tk.Button(frame_filtros, text="Aplicar", command=self.actualizar_matriz,
                  bg="#dbeafe").pack(side="left", padx=5)
        tk.Button(frame_filtros, text="🔄 Limpiar filtros",
                  command=self.reiniciar_filtros, bg="#f1f5f9").pack(side="left", padx=2)

        ind = self.gestor.obtener_resumen_indicadores()
        self.lbl_indicadores.config(
            text=(f"📊 Estado General: Disponibles: {ind['Disponible']} | "
                  f"Ocupadas: {ind['Ocupado']} | Reservas: {ind['Reserva']} | "
                  f"En Limpieza: {ind['En limpieza']} | Pendientes: {ind['Pendiente']} | "
                  f"Mantenimiento: {ind['Mantenimiento']}"))

        f_piso = self.filtro_piso.get()
        f_tipo = self.filtro_tipo.get()
        f_estado = self.filtro_estado.get()

        self.panel_matriz.grid_columnconfigure(0, minsize=55)
        for columna in range(1, 11):
            self.panel_matriz.grid_columnconfigure(
                columna, weight=1, uniform="habitaciones")

        for piso in range(5, 0, -1):
            tk.Label(self.panel_matriz, text=f"Piso {piso}", bg="#ffffff",
                     font=("Helvetica", 9, "bold")).grid(row=6 - piso, column=0,
                                                          padx=5, pady=3)
            for num in range(1, 11):
                id_hab = f"{piso}{num:02d}"
                hab = self.gestor.obtener_habitacion(id_hab)
                if not hab:
                    continue
                if f_piso != "Todos" and str(hab.piso) != f_piso:
                    continue
                if f_tipo != "Todos" and hab.tipo != f_tipo:
                    continue
                if f_estado != "Todos" and hab.estado != f_estado:
                    continue

                color = colores_estado.get(hab.estado, "#ffffff")
                tag = tipo_tag.get(hab.tipo, hab.tipo)
                texto_casilla = f"[{tag}]\n{id_hab}\n{hab.estado[:4]}"
                motivo = self.gestor.motivos_mantenimiento.get(id_hab, "N/A")

                fechas_txt = ""
                if hab.fecha_entrada and hab.fecha_salida:
                    noches = (hab.fecha_salida - hab.fecha_entrada).days
                    fechas_txt = (f"\nEntrada: {hab.fecha_entrada}\n"
                                  f"Salida:  {hab.fecha_salida}\n"
                                  f"Noches:  {noches}")

                btn = tk.Button(
                    self.panel_matriz, text=texto_casilla, bg=color,
                    font=("Helvetica", 10, "bold"),
                    relief="solid", bd=1,
                    command=lambda h=hab, m=motivo, fechas_detalle=fechas_txt:
                        messagebox.showinfo(
                            "Detalle de habitación",
                            (f"Habitación: {h.id_habitacion}\nTipo: {h.tipo}\n"
                             f"Precio/Noche: ${h.precio:,.0f}\nEstado: {h.estado}\n"
                             f"Motivo Mantenimiento: {m}\n"
                             f"Encargado Limpieza: {h.empleado_limpieza or 'N/A'}\n"
                             f"Huésped: {h.huesped_nombre or 'Ninguno'}\n"
                             f"Doc: {h.huesped_doc or 'N/A'}{fechas_detalle}")))
                btn.grid(row=6 - piso, column=num, padx=2, pady=2, sticky="ew")

    # ══════════════════════════════════════════════════════════════
    # RF-06 / RF-07: Mantenimiento
    # ══════════════════════════════════════════════════════════════
    def req_mantenimiento(self):
        win = tk.Toplevel(self)
        win.title("Mantenimiento")
        tk.Label(win, text="ID Habitación (Número entero):").pack(pady=5)
        ent_id = tk.Entry(win); ent_id.pack(pady=5); ent_id.focus_set()

        def procesar_id():
            v_hab, id_clean = self.gestor.validar_entero_positivo(ent_id.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Entrada", id_clean); return
            hab = self.gestor.obtener_habitacion(id_clean)
            if not hab:
                messagebox.showerror("Error", "La habitación no existe."); return

            if hab.estado == "Mantenimiento":
                motivo_actual = self.gestor.motivos_mantenimiento.get(id_clean, "No especificado")
                win.destroy()
                respuesta = messagebox.askyesno(
                    "Mantenimiento Activo",
                    f"La habitación {id_clean} está en mantenimiento por: '{motivo_actual}'.\n\n"
                    f"¿Desea finalizar el mantenimiento y volverla a 'Disponible'?")
                if respuesta:
                    clave = simpledialog.askstring(
                        "Autorización de administrador",
                        "Ingrese la clave de administrador para habilitar la habitación:",
                        show="*")
                    if clave != "admin123":
                        messagebox.showerror("Acceso denegado", "Clave incorrecta o cancelada.")
                        return
                    ok, msj = self.gestor.quitar_mantenimiento(
                        id_clean, autorizado_admin=True)
                    messagebox.showinfo("Resultado", msj)
                    self.actualizar_matriz()
            else:
                win_motivo = tk.Toplevel(win)
                win_motivo.title("Motivo de Mantenimiento")
                tk.Label(win_motivo,
                         text=f"Ingrese el motivo para la Hab. {id_clean}:").pack(pady=5, padx=10)
                ent_motivo = tk.Entry(win_motivo, width=40)
                ent_motivo.pack(pady=5, padx=10); ent_motivo.focus_set()

                def confirmar():
                    motivo_texto = ent_motivo.get().strip()
                    if not motivo_texto:
                        messagebox.showerror("Error",
                                             "Debe ingresar una razón para el mantenimiento.")
                        return
                    ok, msj = self.gestor.poner_en_mantenimiento(id_clean, motivo_texto)
                    messagebox.showinfo("Resultado", msj)
                    if ok:
                        self.actualizar_matriz()
                        win_motivo.destroy(); win.destroy()

                btn = tk.Button(win_motivo, text="Guardar Mantenimiento", command=confirmar)
                btn.pack(pady=10)
                self.enlazar_navegacion_enter([ent_motivo], btn)

        btn_proc = tk.Button(win, text="Continuar", command=procesar_id)
        btn_proc.pack(pady=10)
        self.enlazar_navegacion_enter([ent_id], btn_proc)

    # ============================================================
    # RF-11 / RF-12 / RF-13
    # ============================================================
    def req_checkin(self):
        win = tk.Toplevel(self)
        win.title("Check-in")
        tk.Label(win, text="ID Habitación (Número entero):").pack()
        e_hab = tk.Entry(win); e_hab.pack()
        tk.Label(win, text="Nombre Huésped:").pack()
        e_nom = tk.Entry(win); e_nom.pack()
        tk.Label(win, text="Documento de Identidad (Sólo números):").pack()
        e_doc = tk.Entry(win); e_doc.pack()
        tk.Label(win, text="Hora Actual (24h):").pack()
        e_hora = tk.Entry(win); e_hora.insert(0, str(datetime.datetime.now().hour)); e_hora.pack()
        e_hab.focus_set()

        def ejecutar():
            v_hab, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Validación", id_clean); return
            v_doc, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento de Identidad")
            if not v_doc:
                messagebox.showerror("Error de Validación", doc_clean); return
            nombre = e_nom.get().strip()
            if not nombre:
                messagebox.showerror("Error de Validación",
                                     "El nombre del huésped no puede estar vacío.")
                return
            try:
                hora = int(e_hora.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Ingrese una hora válida en entero."); return

            autorizado = False
            if hora < 10:
                pwd = simpledialog.askstring(
                    "Autorización requerida",
                    "Check-in antes de las 10:00 AM.\nIngrese la clave del administrador:",
                    show='*')
                if pwd == "admin123":
                    autorizado = True
                else:
                    messagebox.showerror("Denegado",
                                         "Clave incorrecta o cancelada. No se permite early check-in.")
                    return

            ok, msj = self.gestor.procesar_checkin(id_clean, nombre, doc_clean, hora, autorizado)
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz()
                win.destroy()

        btn = tk.Button(win, text="Registrar Check-in", command=ejecutar)
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([e_hab, e_nom, e_doc, e_hora], btn)

    # ============================================================
    # RF-14: Check-out
    # ============================================================
    def req_checkout(self):
        win = tk.Toplevel(self)
        win.title("Check-out")
        tk.Label(win, text="ID Habitación:").pack(pady=5)
        ent = tk.Entry(win); ent.pack(pady=5); ent.focus_set()

        def ejecutar():
            v_hab, id_clean = self.gestor.validar_entero_positivo(ent.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Entrada", id_clean); return
            ok, msj = self.gestor.procesar_checkout(id_clean)
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz()
                win.destroy()

        btn = tk.Button(win, text="Procesar Check-out", command=ejecutar)
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([ent], btn)

    # ============================================================
    # RF-15: Alerta
    # ============================================================
    def req_alerta_checkout(self):
        pendientes = self.gestor.habitaciones_sin_checkout()
        if pendientes:
            messagebox.showwarning(
                "⏰ Alerta 12:00 PM",
                "Habitaciones OCUPADAS sin Check-out procesado:\n\n• " + "\n• ".join(pendientes))
        else:
            messagebox.showinfo("Alerta Check-out",
                                "No hay habitaciones pendientes de Check-out.")

    # ============================================================
    # RF-21 / RF-22
    # ============================================================
    def req_reserva(self):
        win = tk.Toplevel(self)
        win.title("Crear Reserva")
        win.geometry("380x420")
        tk.Label(win, text="📅 Nueva Reserva",
                 font=("Helvetica", 11, "bold")).pack(pady=(12, 8))
        tk.Label(win, text="ID Habitación (entero):").pack()
        e_hab = tk.Entry(win, width=25); e_hab.pack(pady=3); e_hab.focus_set()
        tk.Label(win, text="Nombre del Cliente:").pack(pady=(8, 0))
        e_nom = tk.Entry(win, width=25); e_nom.pack(pady=3)
        tk.Label(win, text="Documento (solo números):").pack(pady=(8, 0))
        e_doc = tk.Entry(win, width=25); e_doc.pack(pady=3)

        hoy = datetime.date.today()
        manana = hoy + datetime.timedelta(days=1)
        tk.Label(win, text="Fecha de Entrada (AAAA-MM-DD):").pack(pady=(12, 0))
        e_entrada = tk.Entry(win, width=25)
        e_entrada.insert(0, hoy.strftime("%Y-%m-%d")); e_entrada.pack(pady=3)
        tk.Label(win, text="Fecha de Salida (AAAA-MM-DD):").pack(pady=(8, 0))
        e_salida = tk.Entry(win, width=25)
        e_salida.insert(0, manana.strftime("%Y-%m-%d")); e_salida.pack(pady=3)

        lbl_calculo = tk.Label(win, text="", fg="#1e3a8a",
                               font=("Helvetica", 9, "italic"))
        lbl_calculo.pack(pady=6)

        def calcular_en_vivo(*_):
            try:
                fe = datetime.datetime.strptime(e_entrada.get().strip(), "%Y-%m-%d").date()
                fs = datetime.datetime.strptime(e_salida.get().strip(), "%Y-%m-%d").date()
                if fs <= fe:
                    lbl_calculo.config(text="⚠️ La salida debe ser posterior a la entrada.",
                                       fg="#b91c1c"); return
                noches = (fs - fe).days
                hab = self.gestor.obtener_habitacion(e_hab.get().strip())
                if hab:
                    total = hab.precio * noches
                    lbl_calculo.config(text=f"🌙 {noches} noche(s) · Total estimado: ${total:,.0f}",
                                       fg="#166534")
                else:
                    lbl_calculo.config(text=f"🌙 {noches} noche(s)", fg="#1e3a8a")
            except ValueError:
                lbl_calculo.config(text="Formato esperado: AAAA-MM-DD", fg="#b91c1c")

        for w in (e_hab, e_entrada, e_salida):
            w.bind("<KeyRelease>", calcular_en_vivo)
        calcular_en_vivo()

        def ejecutar():
            v_hab, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Validación", id_clean); return
            v_doc, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento")
            if not v_doc:
                messagebox.showerror("Error de Validación", doc_clean); return
            nombre = e_nom.get().strip()
            if not nombre:
                messagebox.showerror("Error de Validación",
                                     "El nombre del cliente no puede estar vacío.")
                return
            ok, msj = self.gestor.crear_reserva(id_clean, nombre, doc_clean,
                                                fecha_entrada=e_entrada.get(),
                                                fecha_salida=e_salida.get())
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz(); win.destroy()

        btn = tk.Button(win, text="Registrar Reserva", command=ejecutar,
                        bg="#dbeafe", width=20)
        btn.pack(pady=14)
        self.enlazar_navegacion_enter([e_hab, e_nom, e_doc, e_entrada, e_salida], btn)

    # ============================================================
    # RF-23 / RF-24 / RF-25
    # ============================================================
    def req_noshow(self):
        msj = self.gestor.procesar_no_show()
        notifs = self.gestor.obtener_notificaciones()
        if notifs:
            msj += "\n\n🔔 Notificación:\n" + notifs[-1]
        messagebox.showinfo("Liberación No-Show", msj)
        self.actualizar_matriz()

    # ============================================================
    # RF-31 / RF-33
    # ============================================================
    def req_limpieza(self):
        win = tk.Toplevel(self)
        win.title("Gestión de Limpieza")
        win.geometry("320x180")
        tk.Label(win, text="ID Habitación:").pack(pady=(15, 2))
        e_hab = tk.Entry(win); e_hab.pack(pady=5); e_hab.focus_set()

        def procesar_limpieza():
            v_hab, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Entrada", id_clean); return
            hab = self.gestor.obtener_habitacion(id_clean)
            if not hab:
                messagebox.showerror("Error", "La habitación solicitada no existe."); return

            if hab.estado == "En limpieza" and hab.empleado_limpieza:
                emp_actual = hab.empleado_limpieza
                win.destroy()
                respuesta = messagebox.askyesno(
                    "Finalizar Limpieza",
                    f"La habitación {id_clean} está siendo atendida por: {emp_actual}.\n\n"
                    f"¿Desea marcar la limpieza como COMPLETADA y cambiar su estado a 'Disponible'?")
                if respuesta:
                    ok, msj = self.gestor.finalizar_limpieza(id_clean)
                    if ok:
                        messagebox.showinfo("Éxito", msj)
                        self.actualizar_matriz()
                    else:
                        messagebox.showerror("Error", msj)
            else:
                win_emp = tk.Toplevel(win)
                win_emp.title("Asignar Empleado")
                win_emp.geometry("300x180")
                tk.Label(win_emp, text=f"Habitación {id_clean}",
                         font=("Helvetica", 10, "bold")).pack(pady=(10, 2))
                tk.Label(win_emp, text="Seleccione el empleado encargado:").pack(pady=5)
                cb_emp = ttk.Combobox(win_emp,
                                      values=["Empleado 1", "Empleado 2", "Empleado 3"],
                                      state="readonly")
                cb_emp.current(0); cb_emp.pack(pady=5); cb_emp.focus_set()

                def confirmar():
                    emp_sel = cb_emp.get()
                    ok, msj = self.gestor.asignar_limpieza(id_clean, emp_sel)
                    if ok:
                        messagebox.showinfo("Asignación Exitosa",
                                            f"{msj}\n\nPara pasarla a 'Disponible', "
                                            f"presione nuevamente el botón de Limpieza al terminar.")
                        self.actualizar_matriz()
                        win_emp.destroy(); win.destroy()
                    else:
                        messagebox.showerror("Error de Asignación", msj)

                btn_asig = tk.Button(win_emp, text="Asignar y Mandar a Limpiar",
                                     command=confirmar, bg="#dbeafe")
                btn_asig.pack(pady=10)
                cb_emp.bind("<Return>", lambda e: btn_asig.invoke())

        btn_cont = tk.Button(win, text="Continuar", command=procesar_limpieza)
        btn_cont.pack(pady=10)
        self.enlazar_navegacion_enter([e_hab], btn_cont)

    # ============================================================
    # RF-34
    # ============================================================
    def req_asignacion_automatica_limpieza(self):
        antes = sum(1 for h in self.gestor.habitaciones.values()
                    if h.estado in ("En limpieza", "Pendiente"))
        if antes == 0:
            messagebox.showinfo("Auto Limpieza",
                                "No hay habitaciones pendientes de limpieza.")
            return
        finalizadas = sum(
            1 for h in self.gestor.habitaciones.values()
            if h.estado == "En limpieza" and h.empleado_limpieza
        )
        asignadas = self.gestor.asignar_limpieza_automatica()
        en_cola = sum(1 for h in self.gestor.habitaciones.values()
                      if h.estado == "Pendiente")
        detalle = "\n".join(f"• {emp}: {cant} habitación(es)"
                            for emp, cant in self.gestor.empleados_limpieza.items())
        resumen = (
            f"Limpiezas finalizadas: {finalizadas}.\n"
            f"Nuevas habitaciones asignadas: {asignadas}.\n\n"
            f"Asignaciones del día por empleado:\n{detalle}\n\n"
            f"Habitaciones en cola 'Pendiente': {en_cola}.")
        if en_cola:
            messagebox.showwarning(
                "Límite diario de limpieza alcanzado",
                f"Se alcanzó el límite de 21 habitaciones por día.\n"
                f"{en_cola} habitación(es) quedaron en cola 'Pendiente'.\n\n"
                f"{resumen}")
        else:
            messagebox.showinfo("Asignación Automática de Limpieza", resumen)
        self.actualizar_matriz()

    # ============================================================
    # RF-08
    # ============================================================
    def req_reasignar(self):
        win = tk.Toplevel(self)
        win.title("Reasignar Habitación")
        tk.Label(win, text="ID Habitación Origen:").pack()
        e_orig = tk.Entry(win); e_orig.pack()
        tk.Label(win, text="ID Habitación Destino:").pack()
        e_dest = tk.Entry(win); e_dest.pack(); e_orig.focus_set()

        def ejecutar():
            v1, id1 = self.gestor.validar_entero_positivo(e_orig.get(), "Habitación Origen")
            v2, id2 = self.gestor.validar_entero_positivo(e_dest.get(), "Habitación Destino")
            if not v1 or not v2:
                messagebox.showerror("Error", f"{id1}\n{id2}"); return
            ok, msj = self.gestor.reasignar_habitacion(id1, id2)
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz(); win.destroy()

        btn = tk.Button(win, text="Procesar Reasignación", command=ejecutar)
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([e_orig, e_dest], btn)

    # ============================================================
    # RF-16
    # ============================================================
    def req_buscar_huesped(self):
        win = tk.Toplevel(self)
        win.title("Búsqueda de Huéspedes")
        tk.Label(win, text="Buscar por Nombre o Documento:").pack(pady=5)
        e_busqueda = tk.Entry(win); e_busqueda.pack(pady=5); e_busqueda.focus_set()

        def ejecutar():
            query = e_busqueda.get().strip()
            if not query:
                messagebox.showerror("Error", "Ingrese un criterio de búsqueda."); return
            resultados = self.gestor.buscar_huesped(query)
            if not resultados:
                messagebox.showinfo("Búsqueda", "No se encontraron coincidencias."); return
            texto = "Resultados encontrados:\n\n"
            for hab, nom, doc, est in resultados:
                texto += f"• Habitación {hab}: {nom} (Doc: {doc}) - Estado: {est}\n"
            messagebox.showinfo("Resultados Búsqueda", texto)

        btn = tk.Button(win, text="Buscar", command=ejecutar)
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([e_busqueda], btn)

    # ============================================================
    # RF-28
    # ============================================================
    def req_cancelar_reserva(self):
        win = tk.Toplevel(self)
        win.title("Cancelar Reserva")
        tk.Label(win, text="ID Habitación con reserva:").pack(pady=5)
        ent = tk.Entry(win); ent.pack(pady=5); ent.focus_set()

        def ejecutar():
            v_hab, id_clean = self.gestor.validar_entero_positivo(ent.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Entrada", id_clean); return
            ok, msj = self.gestor.cancelar_reserva(id_clean)
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz(); win.destroy()

        btn = tk.Button(win, text="Cancelar Reserva", command=ejecutar)
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([ent], btn)

    # ============================================================
    # RF-42
    # ============================================================
    def req_configurar_tarifas(self):
        win = tk.Toplevel(self)
        win.title("Configurar Tarifas")
        win.geometry("340x220")
        tk.Label(win, text="Tipo de habitación:").pack(pady=(15, 2))
        cb_tipo = ttk.Combobox(win, values=["Doble", "Familiar", "Normal"],
                               state="readonly")
        cb_tipo.current(0); cb_tipo.pack(pady=5); cb_tipo.focus_set()
        tk.Label(win, text="Nuevo precio por noche:").pack(pady=(10, 2))
        e_precio = tk.Entry(win); e_precio.pack(pady=5)

        def guardar():
            try:
                precio = float(e_precio.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Ingrese un precio numérico válido."); return
            ok, msj = self.gestor.actualizar_tarifa(cb_tipo.get(), precio)
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz(); win.destroy()

        btn = tk.Button(win, text="Guardar Tarifa", command=guardar, bg="#dbeafe")
        btn.pack(pady=10)
        e_precio.bind("<Return>", lambda e: btn.invoke())

    # ============================================================
    # RF-43
    # ============================================================
    def req_calcular_estancia(self):
        win = tk.Toplevel(self)
        win.title("Cálculo de Importe")
        tk.Label(win, text="ID Habitación:").pack()
        e_hab = tk.Entry(win); e_hab.pack()
        tk.Label(win, text="Noches de Estancia:").pack()
        e_noches = tk.Entry(win); e_noches.pack(); e_hab.focus_set()

        def ejecutar():
            v_hab, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error de Entrada", id_clean); return
            try:
                noches = int(e_noches.get().strip())
                ok, msj = self.gestor.calcular_costo_estadia(id_clean, noches)
                if ok:
                    messagebox.showinfo("Cálculo de Hospedaje", msj); win.destroy()
                else:
                    messagebox.showerror("Error", msj)
            except ValueError:
                messagebox.showerror("Error", "El número de noches debe ser un entero válido.")

        btn = tk.Button(win, text="Calcular Total", command=ejecutar)
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([e_hab, e_noches], btn)

    # ============================================================
    # RF-17
    # ============================================================
    def req_extender_estancia(self):
        win = tk.Toplevel(self)
        win.title("Extender Estancia")
        win.geometry("340x200")
        tk.Label(win, text="ID Habitación:").pack(pady=(15, 2))
        e_hab = tk.Entry(win); e_hab.pack(pady=5); e_hab.focus_set()
        tk.Label(win, text="Noches adicionales:").pack(pady=(10, 2))
        e_noches = tk.Entry(win); e_noches.pack(pady=5)

        def ejecutar():
            v_hab, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_hab:
                messagebox.showerror("Error", id_clean); return
            v_n, n_clean = self.gestor.validar_entero_positivo(e_noches.get(), "Noches adicionales")
            if not v_n:
                messagebox.showerror("Error", n_clean); return
            ok, msj = self.gestor.extender_estancia(id_clean, int(n_clean))
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz(); win.destroy()

        btn = tk.Button(win, text="Extender Estancia", command=ejecutar, bg="#dbeafe")
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([e_hab, e_noches], btn)

    # ============================================================
    # RF-18
    # ============================================================
    def req_lista_negra(self):
        win = tk.Toplevel(self)
        win.title("Clientes Frecuentes y Lista Negra")
        win.geometry("700x560")
        tk.Label(win, text="🕵️ Control de Clientes Frecuentes y Lista Negra",
                 font=("Helvetica", 12, "bold")).pack(pady=(10, 8))

        frame_listas = tk.Frame(win)
        frame_listas.pack(fill="both", expand=True, padx=10, pady=5)

        frame_ln = tk.LabelFrame(frame_listas, text=" ❌ Lista Negra ",
                                 font=("Helvetica", 10, "bold"), fg="#991b1b",
                                 padx=5, pady=5)
        frame_ln.pack(side="left", fill="both", expand=True, padx=5)
        lst_ln = tk.Listbox(frame_ln, height=10, font=("Consolas", 9))
        lst_ln.pack(fill="both", expand=True)

        frame_cf = tk.LabelFrame(frame_listas, text=" ⭐ Clientes Frecuentes ",
                                 font=("Helvetica", 10, "bold"), fg="#166534",
                                 padx=5, pady=5)
        frame_cf.pack(side="right", fill="both", expand=True, padx=5)
        lst_cf = tk.Listbox(frame_cf, height=10, font=("Consolas", 9))
        lst_cf.pack(fill="both", expand=True)

        def refrescar_listas():
            lst_ln.delete(0, tk.END)
            for doc, motivo in self.gestor.obtener_lista_negra().items():
                lst_ln.insert(tk.END, f"{doc}  →  {motivo}")
            lst_cf.delete(0, tk.END)
            for doc, visitas in self.gestor.obtener_clientes_frecuentes(minimo_visitas=2).items():
                lst_cf.insert(tk.END, f"Doc {doc}  →  {visitas} visitas")

        refrescar_listas()

        frame_form = tk.LabelFrame(win, text=" Acciones ", padx=8, pady=8)
        frame_form.pack(fill="x", padx=10, pady=8)

        tk.Label(frame_form, text="Documento:").grid(row=0, column=0, sticky="w", pady=3)
        e_doc = tk.Entry(frame_form, width=20)
        e_doc.grid(row=0, column=1, pady=3, padx=5); e_doc.focus_set()
        tk.Label(frame_form, text="Motivo (Lista Negra):").grid(row=0, column=2,
                                                                 sticky="w", pady=3, padx=(15, 0))
        e_motivo = tk.Entry(frame_form, width=28)
        e_motivo.grid(row=0, column=3, pady=3, padx=5)

        def agregar_ln():
            v_doc, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento")
            if not v_doc:
                messagebox.showerror("Error", doc_clean); return
            ok, msj = self.gestor.marcar_lista_negra(doc_clean, e_motivo.get())
            messagebox.showinfo("Resultado", msj)
            if ok:
                refrescar_listas()
                e_doc.delete(0, tk.END); e_motivo.delete(0, tk.END)

        def quitar_ln():
            v_doc, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento")
            if not v_doc:
                messagebox.showerror("Error", doc_clean); return
            ok, msj = self.gestor.quitar_lista_negra(doc_clean)
            messagebox.showinfo("Resultado", msj)
            if ok:
                refrescar_listas()

        def agregar_cf():
            v_doc, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento")
            if not v_doc:
                messagebox.showerror("Error", doc_clean); return
            ok, msj = self.gestor.marcar_cliente_frecuente(doc_clean, visitas=3)
            messagebox.showinfo("Resultado", msj)
            if ok:
                refrescar_listas(); e_doc.delete(0, tk.END)

        def consultar():
            v_doc, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento")
            if not v_doc:
                messagebox.showerror("Error", doc_clean); return
            ln, motivo, visitas = self.gestor.consultar_antecedente(doc_clean)
            estado_ln = (f"❌ EN LISTA NEGRA\n   Motivo: {motivo}"
                         if ln else "✅ Sin antecedentes negros")
            estado_cf = ("⭐ CLIENTE FRECUENTE" if visitas >= 2 else "Cliente ocasional")
            messagebox.showinfo(
                "Consulta de Antecedentes",
                f"Documento: {doc_clean}\n\n{estado_ln}\n\n"
                f"Visitas registradas: {visitas}\nClasificación: {estado_cf}")

        frame_btns = tk.Frame(frame_form)
        frame_btns.grid(row=1, column=0, columnspan=4, pady=(10, 0))

        tk.Button(frame_btns, text="➕ Añadir a Lista Negra", command=agregar_ln,
                  bg="#fecaca", width=20).grid(row=0, column=0, padx=4)
        tk.Button(frame_btns, text="➖ Quitar de Lista Negra", command=quitar_ln,
                  bg="#bbf7d0", width=20).grid(row=0, column=1, padx=4)
        tk.Button(frame_btns, text="⭐ Marcar Frecuente", command=agregar_cf,
                  bg="#fef08a", width=20).grid(row=1, column=0, padx=4, pady=5)
        tk.Button(frame_btns, text="🔍 Consultar Documento", command=consultar,
                  bg="#dbeafe", width=20).grid(row=1, column=1, padx=4, pady=5)

        e_motivo.bind("<Return>", lambda e: agregar_ln())

    # ============================================================
    # RF-19
    # ============================================================
    def req_turno(self):
        win = tk.Toplevel(self)
        win.title("Turno del Recepcionista")
        win.geometry("400x300")
        tk.Label(win, text="🕐 Gestión de Turno",
                 font=("Helvetica", 11, "bold")).pack(pady=(10, 5))

        frame_estado = tk.LabelFrame(win, text=" Estado del Turno ", padx=10, pady=10)
        frame_estado.pack(fill="x", padx=10, pady=5)
        lbl_estado = tk.Label(frame_estado, text="", justify="left", font=("Consolas", 9))
        lbl_estado.pack()

        def refrescar():
            t = self.gestor.turno_actual
            if t["abierto"]:
                txt = (f"🟢 TURNO ABIERTO\n"
                       f"Recepcionista: {t['recepcionista']}\n"
                       f"Apertura: {t['hora_apertura'].strftime('%H:%M:%S')}\n"
                       f"Check-ins: {t['checkins_realizados']}  |  "
                       f"Check-outs: {t['checkouts_realizados']}")
            else:
                txt = "🔴 No hay turno abierto."
            lbl_estado.config(text=txt)

        tk.Label(win, text="Nombre del recepcionista:").pack(pady=(10, 2))
        e_nombre = tk.Entry(win, width=30); e_nombre.pack(pady=2); e_nombre.focus_set()

        def abrir():
            ok, msj = self.gestor.abrir_turno(e_nombre.get())
            messagebox.showinfo("Resultado", msj)
            if ok:
                e_nombre.delete(0, tk.END); refrescar()

        def cerrar():
            ok, msj = self.gestor.cerrar_turno()
            messagebox.showinfo("Resultado", msj)
            if ok:
                refrescar()

        frame_btn = tk.Frame(win); frame_btn.pack(pady=15)
        tk.Button(frame_btn, text="Abrir Turno", command=abrir,
                  bg="#bbf7d0", width=15).grid(row=0, column=0, padx=5)
        tk.Button(frame_btn, text="Cerrar Turno", command=cerrar,
                  bg="#fecaca", width=15).grid(row=0, column=1, padx=5)

        e_nombre.bind("<Return>", lambda e: abrir())
        refrescar()

    # ============================================================
    # RF-20
    # ============================================================
    def req_arqueo(self):
        arqueo = self.gestor.generar_arqueo()
        messagebox.showinfo("Arqueo de Turno", arqueo)

    # ============================================================
    # RF-24
    # ============================================================
    def req_notificaciones(self):
        notifs = self.gestor.obtener_notificaciones()
        if not notifs:
            messagebox.showinfo("Notificaciones", "No hay notificaciones pendientes.")
            return
        texto = "🔔 NOTIFICACIONES RECIENTES:\n\n" + "\n\n".join(notifs)
        resp = messagebox.askyesno("Notificaciones",
                                   f"{texto}\n\n¿Desea limpiar las notificaciones?")
        if resp:
            self.gestor.limpiar_notificaciones()

    # ============================================================
    # RF-25
    # ============================================================
    def req_venta_presencial(self):
        win = tk.Toplevel(self)
        win.title("Venta Presencial No-Show")
        win.geometry("400x330")
        tk.Label(win, text="⚡ Venta Inmediata por No-Show",
                 font=("Helvetica", 11, "bold")).pack(pady=(10, 5))

        frame_disp = tk.LabelFrame(win, text=" Habitaciones Liberadas ", padx=5, pady=5)
        frame_disp.pack(fill="x", padx=10, pady=5)
        lst = tk.Listbox(frame_disp, height=4); lst.pack(fill="x")
        for hid in self.gestor.obtener_habitaciones_noshow():
            lst.insert(tk.END, hid)

        if not self.gestor.obtener_habitaciones_noshow():
            tk.Label(frame_disp,
                     text="(No hay habitaciones liberadas. Ejecute primero el proceso No-Show.)",
                     fg="red").pack()

        tk.Label(win, text="ID Habitación:").pack(pady=(10, 2))
        e_hab = tk.Entry(win); e_hab.pack(); e_hab.focus_set()
        tk.Label(win, text="Nombre del cliente:").pack(pady=(8, 2))
        e_nom = tk.Entry(win); e_nom.pack()
        tk.Label(win, text="Documento:").pack(pady=(8, 2))
        e_doc = tk.Entry(win); e_doc.pack()

        def ejecutar():
            v_h, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_h:
                messagebox.showerror("Error", id_clean); return
            v_d, doc_clean = self.gestor.validar_entero_positivo(e_doc.get(), "Documento")
            if not v_d:
                messagebox.showerror("Error", doc_clean); return
            ok, msj = self.gestor.asignacion_presencial_noshow(id_clean, e_nom.get(), doc_clean)
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz(); win.destroy()

        btn = tk.Button(win, text="Asignar Inmediatamente", command=ejecutar, bg="#dbeafe")
        btn.pack(pady=12)
        self.enlazar_navegacion_enter([e_hab, e_nom, e_doc], btn)

    # ============================================================
    # RF-26
    # ============================================================
       # ============================================================
    # RF-26: Comprobante de Reserva  (método completo)
    # ============================================================
    def req_comprobante_reserva(self):
        win = tk.Toplevel(self)
        win.title("Comprobante de Reserva")
        win.geometry("420x200")

        tk.Label(win, text="🧾 Emitir Comprobante de Reserva",
                 font=("Helvetica", 11, "bold")).pack(pady=(15, 5))
        tk.Label(win, text="ID Habitación con reserva activa:").pack(pady=(10, 2))
        e_hab = tk.Entry(win); e_hab.pack(pady=5); e_hab.focus_set()

        def ejecutar():
            v_h, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_h:
                messagebox.showerror("Error", id_clean); return

            ok, msj = self.gestor.generar_comprobante_reserva(id_clean)
            if ok:
                win_c = tk.Toplevel(self)   # hija de self, no de win
                win_c.title(f"Comprobante Reserva {id_clean}")
                win_c.geometry("520x560")

                txt = tk.Text(win_c, width=60, height=28,
                              font=("Consolas", 9), wrap="none")
                txt.pack(padx=10, pady=10, fill="both", expand=True)
                txt.insert("1.0", msj)
                txt.config(state="disabled")

                tk.Button(win_c, text="Cerrar", command=win_c.destroy,
                          bg="#dbeafe").pack(pady=8)
                win.destroy()
            else:
                messagebox.showerror("Error", msj)

        btn = tk.Button(win, text="Generar Comprobante", command=ejecutar, bg="#dbeafe")
        btn.pack(pady=10)
        self.enlazar_navegacion_enter([e_hab], btn)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-27: Calendario de disponibilidad proyectada
    # ══════════════════════════════════════════════════════════════
    def req_calendario(self):
        win = tk.Toplevel(self)
        win.title("Proyección de Disponibilidad")
        win.geometry("1120x700")
        win.minsize(900, 580)
        win.configure(bg="#f4f6f9")

        tk.Label(win, text="Disponibilidad por fecha",
                 font=("Helvetica", 13, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(12, 5))

        frame_busqueda = tk.Frame(win, bg="#f4f6f9")
        frame_busqueda.pack(pady=8)
        tk.Label(frame_busqueda, text="Día a consultar (AAAA-MM-DD):",
                 bg="#f4f6f9").pack(side="left", padx=(4, 8))
        fecha_var = tk.StringVar(value=datetime.date.today().isoformat())
        entrada_fecha = tk.Entry(frame_busqueda, textvariable=fecha_var, width=14)
        entrada_fecha.pack(side="left", padx=4)

        frame_resultado = tk.Frame(win, bg="#ffffff")
        tk.Label(frame_resultado, text="",
                 font=("Helvetica", 10, "bold"), bg="#ffffff",
                 anchor="w").pack(fill="x", padx=8, pady=(6, 2))
        etiqueta_resumen = frame_resultado.winfo_children()[0]

        frame_matriz = tk.Frame(frame_resultado, bg="#ffffff")
        frame_matriz.pack(fill="both", expand=True, padx=8, pady=5)
        frame_acciones = tk.Frame(frame_resultado, bg="#ffffff")
        frame_acciones.pack(pady=(2, 8))

        def buscar_otro_dia():
            frame_resultado.pack_forget()
            frame_busqueda.pack(pady=8)
            entrada_fecha.focus_set()
            entrada_fecha.selection_range(0, tk.END)

        tk.Button(frame_acciones, text="Buscar otro día",
                  command=buscar_otro_dia, bg="#dbeafe").pack(side="left", padx=5)
        tk.Button(frame_acciones, text="Cerrar", command=win.destroy,
                  bg="#e2e8f0").pack(side="left", padx=5)

        def buscar_fecha(event=None):
            try:
                fecha = datetime.date.fromisoformat(fecha_var.get().strip())
            except ValueError:
                messagebox.showerror(
                    "Fecha no válida", "Escribe la fecha con el formato AAAA-MM-DD.",
                    parent=win)
                entrada_fecha.focus_set()
                return

            if fecha < datetime.date.today():
                messagebox.showerror(
                    "Fecha no disponible", "Consulta una fecha de hoy en adelante.",
                    parent=win)
                entrada_fecha.focus_set()
                return

            for widget in frame_matriz.winfo_children():
                widget.destroy()

            reservas = self.gestor.obtener_reservas_en_fecha(fecha)
            reservas_por_id = {habitacion.id_habitacion: habitacion
                               for habitacion in reservas}
            estados = {}
            for piso in range(5, 0, -1):
                for numero in range(1, 11):
                    id_habitacion = f"{piso}{numero:02d}"
                    habitacion = self.gestor.obtener_habitacion(id_habitacion)
                    if id_habitacion in reservas_por_id:
                        estado = "Reservada"
                    elif habitacion.estado == "Mantenimiento":
                        estado = "Mantenimiento"
                    elif (fecha == datetime.date.today()
                          and habitacion.estado == "Ocupado"):
                        estado = "Ocupada"
                    else:
                        estado = "Sin reserva"
                    estados[id_habitacion] = estado

                    color = {
                        "Reservada": "#fef08a",
                        "Mantenimiento": "#93c5fd",
                        "Ocupada": "#fca5a5",
                        "Sin reserva": "#86efac",
                    }[estado]
                    etiqueta_tipo = {"Normal": "NORM", "Doble": "DOBLE",
                                     "Familiar": "FAM"}.get(habitacion.tipo, "")
                    boton = tk.Button(
                        frame_matriz,
                        text=f"[{etiqueta_tipo}]\n{id_habitacion}\n{estado}",
                        bg=color, font=("Helvetica", 9, "bold"),
                        relief="solid", bd=1,
                        command=lambda h=habitacion, e=estado: messagebox.showinfo(
                            "Detalle de habitación",
                            (f"Habitación: {h.id_habitacion}\nTipo: {h.tipo}\n"
                             f"Estado para la fecha: {e}\n"
                             f"Huésped: {h.huesped_nombre or 'Ninguno'}\n"
                             f"Entrada: {h.fecha_entrada or 'N/A'}\n"
                             f"Salida: {h.fecha_salida or 'N/A'}"), parent=win))
                    boton.grid(row=6 - piso, column=numero, padx=2, pady=2,
                               sticky="nsew")

            frame_matriz.grid_columnconfigure(0, minsize=62)
            for columna in range(1, 11):
                frame_matriz.grid_columnconfigure(
                    columna, weight=1, uniform="habitaciones_fecha")
            for fila in range(1, 6):
                tk.Label(frame_matriz, text=f"Piso {6 - fila}",
                         bg="#ffffff", font=("Helvetica", 9, "bold")).grid(
                             row=fila, column=0, padx=4, pady=2, sticky="e")

            conteo = {estado: list(estados.values()).count(estado)
                      for estado in ("Reservada", "Ocupada", "Mantenimiento", "Sin reserva")}
            etiqueta_resumen.config(
                text=(f"{fecha.isoformat()}   |   Reservadas: {conteo['Reservada']}   "
                      f"|   Ocupadas: {conteo['Ocupada']}   "
                      f"|   Mantenimiento: {conteo['Mantenimiento']}   "
                      f"|   Sin reserva: {conteo['Sin reserva']}"))
            frame_busqueda.pack_forget()
            frame_resultado.pack(fill="both", expand=True, padx=8, pady=5)

        tk.Button(frame_busqueda, text="Buscar fecha", command=buscar_fecha,
                  bg="#dbeafe").pack(side="left", padx=5)
        entrada_fecha.bind("<Return>", buscar_fecha)
        entrada_fecha.focus_set()

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-29: Modificar fechas de una reserva
    # ══════════════════════════════════════════════════════════════
    def req_modificar_fechas(self):
        win = tk.Toplevel(self)
        win.title("Modificar Fechas de Reserva")
        win.geometry("380x300")

        tk.Label(win, text="📆 Ajustar Fechas de Reserva",
                 font=("Helvetica", 11, "bold")).pack(pady=(12, 8))

        tk.Label(win, text="ID Habitación con reserva:").pack(pady=(8, 2))
        e_hab = tk.Entry(win, width=25); e_hab.pack(pady=3); e_hab.focus_set()

        hoy = datetime.date.today()
        manana = hoy + datetime.timedelta(days=1)

        tk.Label(win, text="Nueva Fecha de Entrada (AAAA-MM-DD):").pack(pady=(8, 2))
        e_ent = tk.Entry(win, width=25)
        e_ent.insert(0, hoy.strftime("%Y-%m-%d"))
        e_ent.pack(pady=3)

        tk.Label(win, text="Nueva Fecha de Salida (AAAA-MM-DD):").pack(pady=(8, 2))
        e_sal = tk.Entry(win, width=25)
        e_sal.insert(0, manana.strftime("%Y-%m-%d"))
        e_sal.pack(pady=3)

        def ejecutar():
            v_h, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_h:
                messagebox.showerror("Error", id_clean); return
            ok, msj = self.gestor.modificar_fechas_reserva(
                id_clean, e_ent.get(), e_sal.get())
            messagebox.showinfo("Resultado", msj)
            if ok:
                self.actualizar_matriz()
                win.destroy()

        btn = tk.Button(win, text="Guardar Cambios", command=ejecutar, bg="#dbeafe")
        btn.pack(pady=14)
        self.enlazar_navegacion_enter([e_hab, e_ent, e_sal], btn)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-30: Histórico de Reservas
    # ══════════════════════════════════════════════════════════════
    def req_historico(self):
        win = tk.Toplevel(self)
        win.title("Histórico de Reservas")
        win.geometry("820x520")
        win.configure(bg="#f4f6f9")

        tk.Label(win, text="📚 Histórico de Reservas",
                 font=("Helvetica", 12, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(10, 5))

        frame_filtro = tk.Frame(win, bg="#f4f6f9")
        frame_filtro.pack(pady=5)
        tk.Label(frame_filtro, text="Filtrar por documento/nombre:",
                 bg="#f4f6f9").pack(side="left", padx=5)
        e_filtro = tk.Entry(frame_filtro, width=25); e_filtro.pack(side="left")

        frame_tabla = tk.Frame(win, bg="#ffffff")
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ["Fecha registro", "Hab.", "Huésped", "Doc",
                "Tipo", "Entrada", "Salida", "Estado final"]
        anchos = [18, 6, 20, 12, 10, 12, 12, 14]

        tree = ttk.Treeview(frame_tabla, columns=cols, show="headings", height=15)
        for c, w in zip(cols, anchos):
            tree.heading(c, text=c)
            tree.column(c, width=w * 7, anchor="w")
        tree.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        def cargar(filtro=""):
            tree.delete(*tree.get_children())
            for r in self.gestor.obtener_historial_reservas(filtro or None):
                tree.insert("", "end", values=(
                    r["fecha_registro"], r["id_habitacion"], r["huesped_nombre"],
                    r["huesped_doc"], r["tipo"], r["fecha_entrada"],
                    r["fecha_salida"], r["estado_final"]))

        cargar()

        def aplicar_filtro():
            cargar(e_filtro.get().strip())

        btn_filtro = tk.Button(frame_filtro, text="Buscar", command=aplicar_filtro,
                                bg="#dbeafe")
        btn_filtro.pack(side="left", padx=5)
        e_filtro.bind("<Return>", lambda e: aplicar_filtro())

        tk.Button(win, text="Cerrar", command=win.destroy,
                  bg="#e2e8f0", width=14).pack(pady=8)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-38: Reporte de tiempos de limpieza
    # ══════════════════════════════════════════════════════════════
    def req_reporte_tiempos(self):
        win = tk.Toplevel(self)
        win.title("Reporte de Tiempos de Limpieza")
        win.geometry("720x480")
        win.configure(bg="#f4f6f9")

        tk.Label(win, text="⏱️ Registro de Tiempos de Limpieza",
                 font=("Helvetica", 12, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(10, 5))

        frame_tabla = tk.Frame(win, bg="#ffffff")
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ["Habitación", "Empleado", "Inicio", "Fin"]
        anchos = [12, 15, 22, 22]
        tree = ttk.Treeview(frame_tabla, columns=cols, show="headings", height=15)
        for c, w in zip(cols, anchos):
            tree.heading(c, text=c)
            tree.column(c, width=w * 8, anchor="w")
        tree.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        filas = self.gestor.reporte_tiempos_limpieza()
        if not filas:
            tk.Label(win, text="(No hay registros de limpieza todavía)",
                     fg="#b91c1c", bg="#f4f6f9").pack(pady=5)
        for r in filas:
            tree.insert("", "end", values=(r["id"], r["empleado"],
                                           r["inicio"], r["fin"]))

        tk.Button(win, text="Cerrar", command=win.destroy,
                  bg="#e2e8f0", width=14).pack(pady=8)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-39: Hoja de trabajo de limpieza
    # ══════════════════════════════════════════════════════════════
    def req_hoja_trabajo(self):
        hoja = self.gestor.hoja_trabajo_limpieza()

        # Si ningún empleado tiene habitaciones asignadas hoy → avisar
        if not any(hoja.values()):
            messagebox.showinfo("Hoja de Trabajo",
                                "No hay habitaciones asignadas a personal de limpieza.")
            return

        win = tk.Toplevel(self)
        win.title("Hoja de Trabajo de Limpieza")
        win.geometry("780x560")
        win.configure(bg="#f4f6f9")

        tk.Label(win, text="🧾 Hoja de Trabajo — Personal de Limpieza",
                 font=("Helvetica", 12, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(10, 5))

        frame_global = tk.Frame(win, bg="#f4f6f9")
        frame_global.pack(fill="both", expand=True, padx=10, pady=10)

        for empleado, lista in hoja.items():
            frame_emp = tk.LabelFrame(frame_global, text=f" {empleado} ",
                                       bg="#ffffff", font=("Helvetica", 10, "bold"),
                                       padx=8, pady=6)
            frame_emp.pack(fill="x", pady=6)

            if not lista:
                tk.Label(frame_emp, text="(Sin asignaciones)",
                         bg="#ffffff", fg="#64748b").pack(anchor="w")
                continue

            cols = ["Habitación", "Estado", "Inicio", "Fin"]
            tree = ttk.Treeview(frame_emp, columns=cols, show="headings",
                                height=len(lista) + 1)
            for c in cols:
                tree.heading(c, text=c)
                tree.column(c, width=140, anchor="w")
            tree.pack(fill="x")

            for h in lista:
                tree.insert("", "end", values=(h["id"], h["estado"],
                                                h["inicio"], h["fin"]))

        tk.Button(win, text="Cerrar", command=win.destroy,
                  bg="#e2e8f0", width=14).pack(pady=8)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-44: Registrar cobro y método de pago
    # ══════════════════════════════════════════════════════════════
    def req_registrar_pago(self):
        win = tk.Toplevel(self)
        win.title("Registrar Pago")
        win.geometry("380x340")
        win.configure(bg="#f4f6f9")

        tk.Label(win, text="💵 Registro de Cobro y Método de Pago",
                 font=("Helvetica", 11, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(12, 8))

        tk.Label(win, text="ID Habitación:", bg="#f4f6f9").pack(pady=(8, 2))
        e_hab = tk.Entry(win, width=25); e_hab.pack(pady=3); e_hab.focus_set()

        tk.Label(win, text="Subtotal de hospedaje antes del descuento ($):",
             bg="#f4f6f9").pack(pady=(8, 2))
        e_monto = tk.Entry(win, width=25); e_monto.pack(pady=3)

        tk.Label(win, text="Método de pago:", bg="#f4f6f9").pack(pady=(8, 2))
        cb_metodo = ttk.Combobox(win, values=["Efectivo", "Tarjeta", "Transferencia"],
                                  state="readonly", width=22)
        cb_metodo.current(0)
        cb_metodo.pack(pady=3)

        def ejecutar():
            v_h, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_h:
                messagebox.showerror("Error", id_clean); return
            ok, msj = self.gestor.registrar_pago(id_clean, e_monto.get(), cb_metodo.get())
            messagebox.showinfo("Resultado", msj)
            if ok:
                win.destroy()

        btn = tk.Button(win, text="Registrar Pago", command=ejecutar, bg="#dbeafe")
        btn.pack(pady=14)
        self.enlazar_navegacion_enter([e_hab, e_monto], btn)

    # ══════════════════════════════════════════════════════════════
    # 🔥 RF-45: Comprobante de Pago
    # ══════════════════════════════════════════════════════════════
    def req_comprobante_pago(self):
        win = tk.Toplevel(self)
        win.title("Comprobante de Pago")
        win.geometry("400x200")
        win.configure(bg="#f4f6f9")

        tk.Label(win, text="🧾 Emitir Comprobante de Pago",
                 font=("Helvetica", 11, "bold"),
                 bg="#f4f6f9", fg="#1e3a8a").pack(pady=(15, 5))
        tk.Label(win, text="ID Habitación con pago registrado:",
                 bg="#f4f6f9").pack(pady=(10, 2))
        e_hab = tk.Entry(win, width=25); e_hab.pack(pady=5); e_hab.focus_set()

        def ejecutar():
            v_h, id_clean = self.gestor.validar_entero_positivo(e_hab.get(), "ID Habitación")
            if not v_h:
                messagebox.showerror("Error", id_clean); return

            ok, msj = self.gestor.generar_comprobante_pago(id_clean)
            if ok:
                win_c = tk.Toplevel(self)
                win_c.title(f"Comprobante Pago {id_clean}")
                win_c.geometry("520x480")

                txt = tk.Text(win_c, width=60, height=24,
                              font=("Consolas", 10), wrap="none")
                txt.pack(padx=10, pady=10, fill="both", expand=True)
                txt.insert("1.0", msj)
                txt.config(state="disabled")

                tk.Button(win_c, text="Cerrar", command=win_c.destroy,
                          bg="#dbeafe").pack(pady=8)
                win.destroy()
            else:
                messagebox.showerror("Error", msj)

        btn = tk.Button(win, text="Generar Comprobante", command=ejecutar, bg="#dbeafe")
        btn.pack(pady=14)
        self.enlazar_navegacion_enter([e_hab], btn)

    def req_configurar_descuento(self):
        win = tk.Toplevel(self)
        win.title("Tarifa preferencial frecuente")
        win.geometry("380x220")
        win.configure(bg="#f4f6f9")
        tk.Label(win, text="Descuento para clientes frecuentes",
                 font=("Helvetica", 11, "bold"), bg="#f4f6f9",
                 fg="#1e3a8a").pack(pady=(15, 8))
        tk.Label(win, text="Aplica desde 2 visitas registradas y solo al hospedaje.",
                 bg="#f4f6f9").pack(pady=4)
        tk.Label(win, text="Porcentaje de descuento:", bg="#f4f6f9").pack(pady=(8, 2))
        entrada = tk.Entry(win, width=12)
        entrada.insert(0, str(self.gestor.descuento_cliente_frecuente))
        entrada.pack()
        entrada.focus_set()

        def guardar():
            ok, mensaje = self.gestor.configurar_descuento_frecuente(entrada.get())
            if ok:
                self._persistir()
            messagebox.showinfo("Descuento frecuente", mensaje, parent=win)
            if ok:
                win.destroy()

        boton = tk.Button(win, text="Guardar porcentaje", command=guardar,
                          bg="#dbeafe")
        boton.pack(pady=12)
        entrada.bind("<Return>", lambda _event: boton.invoke())

    def _exportar_reporte(self, titulo, encabezados, filas, nombre, formato):
        extension = ".xlsx" if formato == "xlsx" else ".pdf"
        tipo = "Excel" if formato == "xlsx" else "PDF"
        ruta = filedialog.asksaveasfilename(
            parent=self, title=f"Exportar {tipo}", initialfile=f"{nombre}{extension}",
            defaultextension=extension,
            filetypes=[(f"Archivo {tipo}", f"*{extension}")])
        if not ruta:
            return
        try:
            exportar_reporte(titulo, encabezados, filas, formato, ruta)
        except Exception as error:
            messagebox.showerror("Error de exportación", str(error), parent=self)
            return
        messagebox.showinfo("Reporte exportado", f"Archivo creado:\n{ruta}", parent=self)

    def req_reporte_ocupacion(self):
        reporte = self.gestor.reporte_ocupacion_diaria()
        filas = [["General", reporte["ocupadas"], reporte["total"],
                  f"{reporte['porcentaje']:.1f}%"]]
        filas.extend([
            [f"Piso {piso}", datos["ocupadas"], datos["total"],
             f"{datos['porcentaje']:.1f}%"]
            for piso, datos in reporte["pisos"].items()
        ])
        filas.extend([
            [tipo, datos["ocupadas"], datos["total"],
             f"{datos['porcentaje']:.1f}%"]
            for tipo, datos in reporte["tipos"].items()
        ])

        win = tk.Toplevel(self)
        win.title("Reporte diario de ocupación")
        win.geometry("600x470")
        tk.Label(win, text=f"Ocupación del {reporte['fecha']}: "
                 f"{reporte['ocupadas']}/{reporte['total']} habitaciones "
                 f"({reporte['porcentaje']:.1f}%)",
                 font=("Helvetica", 11, "bold")).pack(pady=12)
        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12, pady=5)
        columnas = ("segmento", "ocupadas", "total", "porcentaje")
        tabla = ttk.Treeview(frame, columns=columnas, show="headings", height=14)
        for clave, texto, ancho in zip(
                columnas, ("Segmento", "Ocupadas", "Habitaciones", "Ocupación"),
                (220, 100, 120, 100)):
            tabla.heading(clave, text=texto)
            tabla.column(clave, width=ancho, anchor="center")
        for fila in filas:
            tabla.insert("", "end", values=fila)
        tabla.pack(fill="both", expand=True)

        tk.Button(win, text="Exportar Excel", command=lambda: self._exportar_reporte(
            f"Reporte de ocupación {reporte['fecha']}",
            ["Segmento", "Ocupadas", "Habitaciones", "Ocupación"], filas,
            f"ocupacion_{reporte['fecha']}", "xlsx")).pack(side="left", padx=(20, 5), pady=10)
        tk.Button(win, text="Exportar PDF", command=lambda: self._exportar_reporte(
            f"Reporte de ocupación {reporte['fecha']}",
            ["Segmento", "Ocupadas", "Habitaciones", "Ocupación"], filas,
            f"ocupacion_{reporte['fecha']}", "pdf")).pack(side="left", padx=5, pady=10)
        tk.Button(win, text="Cerrar", command=win.destroy).pack(
            side="right", padx=20, pady=10)

    def req_reporte_ingresos(self):
        win = tk.Toplevel(self)
        win.title("Reporte de ingresos")
        win.geometry("820x520")
        hoy = datetime.date.today().isoformat()
        marco_filtro = tk.Frame(win)
        marco_filtro.pack(fill="x", padx=10, pady=10)
        tk.Label(marco_filtro, text="Desde (AAAA-MM-DD):").pack(side="left", padx=4)
        entrada_inicio = tk.Entry(marco_filtro, width=12)
        entrada_inicio.insert(0, hoy)
        entrada_inicio.pack(side="left", padx=4)
        tk.Label(marco_filtro, text="Hasta (AAAA-MM-DD):").pack(side="left", padx=4)
        entrada_fin = tk.Entry(marco_filtro, width=12)
        entrada_fin.insert(0, hoy)
        entrada_fin.pack(side="left", padx=4)
        resumen = tk.Label(win, text="", font=("Helvetica", 10, "bold"))
        resumen.pack(pady=4)
        columnas = ("fecha", "habitacion", "huesped", "base", "descuento", "monto", "metodo")
        marco_tabla = tk.Frame(win)
        marco_tabla.pack(fill="both", expand=True, padx=10, pady=5)
        tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings")
        anchos = (145, 75, 150, 90, 90, 90, 110)
        for clave, texto, ancho in zip(
                columnas, ("Fecha", "Habitación", "Huésped", "Subtotal", "Descuento",
                           "Total", "Método"), anchos):
            tabla.heading(clave, text=texto)
            tabla.column(clave, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco_tabla, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=barra.set)
        tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        estado_reporte = {"datos": None, "filas": []}

        def generar():
            try:
                datos = self.gestor.reporte_ingresos(
                    entrada_inicio.get().strip(), entrada_fin.get().strip())
            except ValueError as error:
                messagebox.showerror("Fechas no válidas", str(error), parent=win)
                return
            tabla.delete(*tabla.get_children())
            filas = []
            for pago in datos["pagos"]:
                fila = [pago["fecha"], pago["id_habitacion"], pago["huesped"],
                        pago.get("monto_base", pago["monto"]), pago.get("descuento", 0),
                        pago["monto"], pago["metodo"]]
                filas.append(fila)
                tabla.insert("", "end", values=fila)
            estado_reporte["datos"] = datos
            estado_reporte["filas"] = filas
            resumen.config(text=(f"Total recaudado: ${datos['total']:,.2f}  |  " +
                                 "  |  ".join(
                                     f"{metodo}: ${monto:,.2f}"
                                     for metodo, monto in sorted(datos["por_metodo"].items()))))

        def exportar(formato):
            datos = estado_reporte["datos"]
            if datos is None:
                messagebox.showinfo("Reporte", "Genera primero el reporte.", parent=win)
                return
            filas = [["TOTAL", "", "", "", "", datos["total"], ""]]
            filas.extend([[f"Total {metodo}", "", "", "", "", monto, metodo]
                          for metodo, monto in sorted(datos["por_metodo"].items())])
            filas.extend(estado_reporte["filas"])
            self._exportar_reporte(
                f"Ingresos {datos['fecha_inicio']} a {datos['fecha_fin']}",
                ["Fecha", "Habitación", "Huésped", "Subtotal", "Descuento", "Total", "Método"],
                filas, f"ingresos_{datos['fecha_inicio']}_{datos['fecha_fin']}", formato)

        tk.Button(marco_filtro, text="Generar", command=generar,
                  bg="#dbeafe").pack(side="left", padx=6)
        tk.Button(win, text="Exportar Excel", command=lambda: exportar("xlsx")).pack(
            side="left", padx=(15, 5), pady=10)
        tk.Button(win, text="Exportar PDF", command=lambda: exportar("pdf")).pack(
            side="left", padx=5, pady=10)
        tk.Button(win, text="Cerrar", command=win.destroy).pack(
            side="right", padx=15, pady=10)
        generar()

    def req_auditoria(self):
        win = tk.Toplevel(self)
        win.title("Auditoría de transacciones")
        win.geometry("1000x520")
        columnas = ("fecha", "usuario", "accion", "habitacion", "detalle")
        tabla = ttk.Treeview(win, columns=columnas, show="headings")
        for clave, texto, ancho in zip(
                columnas, ("Fecha", "Usuario", "Acción", "Habitación", "Detalle"),
                (150, 180, 180, 100, 360)):
            tabla.heading(clave, text=texto)
            tabla.column(clave, width=ancho, anchor="w")
        barra = ttk.Scrollbar(win, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=barra.set)
        tabla.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        barra.pack(side="left", fill="y", pady=10)
        for evento in reversed(self.gestor.obtener_auditoria()):
            tabla.insert("", "end", values=(
                evento["fecha"], evento["usuario"], evento["accion"],
                evento["id_habitacion"] or "", evento["detalle"]))
        tk.Button(win, text="Cerrar", command=win.destroy).pack(
            side="right", padx=15, pady=10, anchor="s")