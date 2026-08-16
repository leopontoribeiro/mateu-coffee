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


# ── Dimensionamento da extração ────────────────────────────────────────
# Duas lógicas distintas, porque a física é distinta:
#
# ESPRESSO — não escala em ml. Ristretto/normale/lungo são RATIOS sobre a
#   mesma dose. Volume maior = mais DOSES (shots), cada uma com seu puck.
#   Dobrar a água de um normale não faz um lungo: faz um normale aguado.
#
# COADOS/IMERSÃO — escala em ml final. O usuário quer X ml NA JARRA; o pó
#   sai de X ÷ ratio e a água a despejar precisa somar o que o borra
#   retém (~2 g por g de pó), senão o rendimento fica sempre abaixo.

def calcular_espresso(dose_base, estilo_cfg: dict, n_doses: int = 1,
                      cesto_max_g: float | None = None) -> dict:
    """Dimensiona uma extração de espresso por ESTILO × Nº DE DOSES.

    `estilo_cfg` é uma entrada de ESPRESSO_STYLES (precisa de 'ratio' e
    'time'). `n_doses` multiplica pó e yield — cada dose é um shot.

    Retorna dict com dose/yield/ratio/time por dose e totais, mais
    'aviso_cesto' quando a dose por puck excede a capacidade do cesto.
    """
    try:
        d = float(dose_base)
        n = max(1, int(n_doses))
    except (TypeError, ValueError):
        return {}
    ratio = float(estilo_cfg.get("ratio", 2.0))
    yld_1 = round(d * ratio, 1)

    aviso = ""
    if cesto_max_g and d > float(cesto_max_g):
        aviso = (f"Dose de {d:.1f} g excede a capacidade prática do cesto "
                 f"({cesto_max_g:.0f} g). O puck encosta na tela de dispersão "
                 f"e canaliza. Reduza a dose ou use mais doses.")

    return {
        "estilo_ratio": ratio,
        "n_doses": n,
        "dose_por_dose": round(d, 1),
        "yield_por_dose": yld_1,
        "dose": round(d * n, 1),          # pó total a moer
        "yield": round(yld_1 * n, 1),     # bebida total (g ≈ ml)
        "time": int(estilo_cfg.get("time", 28)),
        "ratio": ratio,
        "aviso_cesto": aviso,
    }


def calcular_coado(ml_final, ratio, retencao_g_por_g: float = 2.0,
                   descontar_retencao: bool = True) -> dict:
    """Dimensiona coados/imersão a partir do ML FINAL desejado na jarra.

    Resolve a retenção: o pó absorve `retencao_g_por_g` g de água por g de
    café. Para entregar `ml_final` na jarra é preciso despejar mais água.

        dose  = ml_final / (ratio - retencao)
        agua  = dose * ratio
        final = agua - dose * retencao   (≈ ml_final)

    Se `descontar_retencao=False`, ml_final é tratado como água despejada
    (comportamento antigo) e o rendimento líquido vem estimado à parte.
    """
    try:
        ml = float(ml_final)
        r = float(ratio)
        ret = max(0.0, float(retencao_g_por_g))
    except (TypeError, ValueError):
        return {}
    if ml <= 0 or r <= 0:
        return {}

    if not descontar_retencao:
        dose = ml / r
        agua = ml
    else:
        # ratio precisa superar a retenção, senão nada sai do coador.
        denom = r - ret
        if denom <= 0.5:
            return {"erro": (f"Ratio 1:{r:.1f} é curto demais para este método: "
                             f"o pó retém {ret:.1f} g de água por grama e quase "
                             f"nada chega à jarra. Aumente o ratio.")}
        dose = ml / denom
        agua = dose * r

    retido = dose * ret
    liquido = agua - retido
    return {
        "dose": round(dose, 1),
        "agua": round(agua, 1),          # água a despejar
        "retido": round(retido, 1),      # fica no borra/filtro
        "yield": round(liquido, 1),      # o que chega na jarra
        "ratio": round(r, 2),
        "erro": "",
    }


# ── Pressão: nominal (spec da bomba) → efetiva (no bolo de café) ───────
# Faixa saudável de pressão EFETIVA. Duplicada aqui para manter mc_core
# livre de imports de dados (módulo puro e testável isoladamente).
PRESSAO_EFETIVA_IDEAL = (8.0, 10.0)


