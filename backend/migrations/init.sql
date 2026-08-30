CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INTEGER,
    sex VARCHAR(1),
    diabetes_type VARCHAR(50),
    medical_history TEXT,
    document VARCHAR(100),
    medications TEXT,
    allergies TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id),
    title VARCHAR(200) DEFAULT 'Chat about wounds',
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
    model_version VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_pdfs (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id),
    file_path VARCHAR(500) NOT NULL,
    report_content TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patients_document ON patients(document);
CREATE INDEX IF NOT EXISTS idx_chats_patient_id ON chats(patient_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id ON chat_messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_images_chat_id ON images(chat_id);
CREATE INDEX IF NOT EXISTS idx_report_pdfs_patient_id ON report_pdfs(patient_id);
