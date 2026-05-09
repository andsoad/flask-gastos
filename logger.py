"""
Sistema de logs para Gastos Pareja.
- app_errors.log  → excepciones y errores de BD
- app_activity.log → acciones de usuarios (crear/editar/eliminar)
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Directorio de logs — un nivel arriba de la app para que no sea público
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _make_logger(name: str, filename: str, level=logging.INFO) -> logging.Logger:
    _ensure_log_dir()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # ya inicializado
    logger.setLevel(level)
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8',
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    return logger


def get_error_logger() -> logging.Logger:
    return _make_logger('gastos.errors', 'app_errors.log', logging.ERROR)


def get_activity_logger() -> logging.Logger:
    return _make_logger('gastos.activity', 'app_activity.log', logging.INFO)


# ── Funciones de conveniencia ──────────────────────────────────────────────────

def log_error(message: str, exc: Exception = None):
    logger = get_error_logger()
    if exc:
        logger.exception(f"{message} | {type(exc).__name__}: {exc}")
    else:
        logger.error(message)


def log_activity(user_id: int, username: str, action: str, detail: str = ''):
    logger = get_activity_logger()
    msg = f"user_id={user_id} | username={username} | action={action}"
    if detail:
        msg += f" | {detail}"
    logger.info(msg)
