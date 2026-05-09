import sys
import os

# Ruta del entorno virtual configurado por cPanel
INTERP = "/home/studio5/virtualenv/repositories/flask-gastos/3.13/bin/python"
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application
