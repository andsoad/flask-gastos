from flask_login import UserMixin
from extensions import mysql, login_manager


class Usuario(UserMixin):
    def __init__(self, id, nombre, username, rol, persona, activo):
        self.id       = id
        self.nombre   = nombre
        self.username = username
        self.rol      = rol
        self.persona  = persona
        self.activo   = activo

    def is_admin(self):
        return self.rol == 'admin'

    @staticmethod
    def get_by_id(user_id):
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, nombre, username, rol, persona, activo FROM usuarios WHERE id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        cur.close()
        if row:
            return Usuario(**row)
        return None

    @staticmethod
    def get_by_username(username):
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, nombre, username, password_hash, rol, persona, activo FROM usuarios WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        cur.close()
        return row


@login_manager.user_loader
def load_user(user_id):
    return Usuario.get_by_id(int(user_id))
