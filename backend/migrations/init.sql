-- Este arquivo será executado automaticamente quando o PostgreSQL iniciar
-- Garantindo que as tabelas existam

CREATE TABLE IF NOT EXISTS pacientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    idade INTEGER,
    sexo VARCHAR(1),
    diabetes_tipo VARCHAR(50),
    historico_medico TEXT,
    documento VARCHAR(100),
    medicamentos TEXT,
    alergias TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER REFERENCES pacientes(id),
    titulo VARCHAR(200) DEFAULT 'Chat sobre lesões',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id),
    content TEXT NOT NULL,
    is_user BOOLEAN DEFAULT TRUE,
    message_type VARCHAR(20) DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id),
    image_path VARCHAR(500) NOT NULL,
    filename VARCHAR(200),
    description TEXT,
    classification VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_pdfs (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER REFERENCES pacientes(id),
    file_path VARCHAR(500) NOT NULL,
    report_content TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_pacientes_documento ON pacientes(documento); 
CREATE INDEX IF NOT EXISTS idx_chats_paciente_id ON chats(paciente_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id ON chat_messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_images_chat_id ON images(chat_id);
CREATE INDEX IF NOT EXISTS idx_report_pdfs_paciente_id ON report_pdfs(paciente_id);