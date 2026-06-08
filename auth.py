"""
Módulo de autenticação com hash de senha e gerenciamento de usuários.
"""
import hashlib
import secrets
from typing import Optional, Tuple
import psycopg2
import psycopg2.extras


def _get_db():
    """Obtém conexão com PostgreSQL a partir de secrets."""
    import streamlit as st
    try:
        db = st.connection("postgresql")
        return db.connection()
    except Exception:
        return None


def hash_senha(senha: str) -> str:
    """Cria hash da senha com salt."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    try:
        salt, hash_armazenado = senha_hash.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_armazenado
    except Exception:
        return False


def criar_usuario(email: str, senha: str, nome: str = "") -> Tuple[bool, str]:
    """Cria novo usuário. Retorna (sucesso, mensagem)."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco de dados"

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Verifica se email já existe
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            return False, "Email já cadastrado"

        # Cria novo usuário
        senha_hash = hash_senha(senha)
        cursor.execute(
            "INSERT INTO usuarios (email, senha_hash, nome) VALUES (%s, %s, %s) RETURNING id",
            (email, senha_hash, nome)
        )
        usuario_id = cursor.fetchone()['id']
        conn.commit()

        return True, f"Usuário criado com ID {usuario_id}"
    except Exception as e:
        return False, f"Erro ao criar usuário: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def verificar_login(email: str, senha: str) -> Tuple[bool, Optional[int], str]:
    """Verifica login. Retorna (sucesso, user_id, mensagem)."""
    conn = _get_db()
    if not conn:
        return False, None, "Erro ao conectar ao banco de dados"

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()

        if not usuario:
            return False, None, "Email ou senha incorretos"

        if not verificar_senha(senha, usuario['senha_hash']):
            return False, None, "Email ou senha incorretos"

        return True, usuario['id'], "Login realizado com sucesso"
    except Exception as e:
        return False, None, f"Erro ao fazer login: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def obter_usuario_por_id(user_id: int) -> Optional[dict]:
    """Obtém dados do usuário pelo ID."""
    conn = _get_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id, email, nome FROM usuarios WHERE id = %s", (user_id,))
        resultado = cursor.fetchone()
        return dict(resultado) if resultado else None
    except Exception:
        return None
    finally:
        cursor.close()
        conn.close()
