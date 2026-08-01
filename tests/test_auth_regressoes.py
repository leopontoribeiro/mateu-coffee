"""Testes de regressão de autenticação e de acesso a dados.

São testes estáticos (AST + leitura do fonte) porque o alvo é um arquivo
Streamlit de 4 mil linhas que não dá para importar sem subir a sessão e o
banco. Ainda assim pegam exatamente as classes de bug que já derrubaram o
app em produção — que é o que um teste precisa fazer.
"""
import ast
import os
import re

import bcrypt
import pytest

import mc_core

_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "streamlit_app_final.py")


@pytest.fixture(scope="module")
def fonte():
    with open(_APP, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def arvore(fonte):
    return ast.parse(fonte)


def _funcao(arvore, nome):
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return no
    raise AssertionError(f"função {nome} não encontrada")


# ── Regressão: tela em branco para quem volta autenticado ──────────────
# O return que encerra o run depois de desenhar o login estava um nível
# acima, fora do `if not _check_remember_token()`. Com cookie válido a
# função devolvia True, o login era pulado e o return rodava mesmo assim:
# main() terminava sem renderizar nada e o app ficava preto para todo
# usuário que voltava pelo "manter-me conectado".
def test_return_do_login_nao_escapa_para_o_caminho_autenticado(arvore):
    main = _funcao(arvore, "main")

    gate = None
    for no in ast.walk(main):
        if isinstance(no, ast.If) and any(
                isinstance(sub, ast.Call)
                and getattr(sub.func, "id", "") == "_check_remember_token"
                for sub in ast.walk(no.test)):
            gate = no
            break
    assert gate is not None, "não achei o `if not _check_remember_token()` em main()"

    # Nenhum return pode ser irmão do gate: se o gate não entrar (sessão
    # restaurada), o fluxo tem de seguir para o app logado.
    for pai in ast.walk(main):
        for campo in ("body", "orelse"):
            corpo = getattr(pai, campo, None)
            if not isinstance(corpo, list) or gate not in corpo:
                continue
            irmaos_return = [n for n in corpo if isinstance(n, ast.Return)]
            assert not irmaos_return, (
                "há um `return` no mesmo bloco do gate de autenticação "
                f"(linha {irmaos_return[0].lineno}). Com sessão restaurada ele "
                "encerra main() antes de renderizar o app — tela em branco.")


def test_gate_de_login_termina_com_return_interno(arvore):
    """O bloco que desenha o login precisa encerrar o run, senão o app
    logado seria renderizado por baixo da tela de login."""
    main = _funcao(arvore, "main")
    for no in ast.walk(main):
        if isinstance(no, ast.If) and any(
                isinstance(sub, ast.Call)
                and getattr(sub.func, "id", "") == "_check_remember_token"
                for sub in ast.walk(no.test)):
            assert any(isinstance(n, ast.Return) for n in ast.walk(no)), (
                "o bloco de login não tem return: o app logado renderizaria junto")
            return
    raise AssertionError("gate de autenticação não encontrado")


# ── Regressão: SELECT * arrastando fotos base64 ────────────────────────
# Fotos são base64 no Postgres (MBs por linha). Um SELECT * numa listagem
# baixa dezenas de MB por rerun e trava a página inteira.
_TABELAS_COM_FOTO = ("extracoes", "coffees")


def test_listagens_nao_usam_select_estrela_em_tabela_com_foto(fonte):
    ofensores = []
    for m in re.finditer(r"SELECT\s+(?:\w+\.)?\*\s+FROM\s+(\w+)", fonte, re.I):
        tabela = m.group(1).lower()
        if tabela in _TABELAS_COM_FOTO:
            linha = fonte[:m.start()].count("\n") + 1
            # O backup precisa mesmo de todas as colunas — é uma cópia fiel.
            contexto = fonte[max(0, m.start() - 400):m.start()]
            if "_backup_criar" in contexto or "coffees_data" in contexto:
                continue
            ofensores.append(f"linha {linha}: SELECT * FROM {tabela}")
    assert not ofensores, (
        "SELECT * em tabela com foto base64 fora do backup — isto traz "
        "megabytes por rerun e trava a tela: " + "; ".join(ofensores))


def test_helper_de_foto_cobre_a_coluna_url_legada(fonte, arvore):
    """Parte das fotos foi gravada em foto_*_url. Sem COALESCE elas existem
    no banco e nunca aparecem na tela."""
    corpo = ast.get_source_segment(fonte, _funcao(arvore, "_foto")) or ""
    assert "COALESCE" in corpo, (
        "_foto() precisa ler a coluna canônica e a _url legada")


# ── Regressão: recuperação de senha não pode trocar a senha sozinha ────
# A versão antiga redefinia a senha de qualquer conta a partir do e-mail e
# mostrava a nova na tela: takeover em dois cliques.
def test_recuperacao_nao_redefine_senha_nem_exibe_credencial(fonte, arvore):
    dlg = _funcao(arvore, "_forgot_password_dialog")
    trecho = ast.get_source_segment(fonte, dlg) or ""
    assert "UPDATE usuarios SET senha_hash" not in trecho, (
        "o diálogo de recuperação está redefinindo a senha direto — takeover")
    assert "st.code(" not in trecho, (
        "o diálogo está exibindo uma credencial na tela")


def test_recuperacao_nao_revela_se_o_email_existe(fonte, arvore):
    dlg = _funcao(arvore, "_forgot_password_dialog")
    trecho = ast.get_source_segment(fonte, dlg) or ""
    assert "não encontrado" not in trecho.lower(), (
        "resposta diferente para e-mail inexistente permite enumerar contas")


def test_pedidos_antigos_sao_invalidados_antes_de_criar_o_novo(fonte, arvore):
    """A invalidação tem de vir antes do INSERT.

    Fazendo depois e filtrando por `token_hash <> hash(token)`, o bcrypt gera
    um salt novo a cada chamada, o hash nunca casa e o UPDATE queima o token
    recém-criado — o link chegava ao usuário já inválido.
    """
    dlg = _funcao(arvore, "_forgot_password_dialog")
    trecho = ast.get_source_segment(fonte, dlg) or ""
    pos_update = trecho.find("UPDATE password_resets SET used_at")
    pos_insert = trecho.find("INSERT INTO password_resets")
    assert pos_update != -1 and pos_insert != -1, "fluxo de reset não encontrado"
    assert pos_update < pos_insert, (
        "a invalidação dos pedidos antigos precisa vir antes do INSERT")
    assert "token_hash <>" not in trecho, (
        "comparar token_hash com um hash bcrypt novo nunca casa (salt aleatório)")


def test_reset_grava_apenas_hash_do_token(fonte, arvore):
    dlg = _funcao(arvore, "_forgot_password_dialog")
    trecho = ast.get_source_segment(fonte, dlg) or ""
    assert "_hash_senha(token)" in trecho, "o token precisa ser gravado hasheado"
    m = re.search(r"VALUES \(%s, %s, NOW\(\)", trecho)
    assert m, "INSERT do reset mudou de forma — revalidar que não grava o token cru"


def test_troca_de_senha_invalida_a_sessao_ativa(fonte, arvore):
    """Trocar a senha tem de derrubar o remember_token: senão quem estava
    logado com o token antigo continua dentro."""
    dlg = _funcao(arvore, "_reset_password_dialog")
    trecho = ast.get_source_segment(fonte, dlg) or ""
    assert "remember_token=NULL" in trecho, (
        "a troca de senha precisa limpar o remember_token")


# ── Regressão: token de sessão não pode viajar na URL ──────────────────
def test_token_de_sessao_nao_e_escrito_em_query_param(fonte):
    assert 'st.query_params["mc_token"] = ' not in fonte, (
        "token de 30 dias na query string vaza em histórico, logs e Referer")


# ── Isolamento entre contas ────────────────────────────────────────────
def _strings_sql(arvore):
    """Todo literal de string do módulo, com f-strings remontadas.

    Ler do AST em vez de fatiar o texto evita falso positivo com SQL
    quebrado em várias linhas por concatenação implícita.
    """
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            yield no.lineno, no.value
        elif isinstance(no, ast.JoinedStr):
            partes = [v.value for v in no.values
                      if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            yield no.lineno, " ".join(partes)


def test_escritas_em_dados_do_usuario_filtram_por_dono(arvore):
    """Todo UPDATE/DELETE em tabela de conteúdo precisa de user_id no WHERE."""
    alvo = re.compile(r"(UPDATE|DELETE FROM)\s+(extracoes|coffees|capsulas)\b", re.I)
    faltando = []
    for linha, sql in _strings_sql(arvore):
        m = alvo.search(sql)
        if not m:
            continue
        # A restauração de backup limpa a conta inteira antes de reinserir e
        # já roda com o user_id do dono no WHERE da própria query.
        if "user_id" not in sql:
            faltando.append(f"linha {linha}: {m.group(0)}")
    assert not faltando, (
        "escrita sem filtro de dono (permite mexer em dado de outra conta): "
        + "; ".join(faltando))


# ── Hashing de senha ───────────────────────────────────────────────────
def test_hash_vazio_nunca_autentica():
    """Contas criadas via Google nascem com senha_hash vazio; senha em branco
    não pode entrar nelas."""
    assert mc_core.verify_senha("", "") is False
    assert mc_core.verify_senha("qualquer", "") is False
    assert mc_core.verify_senha("", None) is False


def test_bcrypt_ida_e_volta():
    h = mc_core.hash_senha("SenhaForte!2026")
    assert h.startswith("$2")
    assert mc_core.verify_senha("SenhaForte!2026", h) is True
    assert mc_core.verify_senha("senhaforte!2026", h) is False


def test_hash_sha256_legado_ainda_valida():
    import hashlib
    salt = "abc123"
    legado = f"{salt}${hashlib.sha256(f'{salt}minhasenha'.encode()).hexdigest()}"
    assert mc_core.verify_senha("minhasenha", legado) is True
    assert mc_core.verify_senha("outra", legado) is False


def test_hash_malformado_nao_autentica():
    for ruim in ("$2", "sem-cifrao", "a$b$c$d", "   "):
        assert mc_core.verify_senha("x", ruim) is False
