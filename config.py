import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(
            f"[CONFIG] Variable d'environnement manquante : '{name}'. "
            f"Vérifiez votre fichier .env."
        )
    return value


class Config:
    APP_NAME   = 'SMarketing'
    SECRET_KEY = _require_env('SECRET_KEY')

    DEFAULT_RESET_PASSWORD = os.environ.get('DEFAULT_RESET_PASSWORD', 'Reset.123!')

    # ── Groq AI ───────────────────────────────────────────────────────────────
    GROQ_API_KEY  = os.environ.get('GROQ_API_KEY', '')
    GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
    GROQ_MODEL    = 'llama-3.3-70b-versatile'

    # ── Email ─────────────────────────────────────────────────────────────────
    MAIL_SERVER         = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT           = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS        = True
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')

    # ── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # ── Base de données — Aiven MySQL ou local ────────────────────────────────
    # Supporte les deux conventions de nommage (.env Aiven: DB_* ou local: MYSQL_*)
    _db_user     = os.environ.get('DB_USER',     os.environ.get('MYSQL_USER',     'root'))
    _db_password = os.environ.get('DB_PASSWORD', os.environ.get('MYSQL_PASSWORD', ''))
    _db_host     = os.environ.get('DB_HOST',     os.environ.get('MYSQL_HOST',     'localhost'))
    _db_port     = os.environ.get('DB_PORT',     os.environ.get('MYSQL_PORT',     '3306'))
    _db_name     = os.environ.get('DB_NAME',     os.environ.get('MYSQL_DB',       'marketing_automation'))

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        f"mysql+pymysql://{_db_user}:{_db_password}@{_db_host}:{_db_port}/{_db_name}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Pool — adapté Aiven free tier ─────────────────────────────────────────
    # IMPORTANT : PyMySQL sur Windows n'accepte PAS 'ssl_mode' (c'est MySQL Connector).
    # Aiven nécessite SSL mais sans certificat local — on désactive la vérification.
    _is_aiven = bool(os.environ.get('DB_HOST') or os.environ.get('DATABASE_URL'))

    _ssl_args = {'ssl': {'check_hostname': False, 'verify_mode': 0}} if _is_aiven else {}

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle':  280,
        'pool_pre_ping': True,
        'pool_size':     2,
        'max_overflow':  3,
        'pool_timeout':  30,
        'connect_args': {
            'connect_timeout': 20,
            'read_timeout':    30,
            'write_timeout':   30,
            'charset':         'utf8mb4',
            'use_unicode':     True,
            **_ssl_args,
        },
    }

    # ── Session ───────────────────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE      = False
    SESSION_COOKIE_HTTPONLY    = True
    SESSION_COOKIE_SAMESITE    = 'Lax'

    # ── Sécurité login ────────────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS     = 5
    LOGIN_COOLDOWN_MINUTES = 15