# Configuración MySQL para la aplicación web

MySQL Workbench no reemplaza al servidor MySQL: Workbench es la interfaz gráfica que administra una instancia MySQL. Para ejecutar la aplicación debes tener activo el servicio MySQL, ya sea instalado directamente o mediante otro administrador local.

## Conexión

La configuración se lee de `database.ini`, creado desde `database.ini.example`.

```powershell
Copy-Item database.ini.example database.ini
```

Valores predeterminados:

```ini
[mysql]
host = 127.0.0.1
port = 3306
user = root
password =
database = sistema_hotelero
```

## MySQL Workbench

En Workbench puedes:

1. Crear o abrir una conexión local.
2. Confirmar que el servidor responde.
3. Administrar el esquema `sistema_hotelero` después de iniciar la aplicación Flask.
4. Consultar las tablas sin eliminar las 50 habitaciones iniciales.

La aplicación crea automáticamente el esquema, las tablas y los datos iniciales necesarios si la instancia MySQL está disponible.

## Iniciar

```powershell
python -m pip install -r requirements.txt
python run.py
```

Abre `http://127.0.0.1:5000`.
