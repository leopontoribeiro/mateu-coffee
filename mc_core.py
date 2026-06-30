"""mc_core.py — lógica pura e testável do Mateu Coffee (sem Streamlit/DB).

Extraído do monólito streamlit_app_final.py para:
  • modularização (auth, logging e helpers fora do arquivo de 5k linhas)
  • observabilidade (logger central configurável via MC_LOG_LEVEL)
  • testabilidade (funções puras cobertas por tests/test_mc_core.py)
"""
from __future__ import annotations

import bcrypt
import hashlib
import logging
import os
import re
import sys

# ── Observabilidade ────────────────────────────────────────────────────
def get_logger(name: str = "mateu") -> logging.Logger:
    """Logger único por processo, stdout (capturado pelos logs do Render)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(os.environ.get("MC_LOG_LEVEL", "INFO"))
        logger.propagate = False
    return logger


# ── Auth (hashing) ─────────────────────────────────────────────────────
def hash_senha(senha: str) -> str:
    """Hash bcrypt — lento por design, resistente a brute-force."""
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verify_senha(senha: str, hash_stored: str) -> bool:
    """Verifica senha. Suporta bcrypt (novo) e SHA-256 legado (migração)."""
    if not hash_stored:
        return False
    if hash_stored.startswith("$2"):
        try:
            return bcrypt.checkpw(senha.encode(), hash_stored.encode())
        except Exception:
            return False
    parts = hash_stored.split("$")  # legado "{salt}${hex}"
    if len(parts) == 2:
        salt, h = parts
        return hashlib.sha256(f"{salt}{senha}".encode()).hexdigest() == h
    return False


# ── Helpers de café (puros) ────────────────────────────────────────────
def stars(n) -> str:
    """Estrelas preenchidas/vazias para uma nota 0–5."""
    n = max(0, min(5, int(n or 0)))
    return "★" * n + "☆" * (5 - n)


def brew_ratio(dose_g, rendimento_g) -> str:
    """Ratio de extração '1:X.X' (dose:rendimento), ou '—' se inválido."""
    try:
        d, r = float(dose_g), float(rendimento_g)
    except (TypeError, ValueError):
        return "—"
    if d <= 0 or r <= 0:
        return "—"
    return f"1:{r / d:.1f}"


def freshness_window(dias) -> tuple[str, str] | None:
    """Classifica frescor da torra por dias pós-torra → (label, cor hex)."""
    try:
        d = int(dias)
    except (TypeError, ValueError):
        return None
    if d < 0:
        return None
    if d <= 4:
        return ("descanso", "#4A9EFF")
    if d <= 21:
        return ("ideal", "#3DD68C")
    if d <= 45:
        return ("bom", "#E8A33D")
    return ("decaindo", "#E85D5D")


def valida_email(email: str) -> bool:
    """Validação simples de formato de e-mail."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))
