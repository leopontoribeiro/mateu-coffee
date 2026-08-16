"""Coerência do modelo de extração entre as camadas.

Trava as invariantes que os bugs anteriores violaram:
  • pressão nominal ≠ pressão efetiva (uma tabela só)
  • retenção de água com uma fonte única (receita e EY concordando)
  • espresso dimensionado por estilo × doses, nunca escalado em ml
"""
import pytest

import mc_core
from mc_data import (ESPRESSO_STYLES, ESPRESSO_STYLE_DEFAULT, METHOD_PROFILES,
                     RETENCAO_G_POR_G, RETENCAO_PADRAO, PRESSAO_EFETIVA_IDEAL,
                     MAQUINAS_ESPRESSO, CESTO_CAPACIDADE_G, CESTO_PADRAO_MM)


# ── Integridade dos dados ──────────────────────────────────────────────
def test_estilo_default_existe():
    assert ESPRESSO_STYLE_DEFAULT in ESPRESSO_STYLES


@pytest.mark.parametrize("nome,cfg", ESPRESSO_STYLES.items())
def test_todo_estilo_tem_campos_obrigatorios(nome, cfg):
    for k in ("ratio", "time", "grind", "grind_delta", "ey_alvo", "desc"):
        assert k in cfg, f"{nome} sem '{k}'"
    lo, hi = cfg["ey_alvo"]
    assert 0 < lo < hi < 30


def test_ratios_dos_estilos_sao_crescentes():
    ordem = ["Ristretto", "Normale", "Lungo"]
    rs = [ESPRESSO_STYLES[n]["ratio"] for n in ordem]
    assert rs == sorted(rs) and len(set(rs)) == 3


def test_tempo_cresce_com_o_ratio():
    ts = [ESPRESSO_STYLES[n]["time"] for n in ["Ristretto", "Normale", "Lungo"]]
    assert ts == sorted(ts)


@pytest.mark.parametrize("nome,cfg", MAQUINAS_ESPRESSO.items())
def test_maquina_nunca_extrai_acima_da_faixa(nome, cfg):
    if cfg["efetiva"] is None:
        return
    assert cfg["efetiva"] <= PRESSAO_EFETIVA_IDEAL[1] + 0.5, \
        f"{nome}: efetiva {cfg['efetiva']} acima da faixa saudável"


def test_pressao_ideal_de_mc_core_bate_com_mc_data():
    """Duas constantes divergentes = diagnóstico inconsistente."""
    assert mc_core.PRESSAO_EFETIVA_IDEAL == PRESSAO_EFETIVA_IDEAL


# ── Retenção: fonte única entre receita e EY ───────────────────────────
def test_engine_usa_a_mesma_tabela_de_retencao():
    import streamlit_app_final as app
    assert app.CoffeeEngine.RETENCAO is RETENCAO_G_POR_G


@pytest.mark.parametrize("metodo", [m for m, p in METHOD_PROFILES.items()
                                    if p["pressure"] is None and m != "Outro"])
def test_receita_e_ey_concordam_sobre_o_liquido(metodo):
    """A água que a receita manda despejar tem que render o ml pedido,
    e o EY tem que ser calculado sobre esse mesmo líquido."""
    import streamlit_app_final as app
    prof = METHOD_PROFILES[metodo]
    ret = RETENCAO_G_POR_G.get(metodo, RETENCAO_PADRAO)
    alvo = 400.0
    r = mc_core.calcular_coado(alvo, prof["ratio"], ret)
    assert r["yield"] == pytest.approx(alvo, abs=1.0)

    bev_engine = r["agua"] - app.CoffeeEngine.RETENCAO.get(
        metodo, RETENCAO_PADRAO) * r["dose"]
    assert bev_engine == pytest.approx(r["yield"], abs=1.0)


# ── Espresso não escala em ml ──────────────────────────────────────────
def test_lungo_nao_e_normale_com_mais_agua():
    """Dobrar a água de um normale dá outro ratio que não o do lungo."""
    nor = mc_core.calcular_espresso(18.0, ESPRESSO_STYLES["Normale"])
    lun = mc_core.calcular_espresso(18.0, ESPRESSO_STYLES["Lungo"])
    assert lun["dose"] == nor["dose"]
    assert lun["yield"] != nor["yield"] * 2
    assert lun["time"] != nor["time"]


def test_duas_doses_nao_viram_um_lungo():
    duas = mc_core.calcular_espresso(18.0, ESPRESSO_STYLES["Normale"], n_doses=2)
    lungo = mc_core.calcular_espresso(18.0, ESPRESSO_STYLES["Lungo"])
    assert duas["yield"] == 72.0 and lungo["yield"] == 54.0
    assert duas["ratio"] != lungo["ratio"]


def test_cesto_padrao_tem_capacidade_definida():
    assert CESTO_PADRAO_MM in CESTO_CAPACIDADE_G
    base = METHOD_PROFILES["Espresso"]["dose"]
    assert base <= CESTO_CAPACIDADE_G[CESTO_PADRAO_MM]


# ── Fumaça: o app importa sem Streamlit rodando ────────────────────────
def test_app_importa():
    import streamlit_app_final  # noqa: F401


def test_perfis_nao_tem_chave_morta_yield_label():
    for m, p in METHOD_PROFILES.items():
        assert "yield_label" not in p, f"{m} ainda tem yield_label"
