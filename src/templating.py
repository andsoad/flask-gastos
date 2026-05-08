"""
Renderizador de templates Jinja2.
Jinja2 está disponible en Cloudflare Workers Python (viene con Pyodide).
"""
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

_env = None


def get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=select_autoescape(['html']),
            autoescape=True,
        )
        # Carga templates desde el directorio templates/
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        _env.loader = FileSystemLoader(template_dir)
    return _env


def render(template_name: str, **ctx) -> str:
    return get_env().get_template(template_name).render(**ctx)
