-- Usuarios 
CREATE TABLE app_user (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    date_joined     TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active       BOOLEAN NOT NULL DEFAULT true
);

-- Documento subido por el usuario
CREATE TABLE document (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    original_path   VARCHAR(500) NOT NULL,
    size_bytes      INTEGER,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Plantillas de formato reutilizables
CREATE TABLE format_template (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
    name            VARCHAR(150) NOT NULL,
    font            VARCHAR(100) NOT NULL,
    font_size       NUMERIC(4,1) NOT NULL,
    margin_top      NUMERIC(4,2) NOT NULL,
    margin_bottom   NUMERIC(4,2) NOT NULL,
    margin_left     NUMERIC(4,2) NOT NULL,
    margin_right    NUMERIC(4,2) NOT NULL,
    line_spacing    NUMERIC(3,2) NOT NULL DEFAULT 1.0,
    is_public       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agentes de IA
CREATE TABLE ai_agent (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    provider        VARCHAR(100) NOT NULL,
    alias           VARCHAR(100) NOT NULL,
    encrypted_api_key VARCHAR(500) NOT NULL,
    added_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active       BOOLEAN NOT NULL DEFAULT true
);

-- Formateo (Documento + Plantilla + Agente de IA)
CREATE TABLE formatting_job (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    template_id     INTEGER NOT NULL REFERENCES format_template(id),
    agent_id        INTEGER REFERENCES ai_agent(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','completed','failed')),
    result_path     VARCHAR(500),
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

-- Bitácora/log de eventos de cada trabajo
CREATE TABLE job_log (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER NOT NULL REFERENCES formatting_job(id) ON DELETE CASCADE,
    event       VARCHAR(255) NOT NULL,
    detail      TEXT,
    logged_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);