"""Testes das funções puras do Mateu Coffee (mc_core).

Rodar:  pytest -q
Não dependem de Streamlit, DB nem rede.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mc_core


# ── Auth ────────────────────────────────────────────────────────────────
def test_hash_e_verify_bcrypt_roundtrip():
    h = mc_core.hash_senha("café-forte-123")
    assert h.startswith("$2")
    assert mc_core.verify_senha("café-forte-123", h) is True
    assert mc_core.verify_senha("senha-errada", h) is False


def test_verify_senha_legado_sha256():
    import hashlib
    salt = "abc"
    senha = "minhasenha"
    h = f"{salt}${hashlib.sha256(f'{salt}{senha}'.encode()).hexdigest()}"
    assert mc_core.verify_senha(senha, h) is True
    assert mc_core.verify_senha("outra", h) is False


def test_verify_senha_vazia_ou_invalida():
    assert mc_core.verify_senha("x", "") is False
    assert mc_core.verify_senha("x", "formato-invalido") is False


# ── Helpers de café ──────────────────────────────────────────────────────
def test_stars():
    assert mc_core.stars(0) == "☆☆☆☆☆"
    assert mc_core.stars(3) == "★★★☆☆"
    assert mc_core.stars(5) == "★★★★★"
    assert mc_core.stars(9) == "★★★★★"   # clamp
    assert mc_core.stars(None) == "☆☆☆☆☆"


def test_brew_ratio():
    assert mc_core.brew_ratio(18, 36) == "1:2.0"
    assert mc_core.brew_ratio(15, 250) == "1:16.7"
    assert mc_core.brew_ratio(0, 36) == "—"
    assert mc_core.brew_ratio(18, 0) == "—"
    assert mc_core.brew_ratio(None, "x") == "—"


def test_freshness_window():
    assert mc_core.freshness_window(2)[0] == "descanso"
    assert mc_core.freshness_window(10)[0] == "ideal"
    assert mc_core.freshness_window(30)[0] == "bom"
    assert mc_core.freshness_window(60)[0] == "decaindo"
    assert mc_core.freshness_window(-1) is None
    assert mc_core.freshness_window("nao-numero") is None


def test_valida_email():
    assert mc_core.valida_email("a@b.com") is True
    assert mc_core.valida_email("  a@b.com  ") is True
    assert mc_core.valida_email("sem-arroba") is False
    assert mc_core.valida_email("") is False


def test_parse_stages():
    passos = [
        "Enxágue o filtro e descarte a água.",          # sem marcador → ignorado
        "T = 0 s: Despeje 50 g em movimento circular.",  # segundos
        "T = 0:45: Comece o pour principal, até 100 g.",
        "T = 1:15: Despeje até 200 g em 10 s.",
        "T ≈ 3:30: drawdown completo.",                  # '≈' também vale
    ]
    st = mc_core.parse_stages(passos)
    assert [s["t"] for s in st] == [0, 45, 75, 210]     # ordenado, sem os 2 sem tempo
    assert st[0]["label"].startswith("Despeje 50 g")
    assert st[3]["label"] == "drawdown completo"
    assert mc_core.parse_stages([]) == []
    assert mc_core.parse_stages(None) == []


def test_logger_singleton():
    a = mc_core.get_logger("mateu")
    antes = len(a.handlers)
    b = mc_core.get_logger("mateu")
    assert a is b
    # Não duplica handlers. Conta a diferença em vez do total: o pytest
    # anexa os handlers dele ao mesmo logger, então o total nunca é 1 sob
    # captura de log — era isso que deixava o CI vermelho de forma crônica.
    assert len(b.handlers) == antes
