"""
Módulo de CRUD para cafés e extrações no PostgreSQL.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, timedelta
import psycopg2
import psycopg2.extras
import os


def _get_db():
    """Obtém conexão com PostgreSQL."""
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            try:
                import streamlit as st
                database_url = st.secrets.get("database_url") or st.secrets.get("DATABASE_URL")
            except Exception:
                pass

        if not database_url:
            return None

        # Neon requer SSL — garante sslmode=require na URL
        if "sslmode" not in database_url:
            sep = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{sep}sslmode=require"

        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Erro ao conectar BD: {str(e)}")
        return None


def init_db():
    """Cria tabelas se não existirem."""
    conn = _get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome VARCHAR(255) DEFAULT '',
                remember_token TEXT,
                remember_token_expires TIMESTAMP,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cafes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                origem VARCHAR(255) DEFAULT '',
                tipo VARCHAR(100) DEFAULT '',
                torrefacao VARCHAR(100) DEFAULT '',
                preco_kg NUMERIC(10,2) DEFAULT 0,
                estoque_gramas NUMERIC(10,2) DEFAULT 0,
                notas TEXT DEFAULT '',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                cafe_id INTEGER REFERENCES cafes(id) ON DELETE SET NULL,
                data DATE NOT NULL,
                gramas_cafe NUMERIC(10,2) NOT NULL,
                gramas_agua NUMERIC(10,2),
                tempo_segundos INTEGER,
                temperatura NUMERIC(5,2),
                pressao NUMERIC(5,2),
                metodo VARCHAR(100) DEFAULT '',
                notas TEXT DEFAULT '',
                aroma INTEGER DEFAULT 0,
                acidez INTEGER DEFAULT 0,
                corpo INTEGER DEFAULT 0,
                sabor_notas TEXT DEFAULT '',
                nota_geral NUMERIC(4,2) DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_recipes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                cafe_nome VARCHAR(255) NOT NULL,
                metodo VARCHAR(100) DEFAULT '',
                dose_gramas NUMERIC(10,2) DEFAULT 0,
                agua_ml NUMERIC(10,2) DEFAULT 0,
                nota INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrações — colunas que podem faltar em tabelas antigas
        migrations = [
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nome VARCHAR(255) DEFAULT ''",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS remember_token TEXT",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS remember_token_expires TIMESTAMP",
        ]
        for sql in migrations:
            cursor.execute(sql)

        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao inicializar BD: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


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
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"
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
    except psycopg2.Error as e:
        import streamlit as st
        st.error(f"Erro ao listar cafés: {str(e)}")
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
    except psycopg2.Error as e:
        import streamlit as st
        st.error(f"Erro ao obter café: {str(e)}")
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
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"
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
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"
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
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"
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
    except psycopg2.Error as e:
        import streamlit as st
        st.error(f"Erro ao listar extrações: {str(e)}")
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
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"
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
    except psycopg2.Error as e:
        import streamlit as st
        st.error(f"Erro ao obter estatísticas: {str(e)}")
        return {"total_cafes": 0, "total_extractions": 0, "consumo_semana": 0, "consumo_hoje": 0}
    finally:
        cursor.close()
        conn.close()


# ── ANÁLISE SENSORIAL ──────────────────────────────────────────────

def atualizar_analise_sensorial(extracao_id: int, user_id: int, aroma: int, acidez: int,
                                corpo: int, sabor_notas: str, nota_geral: float) -> Tuple[bool, str]:
    """Atualiza análise sensorial de uma extração."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE extractions
            SET aroma = %s, acidez = %s, corpo = %s, sabor_notas = %s, nota_geral = %s
            WHERE id = %s AND user_id = %s
        """, (aroma, acidez, corpo, sabor_notas, nota_geral, extracao_id, user_id))
        conn.commit()
        return True, "Análise sensorial salva"
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def obter_melhor_receita_por_metodo(user_id: int, metodo: str) -> Optional[Dict[str, Any]]:
    """Retorna a receita com melhor nota média para um método."""
    conn = _get_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT c.nome as cafe, e.metodo, e.gramas_cafe, e.gramas_agua,
                   AVG(e.nota_geral) as nota_media
            FROM extractions e
            LEFT JOIN cafes c ON e.cafe_id = c.id
            WHERE e.user_id = %s AND e.metodo = %s AND e.nota_geral > 0
            GROUP BY c.nome, e.metodo, e.gramas_cafe, e.gramas_agua
            ORDER BY nota_media DESC
            LIMIT 1
        """, (user_id, metodo))
        resultado = cursor.fetchone()
        return dict(resultado) if resultado else None
    except psycopg2.Error:
        return None
    finally:
        cursor.close()
        conn.close()


def obter_notas_por_metodo(user_id: int) -> List[Dict[str, Any]]:
    """Retorna nota média por método de extração."""
    conn = _get_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT metodo, AVG(nota_geral) as nota_media, COUNT(*) as total
            FROM extractions
            WHERE user_id = %s AND nota_geral > 0
            GROUP BY metodo
            ORDER BY nota_media DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error:
        return []
    finally:
        cursor.close()
        conn.close()


def obter_evolucao_notas(user_id: int, dias: int = 60) -> List[Dict[str, Any]]:
    """Retorna evolução de notas ao longo do tempo."""
    conn = _get_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        data_limite = date.today() - timedelta(days=dias)
        cursor.execute("""
            SELECT data, nota_geral
            FROM extractions
            WHERE user_id = %s AND data >= %s AND nota_geral > 0
            ORDER BY data ASC
        """, (user_id, data_limite))
        return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error:
        return []
    finally:
        cursor.close()
        conn.close()


# ── RECEITAS COMPARTILHADAS ────────────────────────────────────────

def criar_receita_compartilhada(user_id: int, cafe_nome: str, metodo: str,
                               dose_gramas: float, agua_ml: float, nota: int) -> Tuple[bool, str]:
    """Cria uma receita compartilhada."""
    conn = _get_db()
    if not conn:
        return False, "Erro ao conectar ao banco"

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO shared_recipes (user_id, cafe_nome, metodo, dose_gramas, agua_ml, nota)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, cafe_nome, metodo, dose_gramas, agua_ml, nota))
        conn.commit()
        return True, "Receita compartilhada com sucesso"
    except psycopg2.Error as e:
        return False, f"Erro banco de dados: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def listar_receitas_compartilhadas(limite: int = 20) -> List[Dict[str, Any]]:
    """Lista receitas compartilhadas por toda a comunidade."""
    conn = _get_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT cafe_nome, metodo, dose_gramas, agua_ml, nota, criado_em
            FROM shared_recipes
            ORDER BY criado_em DESC
            LIMIT %s
        """, (limite,))
        return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error:
        return []
    finally:
        cursor.close()
        conn.close()
