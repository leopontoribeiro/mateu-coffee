-- Schema PostgreSQL — Mateu Coffee
-- Documentação do schema real criado por _init_db() em streamlit_app_final.py
-- NÃO executar manualmente — o app cria e migra automaticamente no startup.

CREATE TABLE IF NOT EXISTS usuarios (
    id                     SERIAL PRIMARY KEY,
    email                  TEXT UNIQUE NOT NULL,
    senha_hash             TEXT NOT NULL,           -- bcrypt ($2b$...) ou legado SHA-256
    criado_em              TIMESTAMP DEFAULT NOW(),
    remember_token         TEXT,
    remember_token_expires TIMESTAMP,
    last_grinder           TEXT,
    last_clicks            INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS coffees (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER REFERENCES usuarios(id),
    data_cadastro     DATE NOT NULL DEFAULT CURRENT_DATE,
    nome              TEXT NOT NULL,
    tipo              TEXT NOT NULL DEFAULT 'Grãos',       -- 'Grãos' | 'Moído'
    torra             TEXT NOT NULL DEFAULT 'Média',       -- 'Clara' | 'Média' | 'Escura'
    notas             TEXT DEFAULT '',
    classificacao     INTEGER DEFAULT 0,                   -- 0–5 estrelas (0 = sem avaliação)
    classificacao_cafe TEXT DEFAULT '',                    -- 'Especial (>80 pts)' | 'Gourmet' | ...
    regiao            TEXT DEFAULT '',
    data_torra        DATE,
    tamanho_pacote    INTEGER DEFAULT 250,
    foto_embalagem    TEXT,                                -- base64 JPEG comprimido
    local_compra      TEXT DEFAULT '',
    valor_compra      FLOAT DEFAULT 0,
    data_compra       DATE,
    intensidade       INTEGER DEFAULT 5,                   -- 1–12
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS extracoes (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER REFERENCES usuarios(id),
    coffee_id            INTEGER REFERENCES coffees(id) ON DELETE CASCADE,
    data                 DATE NOT NULL DEFAULT CURRENT_DATE,
    data_hora_extracao   TIMESTAMP DEFAULT NOW(),
    metodo               TEXT NOT NULL DEFAULT 'Espresso',
    gramas               FLOAT NOT NULL DEFAULT 18,
    agua_alvo            FLOAT NOT NULL DEFAULT 300,
    tempo_extracao       INTEGER NOT NULL DEFAULT 150,
    moedor               TEXT DEFAULT '',
    clicks_moedor        INTEGER DEFAULT 0,
    tds                  FLOAT DEFAULT 0,
    temp_real            FLOAT,
    pressao_real         FLOAT,
    brew_ratio           FLOAT DEFAULT 0,
    ey                   FLOAT DEFAULT 0,
    fluxo                FLOAT DEFAULT 0,
    foto_caneca          TEXT,
    classificacao        INTEGER DEFAULT 0,
    notas                TEXT DEFAULT '',
    crema_stars          INTEGER DEFAULT 0,
    corpo_stars          INTEGER DEFAULT 0,
    equilibrio_stars     INTEGER DEFAULT 0,
    acidez_stars         INTEGER DEFAULT 0,
    amargor_stars        INTEGER DEFAULT 0,
    presenca_boca_stars  INTEGER DEFAULT 0,
    docura_stars         INTEGER DEFAULT 0,
    nota_final_stars     INTEGER DEFAULT 0,
    balanco_ideal        TEXT DEFAULT '',
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capsulas (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER REFERENCES usuarios(id),
    nome                 TEXT NOT NULL,
    marca                TEXT DEFAULT '',
    maquina              TEXT NOT NULL DEFAULT 'Nespresso',
    intensidade          INTEGER DEFAULT 5,
    quantidade           INTEGER DEFAULT 10,
    aluminio             BOOLEAN DEFAULT FALSE,
    volume_ml            INTEGER DEFAULT 40,
    foto_embalagem       TEXT,
    crema_stars          INTEGER DEFAULT 3,
    corpo_stars          INTEGER DEFAULT 3,
    equilibrio_stars     INTEGER DEFAULT 3,
    acidez_stars         INTEGER DEFAULT 3,
    amargor_stars        INTEGER DEFAULT 3,
    presenca_boca_stars  INTEGER DEFAULT 3,
    docura_stars         INTEGER DEFAULT 3,
    nota_final_stars     INTEGER DEFAULT 3,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backups (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES usuarios(id),
    tipo           TEXT NOT NULL DEFAULT 'manual',   -- 'manual' | 'semanal' | 'pre-restore'
    criado_em      TIMESTAMP DEFAULT NOW(),
    notas          TEXT DEFAULT '',
    coffees_data   JSONB DEFAULT '[]',
    extracoes_data JSONB DEFAULT '[]',
    capsulas_data  JSONB DEFAULT '[]',
    git_hash       TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_coffees_user_id   ON coffees(user_id);
CREATE INDEX IF NOT EXISTS idx_extracoes_user_id ON extracoes(user_id);
CREATE INDEX IF NOT EXISTS idx_extracoes_cafe_id ON extracoes(coffee_id);
CREATE INDEX IF NOT EXISTS idx_extracoes_data    ON extracoes(data);
CREATE INDEX IF NOT EXISTS idx_capsulas_user_id  ON capsulas(user_id);
CREATE INDEX IF NOT EXISTS idx_backups_criado_em ON backups(criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_backups_user_id   ON backups(user_id);
