-- Schema PostgreSQL para Mateu Coffee
-- Criado para suportar autenticação real e CRUD funcional

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    nome VARCHAR(255),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de cafés
CREATE TABLE IF NOT EXISTS cafes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    origem VARCHAR(255),
    tipo VARCHAR(100),
    torrefacao VARCHAR(100),
    preco_kg NUMERIC(10, 2),
    estoque_gramas NUMERIC(10, 2) DEFAULT 0,
    notas TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de extrações
CREATE TABLE IF NOT EXISTS extractions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cafe_id INTEGER REFERENCES cafes(id) ON DELETE SET NULL,
    data DATE NOT NULL,
    gramas_cafe NUMERIC(10, 2) NOT NULL,
    gramas_agua NUMERIC(10, 2),
    tempo_segundos INTEGER,
    temperatura NUMERIC(5, 2),
    pressao NUMERIC(5, 2),
    metodo VARCHAR(100),
    notas TEXT,
    aroma INTEGER DEFAULT 5,
    acidez INTEGER DEFAULT 5,
    corpo INTEGER DEFAULT 5,
    sabor_notas TEXT,
    nota_geral NUMERIC(3, 1) DEFAULT 5.0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de receitas compartilhadas
CREATE TABLE IF NOT EXISTS shared_recipes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cafe_nome VARCHAR(255) NOT NULL,
    metodo VARCHAR(100) NOT NULL,
    dose_gramas NUMERIC(10, 2),
    agua_ml NUMERIC(10, 2),
    nota INTEGER,
    autor_anonimo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para receitas
CREATE INDEX IF NOT EXISTS idx_shared_recipes_user_id ON shared_recipes(user_id);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_cafes_user_id ON cafes(user_id);
CREATE INDEX IF NOT EXISTS idx_extractions_user_id ON extractions(user_id);
CREATE INDEX IF NOT EXISTS idx_extractions_cafe_id ON extractions(cafe_id);
CREATE INDEX IF NOT EXISTS idx_extractions_data ON extractions(data);

-- Triggers para atualizar atualizado_em
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_usuarios_update ON usuarios;
CREATE TRIGGER tr_usuarios_update BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS tr_cafes_update ON cafes;
CREATE TRIGGER tr_cafes_update BEFORE UPDATE ON cafes
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