def pressao_efetiva(nominal, maquina: dict | None = None) -> float | None:
    """Converte pressão NOMINAL da bomba em pressão EFETIVA no puck.

    O valor de catálogo ("15 bar", "20 bar") é o pico da bomba vibratória
    sem carga. Entre a bomba e o café há OPV, perda de carga e a
    resistência do próprio bolo — a extração real fica perto de 9 bar.
    Sem essa conversão o motor sensorial lê 15 bar como super-pressão e
    acusa adstringência/canalização que não existem.

    `maquina` é um dict do registro MAQUINAS_ESPRESSO. Se vier None (ou
    sem calibração), aplica a curva genérica abaixo.

    Retorna None se `nominal` não for numérico.
    """
    try:
        n = float(nominal)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None

    if maquina:
        m_nom, m_ef = maquina.get("nominal"), maquina.get("efetiva")
        if m_nom and m_ef:
            # Máquina conhecida: escala proporcional em torno do par
            # calibrado, para o caso do usuário digitar um valor diferente
            # do nominal de catálogo (ex.: leu 13 no manômetro).
            return round(n * (float(m_ef) / float(m_nom)), 1)

    # Curva genérica: até 10 bar o valor já é plausível como pressão de
    # extração. Acima disso é quase certamente spec de bomba — o excedente
    # é fortemente amortecido pelo OPV, com teto em ~10,5 bar no puck.
    if n <= 10.0:
        return round(n, 1)
    return round(min(10.5, 9.0 + (n - 10.0) * 0.10), 1)


def diagnostico_pressao(nominal, maquina: dict | None = None) -> dict | None:
    """Diagnóstico legível da pressão: converte, classifica e explica.

    Retorna {'nominal', 'efetiva', 'convertida', 'status', 'msg'} ou None.
    'status' ∈ {'baixa', 'ideal', 'alta'} e sempre se refere à EFETIVA.
    """
    ef = pressao_efetiva(nominal, maquina)
    if ef is None:
        return None
    n = float(nominal)
    lo, hi = PRESSAO_EFETIVA_IDEAL
    convertida = abs(ef - n) > 0.05

    if ef < lo:
        status = "baixa"
        msg = (f"Pressão efetiva {ef:.1f} bar abaixo da faixa {lo:.0f}–{hi:.0f} bar: "
               "tende a corpo fino e crema pobre. Moa mais fino ou aumente a dose.")
    elif ef > hi:
        status = "alta"
        msg = (f"Pressão efetiva {ef:.1f} bar acima de {hi:.0f} bar: risco real de "
               "canalização e adstringência. Moa mais grosso ou reduza a dose.")
    else:
        status = "ideal"
        msg = f"Pressão efetiva {ef:.1f} bar dentro da faixa ideal {lo:.0f}–{hi:.0f} bar."

    if convertida:
        msg += (f" (Os {n:.0f} bar da especificação são o pico da bomba sem carga, "
                f"não a pressão no bolo de café.)")
    return {"nominal": n, "efetiva": ef, "convertida": convertida,
            "status": status, "msg": msg}


def valida_email(email: str) -> bool:
    """Validação simples de formato de e-mail."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))


# ── Etapas cronometradas (para os alarmes do timer) ────────────────────
_STAGE_RE = re.compile(r"T\s*[=≈]\s*(\d+)(?::(\d+))?\s*s?\s*:\s*(.*)", re.I)


def parse_stages(passos) -> list[dict]:
    """Extrai etapas com marcador de tempo ('T = 0:45: ...') dos passos de
    uma receita → lista ordenada de {"t": segundos, "label": rótulo curto}.

    Usado para pré-carregar os alarmes multi-etapa do timer de extração.
    Passos sem marcador de tempo são ignorados. Retorna [] se nenhum.
    """
    out = []
    for p in passos or []:
        m = _STAGE_RE.match(str(p).strip())
        if not m:
            continue
        mm = int(m.group(1))
        ss = int(m.group(2)) if m.group(2) else 0
        # "T = 30 s:" (só um número seguido de 's') → segundos, não minutos
        if m.group(2) is None and re.search(r"\d+\s*s\s*:", str(p)):
            secs = mm
        else:
            secs = mm * 60 + ss
        desc = re.sub(r"\s+", " ", m.group(3)).strip().rstrip(".")
        # Rótulo curto: primeira oração antes de vírgula/travessão, ~34 chars
        label = re.split(r"[,—.:(]", desc)[0].strip()[:34] or f"{secs}s"
        out.append({"t": secs, "label": label})
    out.sort(key=lambda x: x["t"])
    return out
