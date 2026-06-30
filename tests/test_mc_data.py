"""Testes de sanidade dos dados estáticos extraídos para mc_data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import mc_data


def test_listas_nao_vazias():
    assert len(mc_data.METODOS) >= 5
    assert "Espresso" in mc_data.METODOS
    assert len(mc_data._MOEDORES) >= 1
    assert len(mc_data._LOCAIS_COMPRA) >= 1
    assert len(mc_data.CLASSIFICACOES_CAFE) >= 1


def test_receitas_estrutura():
    assert len(mc_data.RECIPES) >= 5
    for r in mc_data.RECIPES:
        assert isinstance(r, dict)
        assert r.get("nome"), "toda receita precisa de nome"
