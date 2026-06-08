"""
Módulo de CRUD para cafés e extrações no PostgreSQL.
"""
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
import psycopg2
import psycopg2.extras


def _get_db():
    """Obtém conexão com PostgreSQL."""
    import streamlit as st
    try:
        db = st.connection("postgresql")
        return db.connection()
    except Exception:
        return None


# ── CAFÉS ──────────────────────────────────────────────────────

def criar_cafe(user_id: int, nome: str, origem: str = "", tipo: str = "",
               torrefacao: str = "", preco_kg: float = 0, notas: str = "") -> Tuple[bool, str]:
    """Cria novo café. Retorna (sucesso, mensagem)."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cafes (user_id, nome, origem, tipo, torrefacao, preco_kg, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, nome, origem, tipo, torrefacao, preco_kg, notas))
        conn.commit()
        return True, "Café adicionado com sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def listar_cafes(user_id: int) -> List[Dict[str, Any]]:
    """Lista todos os cafés do usuário."""
    conn = _get_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT id, nome, origem, tipo, torrefacao, preco_kg, estoque_gramas, notas, criado_em
            FROM cafes WHERE user_id = %s ORDER BY criado_em DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        cursor.close()
        conn.close()


def obter_cafe(cafe_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Obtém um café específico."""
    conn = _get_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT * FROM cafes WHERE id = %s AND user_id = %s
        """, (cafe_id, user_id))
        resultado = cursor.fetchone()
        return dict(resultado) if resultado else None
    except Exception:
        return None
    finally:
        cursor.close()
        conn.close()


def atualizar_cafe(cafe_id: int, user_id: int, **kwargs) -> Tuple[bool, str]:
    """Atualiza um café."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        colunas = ", ".join([f"{k} = %s" for k in kwargs.keys()])
        valores = list(kwargs.values()) + [cafe_id, user_id]

        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE cafes SET {colunas}, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
        """, valores)
        conn.commit()
        return True, "Café atualizado com sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def deletar_cafe(cafe_id: int, user_id: int) -> Tuple[bool, str]:
    """Deleta um café."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cafes WHERE id = %s AND user_id = %s", (cafe_id, user_id))
        conn.commit()
        return True, "Café deletado com sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        cursor.close()
        conn.close()


# ── EXTRAÇÕES ──────────────────────────────────────────────────

def criar_extracao(user_id: int, cafe_id: int, data: date, gramas_cafe: float,
                   gramas_agua: float = None, tempo_segundos: int = None,
                   temperatura: float = None, pressao: float = None,
                   metodo: str = "", notas: str = "") -> Tuple[bool, str]:
    """Cria nova extração."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO extractions
            (user_id, cafe_id, data, gramas_cafe, gramas_agua, tempo_segundos, temperatura, pressao, metodo, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, cafe_id, data, gramas_cafe, gramas_agua, tempo_segundos, temperatura, pressao, metodo, notas))
        conn.commit()
        return True, "Extração registrada com sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def listar_extractions(user_id: int, cafe_id: int = None, dias: int = 30) -> List[Dict[str, Any]]:
    """Lista extrações do usuário (últimos N dias)."""
    conn = _get_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        data_limite = date.today() - timedelta(days=dias)

        if cafe_id:
            cursor.execute("""
                SELECT * FROM extractions
                WHERE user_id = %s AND cafe_id = %s AND data >= %s
                ORDER BY data DESC, criado_em DESC
            """, (user_id, cafe_id, data_limite))
        else:
            cursor.execute("""
                SELECT e.*, c.nome as cafe_nome FROM extractions e
                LEFT JOIN cafes c ON e.cafe_id = c.id
                WHERE e.user_id = %s AND e.data >= %s
                ORDER BY e.data DESC, e.criado_em DESC
            """, (user_id, data_limite))

        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        cursor.close()
        conn.close()


def deletar_extracao(extracao_id: int, user_id: int) -> Tuple[bool, str]:
    """Deleta uma extração."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM extractions WHERE id = %s AND user_id = %s", (extracao_id, user_id))
        conn.commit()
        return True, "Extração deletada com sucesso"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        cursor.close()
        conn.close()


# ── ESTATÍSTICAS ────────────────────────────────────────────────

def obter_estatisticas(user_id: int) -> Dict[str, Any]:
    """Obtém estatísticas do usuário."""
    conn = _get_db()
    if not conn:
        return {"total_cafes": 0, "total_extractions": 0, "consumo_semana": 0, "consumo_hoje": 0}

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        hoje = date.today()
        semana_atras = hoje - timedelta(days=6)

        # Total de cafés
        cursor.execute("SELECT COUNT(*) as cnt FROM cafes WHERE user_id = %s", (user_id,))
        total_cafes = cursor.fetchone()['cnt'] or 0

        # Total de extrações
        cursor.execute("SELECT COUNT(*) as cnt FROM extractions WHERE user_id = %s", (user_id,))
        total_extractions = cursor.fetchone()['cnt'] or 0

        # Consumo semana
        cursor.execute("""
            SELECT COALESCE(SUM(gramas_cafe), 0) as total
            FROM extractions WHERE user_id = %s AND data >= %s
        """, (user_id, semana_atras))
        consumo_semana = float(cursor.fetchone()['total'] or 0)

        # Consumo hoje
        cursor.execute("""
            SELECT COALESCE(SUM(gramas_cafe), 0) as total
            FROM extractions WHERE user_id = %s AND data = %s
        """, (user_id, hoje))
        consumo_hoje = float(cursor.fetchone()['total'] or 0)

        return {
            "total_cafes": total_cafes,
            "total_extractions": total_extractions,
            "consumo_semana": consumo_semana,
            "consumo_hoje": consumo_hoje,
            "consumo_media_dia": consumo_semana / 7 if consumo_semana else 0
        }
    except Exception:
        return {"total_cafes": 0, "total_extractions": 0, "consumo_semana": 0, "consumo_hoje": 0}
    finally:
        cursor.close()
        conn.close()


# Type hints
from typing import Tuple
