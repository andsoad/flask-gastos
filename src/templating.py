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
        # En Cloudflare Workers el root es src/, templates está un nivel arriba
        import os
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        _env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html']),
        )
    return _env


def render(template_name: str, **ctx) -> str:
    return get_env().get_template(template_name).render(**ctx)
