# Gastos Pareja 💑

Aplicación Flask + MySQL para llevar el control de gastos compartidos entre dos personas.

## Características

- ✅ Gastos divididos al 50% entre dos personas
- ✅ Soporte para gastos diferidos a varios meses (sin interés)
- ✅ Pagos extra / transferencias directas
- ✅ Reporte mensual y acumulado (desde dic 2024)
- ✅ Categorías: Súper, Restaurantes, Transporte, Servicios, Entretenimiento, Salud, Viajes, Ropa, Otros
- ✅ Sistema de usuarios con roles admin / usuario
- ✅ Compatible con InMotion Hosting (Passenger WSGI)

---

## Instalación en InMotion Hosting

### 1. Subir archivos

Sube todos los archivos al directorio de tu dominio via FTP o el Administrador de Archivos de cPanel.

### 2. Crear la base de datos MySQL

En cPanel > MySQL Databases:
1. Crea una base de datos (ej. `usuario_gastos`)
2. Crea un usuario MySQL y asígnalo a la base de datos con todos los permisos
3. En phpMyAdmin, importa el archivo `schema.sql`

### 3. Configurar el archivo `.env`

Edita el archivo `.env` con tus credenciales:

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=usuario_mysql
MYSQL_PASSWORD=tu_password
MYSQL_DB=usuario_gastos
SECRET_KEY=una_clave_secreta_larga_y_aleatoria
```

### 4. Crear el entorno virtual e instalar dependencias

Conéctate via SSH:

```bash
cd ~/public_html/tu-directorio
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Nota:** Ajusta la ruta del intérprete en `passenger_wsgi.py` si usas una versión distinta de Python.

### 5. Configurar Python App en cPanel

En cPanel > Setup Python App:
- Python version: 3.11 (o la disponible)
- Application root: directorio de tu app
- Application URL: tu dominio o subdominio
- Application startup file: `passenger_wsgi.py`
- Application Entry point: `application`

### 6. Crear el primer usuario admin

```bash
source venv/bin/activate
python crear_admin.py
```

Sigue las instrucciones para crear tu cuenta de administrador.

---

## Uso

### Gastos diferidos

Un gasto de $3,000 diferido a 3 meses se registra **una sola vez** con `meses_diferidos = 3`.
La app automáticamente aplica **$1,000** a cada uno de los 3 meses consecutivos,
y divide esa cuota en **$500 por persona**.

### Pagos extra

Son transferencias directas entre las dos personas (sin asociarse a un gasto específico).
Se registran con el mes al que pertenecen y aparecen en el reporte mensual afectando el balance.

### Reporte

El reporte muestra:
- **Balance del mes seleccionado**: cuánto pagó cada quien, cuánto le toca, y quién debe qué
- **Acumulado desde dic 2024**: balance histórico total
- **Histórico mensual**: tabla con el desglose mes por mes

---

## Estructura del proyecto

```
gastos_pareja/
├── app.py               # App principal Flask
├── extensions.py        # Extensiones (MySQL, LoginManager)
├── models.py            # Modelo de Usuario
├── passenger_wsgi.py    # Entrada WSGI para InMotion
├── crear_admin.py       # Script para crear el primer admin
├── requirements.txt
├── schema.sql           # Esquema de la base de datos
├── .env                 # Credenciales (NO subir a git)
├── routes/
│   ├── auth.py
│   ├── gastos.py
│   ├── pagos_extra.py
│   ├── reportes.py
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── reporte.html
│   ├── gastos/
│   ├── pagos_extra/
│   └── admin/
└── static/
    ├── css/style.css
    └── js/main.js
```
