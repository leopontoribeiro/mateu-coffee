"""Testes da conversão pressão NOMINAL → EFETIVA.

Regressão do bug: o app tratava os 15 bar da especificação da Oster como
pressão de extração, disparando diagnóstico falso de adstringência e
canalização. 15 bar é o pico da bomba vibratória SEM CARGA; a extração
real acontece por volta de 9 bar.
"""
import pytest

import mc_core
from mc_data import MAQUINAS_ESPRESSO, PRESSAO_EFETIVA_IDEAL

OSTER = MAQUINAS_ESPRESSO["Oster Xpert Perfect Brew (BVSTEM7300)"]


# ── Regressão principal ────────────────────────────────────────────────
def test_oster_15bar_vira_9bar_efetivos():
    assert mc_core.pressao_efetiva(15.0, OSTER) == 9.0


def test_oster_15bar_nao_e_diagnosticada_como_alta():
    d = mc_core.diagnostico_pressao(15.0, OSTER)
    assert d["status"] == "ideal"
    assert d["convertida"] is True
    assert "sem carga" in d["msg"]


def test_oster_15bar_dentro_da_faixa_ideal():
    lo, hi = PRESSAO_EFETIVA_IDEAL
    assert lo <= mc_core.pressao_efetiva(15.0, OSTER) <= hi


# ── Curva genérica (máquina desconhecida) ──────────────────────────────
@pytest.mark.parametrize("nominal", [11.0, 15.0, 20.0])
def test_generica_nunca_passa_de_10_5_bar(nominal):
    assert mc_core.pressao_efetiva(nominal) <= 10.5


@pytest.mark.parametrize("nominal", [6.0, 8.0, 9.0, 10.0])
def test_generica_preserva_valores_plausiveis(nominal):
    """Até 10 bar o valor já é pressão de extração crível — não converte."""
    assert mc_core.pressao_efetiva(nominal) == nominal


def test_generica_15bar_fica_na_faixa_sca():
    lo, hi = PRESSAO_EFETIVA_IDEAL
    assert lo <= mc_core.pressao_efetiva(15.0) <= hi


# ── Máquina calibrada em 9 bar: conversão é identidade ─────────────────
def test_semi_profissional_nao_altera_valor():
    m = MAQUINAS_ESPRESSO["Semi-profissional (E61 / 9 bar calibrada)"]
    assert mc_core.pressao_efetiva(9.0, m) == 9.0
    assert mc_core.diagnostico_pressao(9.0, m)["convertida"] is False


def test_escala_proporcional_em_maquina_conhecida():
    """Usuário leu 12 bar no manômetro de uma máquina 15/9 → 7.2 efetivos."""
    assert mc_core.pressao_efetiva(12.0, OSTER) == 7.2


# ── Detecção real de pressão alta continua funcionando ─────────────────
def test_pressao_efetiva_alta_ainda_e_sinalizada():
    m = {"nominal": 10.0, "efetiva": 12.0}  # máquina descalibrada
    d = mc_core.diagnostico_pressao(10.0, m)
    assert d["status"] == "alta"
    assert "canaliza" in d["msg"].lower()


def test_pressao_baixa_e_sinalizada():
    d = mc_core.diagnostico_pressao(6.0)
    assert d["status"] == "baixa"


# ── Entradas inválidas ─────────────────────────────────────────────────
@pytest.mark.parametrize("v", [None, "", "abc", 0, -3])
def test_entradas_invalidas_retornam_none(v):
    assert mc_core.pressao_efetiva(v) is None
    assert mc_core.diagnostico_pressao(v) is None


def test_maquina_sem_calibracao_cai_na_curva_generica():
    m = MAQUINAS_ESPRESSO["Outra / não sei"]
    assert mc_core.pressao_efetiva(15.0, m) == mc_core.pressao_efetiva(15.0)
