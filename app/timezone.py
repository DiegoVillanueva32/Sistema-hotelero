import datetime
import os
from zoneinfo import ZoneInfo


TZ_HOTEL = ZoneInfo(os.getenv("HOTEL_TIMEZONE", "America/Bogota"))


def hora_local():
    return datetime.datetime.now(TZ_HOTEL).replace(tzinfo=None)


def fecha_local():
    return hora_local().date()
