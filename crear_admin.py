"""
Ejecuta este script UNA VEZ para crear el primer usuario admin.
Uso: python crear_admin.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

import MySQLdb
from werkzeug.security import generate_password_hash

host     = os.environ.get('MYSQL_HOST', 'localhost')
port     = int(os.environ.get('MYSQL_PORT', 3306))
user     = os.environ.get('MYSQL_USER')
password = os.environ.get('MYSQL_PASSWORD')
db_name  = os.environ.get('MYSQL_DB', 'gastos_pareja')

nombre   = input("Nombre completo: ").strip()
username = input("Nombre de usuario: ").strip().lower()
pw       = input("Contraseña: ").strip()

pw_hash = generate_password_hash(pw)

conn = MySQLdb.connect(host=host, port=port, user=user, passwd=password, db=db_name, charset='utf8mb4')
cur  = conn.cursor()
cur.execute("""
    INSERT INTO usuarios (nombre, username, password_hash, rol, activo)
    VALUES (%s, %s, %s, 'admin', 1)
""", (nombre, username, pw_hash))
conn.commit()
cur.close()
conn.close()

print(f"\n✅ Admin '{nombre}' (@{username}) creado exitosamente.")
