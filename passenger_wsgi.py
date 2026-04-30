import sys
import os

# Ajusta esta ruta al directorio de tu app en el servidor
INTERP = os.path.join(os.environ['HOME'], 'virtualenv', 'gastos_pareja', '3.11', 'bin', 'python3')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application
