from flask import current_app
from persistencia import guardar_estado


class HotelService:
    def __init__(self):
        pass

    @property
    def gestor(self):
        return current_app.extensions["gestor_hotel"]

    def persistir(self):
        guardar_estado(self.gestor)


hotel_service = HotelService()
