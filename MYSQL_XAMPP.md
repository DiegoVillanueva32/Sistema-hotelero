# MySQL con XAMPP

La aplicación se conecta al MySQL/MariaDB local de XAMPP. phpMyAdmin es la interfaz para administrar esa base; no es un servicio de Google.

## Preparación

1. Abre XAMPP Control Panel e inicia **MySQL**. Inicia también **Apache** para abrir phpMyAdmin.
2. Abre `http://localhost/phpmyadmin` y confirma que phpMyAdmin carga.
3. En la carpeta del proyecto, crea la configuración local desde PowerShell:

   ```powershell
   Copy-Item database.ini.example database.ini
   ```

4. Si cambiaste la contraseña de MySQL en XAMPP, actualiza `password` en `database.ini`. El ejemplo usa el usuario `root` sin contraseña, que es el valor típico de una instalación local nueva; no uses esa configuración en un servidor público.
5. Instala las dependencias en el mismo Python con el que ejecutas la aplicación:

   ```powershell
   python -m pip install -r requirements.txt
   ```

## Iniciar la aplicación

La primera ejecución crea la base `sistema_hotelero` y sus tablas en MySQL. Si las tablas están vacías, la aplicación inicia con sus 50 habitaciones predeterminadas.

```powershell
python main.py
```

## Ver y editar datos

Con XAMPP activo, visita `http://localhost/phpmyadmin` y abre la base `sistema_hotelero`. Puedes consultar y editar sus tablas desde ahí.

Cierra la aplicación antes de modificar o eliminar filas en phpMyAdmin. La app mantiene una copia del estado en memoria y ejecuta guardados automáticos; si sigue abierta, puede volver a escribir los datos que tenía cargados. Al abrirla otra vez, cargará los cambios de MySQL.

No elimines habitaciones de la tabla `habitaciones`: el sistema espera conservar las 50 habitaciones. Para limpiar pruebas, es más seguro borrar filas de `historial_reservas`, `pagos` o `notificaciones`, según corresponda.
