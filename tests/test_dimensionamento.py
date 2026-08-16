"""Testes do dimensionamento da extração.

Duas lógicas distintas:
  ESPRESSO  — estilo (ratio sobre a mesma dose) × nº de doses (shots).
  COADOS    — ml final NA JARRA, descontando a água retida pelo borra.
"""
import pytest

import mc_core
from mc_data import (ESPRESSO_STYLES, ESPRESSO_STYLE_DEFAULT,
                     CESTO_CAPACIDADE_G, RETENCAO_G_POR_G, RETENCAO_PADRAO)

RIS = ESPRESSO_STYLES["Ristretto"]
NOR = ESPRESSO_STYLES["Normale"]
LUN = ESPRESSO_STYLES["Lungo"]


# ── Espresso: os três estilos sobre a mesma dose ───────────────────────
@pytest.mark.parametrize("cfg,yield_esperado,tempo", [
    (RIS, 27.0, 25),
    (NOR, 36.0, 28),
    (LUN, 54.0, 35),
])
def test_estilos_com_18g(cfg, yield_esperado, tempo):
    r = mc_core.calcular_espresso(18.0, cfg)
    assert r["dose"] == 18.0
    assert r["yield"] == yield_esperado
    assert r["time"] == tempo


def test_estilos_mantem_a_mesma_dose():
    """O que muda entre os estilos é o yield, não o pó."""
    doses = {mc_core.calcular_espresso(18.0, c)["dose"]
             for c in (RIS, NOR, LUN)}
    assert doses == {18.0}


def test_ratio_cresce_de_ristretto_para_lungo():
    ys = [mc_core.calcular_espresso(18.0, c)["yield"] for c in (RIS, NOR, LUN)]
    assert ys == sorted(ys)


# ── Nº de doses multiplica pó E bebida ─────────────────────────────────
def test_duas_doses_dobram_po_e_bebida():
    r = mc_core.calcular_espresso(18.0, NOR, n_doses=2)
    assert r["dose"] == 36.0
    assert r["yield"] == 72.0
    assert r["dose_por_dose"] == 18.0
    assert r["yield_por_dose"] == 36.0


def test_n_doses_nao_altera_o_ratio():
    """Mais shots não mudam a receita de cada shot."""
    for n in (1, 2, 3, 5):
        r = mc_core.calcular_espresso(18.0, NOR, n_doses=n)
        assert r["yield"] / r["dose"] == pytest.approx(2.0)


def test_n_doses_invalido_vira_um():
    assert mc_core.calcular_espresso(18.0, NOR, n_doses=0)["n_doses"] == 1
    assert mc_core.calcular_espresso(18.0, NOR, n_doses=-3)["n_doses"] == 1


# ── Capacidade do cesto ────────────────────────────────────────────────
def test_dose_dentro_do_cesto_nao_avisa():
    r = mc_core.calcular_espresso(18.0, NOR, cesto_max_g=CESTO_CAPACIDADE_G[58])
    assert r["aviso_cesto"] == ""


def test_dose_acima_do_cesto_avisa():
    r = mc_core.calcular_espresso(26.0, NOR, cesto_max_g=CESTO_CAPACIDADE_G[58])
    assert "excede a capacidade" in r["aviso_cesto"]


def test_aviso_olha_a_dose_por_puck_nao_o_total():
    """3 doses de 18g são 3 pucks de 18g — não um puck de 54g."""
    r = mc_core.calcular_espresso(18.0, NOR, n_doses=3,
                                  cesto_max_g=CESTO_CAPACIDADE_G[58])
    assert r["dose"] == 54.0
    assert r["aviso_cesto"] == ""


# ── Coados: retenção ───────────────────────────────────────────────────
def test_agua_despejada_supera_o_ml_final():
    r = mc_core.calcular_coado(500, 16.0, 2.0)
    assert r["agua"] > 500
    assert r["yield"] == pytest.approx(500, abs=1.0)


def test_conservacao_agua_igual_retido_mais_liquido():
    r = mc_core.calcular_coado(400, 16.0, 2.0)
    assert r["agua"] == pytest.approx(r["retido"] + r["yield"], abs=0.5)


def test_retencao_e_proporcional_a_dose():
    r = mc_core.calcular_coado(500, 16.0, 2.0)
    assert r["retido"] == pytest.approx(r["dose"] * 2.0, abs=0.5)


def test_sem_descontar_retencao_o_rendimento_fica_abaixo():
    """Comportamento antigo: promete 500ml e entrega menos."""
    r = mc_core.calcular_coado(500, 16.0, 2.0, descontar_retencao=False)
    assert r["agua"] == 500
    assert r["yield"] < 500


def test_descontar_entrega_mais_cafe_que_nao_descontar():
    com = mc_core.calcular_coado(500, 16.0, 2.0)
    sem = mc_core.calcular_coado(500, 16.0, 2.0, descontar_retencao=False)
    assert com["dose"] > sem["dose"]
    assert com["yield"] > sem["yield"]


@pytest.mark.parametrize("metodo", list(RETENCAO_G_POR_G))
def test_todos_os_metodos_coados_tem_ratio_viavel(metodo):
    """Ratio precisa superar a retenção, senão nada chega à jarra."""
    from mc_data import METHOD_PROFILES
    prof = METHOD_PROFILES.get(metodo)
    if not prof or prof["pressure"] is not None:
        pytest.skip("método com pressão")
    r = mc_core.calcular_coado(400, prof["ratio"], RETENCAO_G_POR_G[metodo])
    assert not r.get("erro"), f"{metodo}: {r.get('erro')}"
    assert r["dose"] > 0


def test_ratio_curto_demais_retorna_erro():
    r = mc_core.calcular_coado(300, 2.0, 2.0)
    assert r.get("erro")


@pytest.mark.parametrize("ml,ratio", [(0, 16), (-5, 16), (300, 0), (None, 16)])
def test_coado_entradas_invalidas(ml, ratio):
    assert mc_core.calcular_coado(ml, ratio, 2.0) in ({}, {})


# ── Escalar coado preserva o ratio ─────────────────────────────────────
@pytest.mark.parametrize("ml", [250, 500, 1000])
def test_escala_de_coado_preserva_ratio(ml):
    r = mc_core.calcular_coado(ml, 16.0, 2.0)
    assert r["agua"] / r["dose"] == pytest.approx(16.0, abs=0.05)
