# Base de datos MySQL

El sistema puede usar MySQL local instalado con XAMPP o MySQL Workbench.

## Preparación

1. Inicia el servicio MySQL desde XAMPP o MySQL Workbench.
2. Confirma el puerto, normalmente `3306`.
3. En la carpeta del proyecto, crea la configuración local:

   ```powershell
   Copy-Item database.ini.example database.ini
   ```

4. Ajusta `database.ini`: host, puerto, usuario, contraseña y nombre de base. El nombre general predeterminado es `sistema_hotelero`.
5. Instala las dependencias:

   ```powershell
   python -m pip install -r requirements.txt
   ```

## Iniciar Flask

```powershell
python run.py
```

Abre `http://127.0.0.1:5000`. La primera ejecución crea la base y las tablas si MySQL está disponible; si las tablas están vacías, carga las 50 habitaciones predeterminadas.

## Variables opcionales

- `HOTEL_DB_HOST`
- `HOTEL_DB_PORT`
- `HOTEL_DB_USER`
- `HOTEL_DB_PASSWORD`
- `HOTEL_DB_NAME`
- `HOTEL_SECRET_KEY`

## MySQL Workbench

Puedes inspeccionar el esquema `sistema_hotelero` y sus tablas. No elimines filas de `habitaciones` si quieres conservar las 50 habitaciones iniciales. Para pruebas, limpia preferentemente `historial_reservas`, `pagos` o `notificaciones`.
