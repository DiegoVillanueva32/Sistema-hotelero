# main.py
from gestor_hotel import GestorHotel
from persistencia import cargar_estado, guardar_estado, inicializar_bd
from vistas import VistaPrincipal

if __name__ == "__main__":
    # La base MySQL debe estar iniciada en XAMPP antes de abrir la app.
    inicializar_bd()
    gestor = GestorHotel()
    if not cargar_estado(gestor):
        guardar_estado(gestor)
    app = VistaPrincipal(gestor)
    app.mainloop()