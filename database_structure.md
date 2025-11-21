# Base de données

## Schéma de base de données (PostgreSQL)

```sql
-- Configuration de la base de données
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table des filières
CREATE TABLE filieres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,      -- ex: "12e SE", "10e SExp"
    CONSTRAINT valid_filiere_format CHECK (
        name ~ '^(10|11|12)e (SE|SExp|SEco|SS|LL|S,C)$'
    )
    number_of_periods INTEGER NOT NULL CHECK (number_of_periods IN (2, 3)),
    subjects_group1 JSONB NOT NULL,         -- Matières principales avec coefficients
    subjects_group2 JSONB NOT NULL,         -- Matières secondaires avec coefficients
    academic_year VARCHAR(9) NOT NULL,
    head_teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_academic_year CHECK (academic_year ~* '^[0-9]{4}-[0-9]{4}$')
);

-- Table des utilisateurs
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'teacher', 'student', 'parent')),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone_number VARCHAR(20),
    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    filiere_id INTEGER REFERENCES filieres(id) ON DELETE SET NULL,
    subjects TEXT[], -- Pour les enseignants
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$')
);

-- Table des structures de bulletin
CREATE TABLE bulletin_structures (
    id SERIAL PRIMARY KEY,
    filiere_id INTEGER REFERENCES filieres(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_filiere_structure UNIQUE (filiere_id)
);

-- Fonction pour valider la période selon la filière
CREATE OR REPLACE FUNCTION validate_period()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM filieres f
        JOIN users s ON s.filiere_id = f.id
        WHERE s.id = NEW.student_id
        AND (
            (f.number_of_periods = 2 AND NEW.period NOT IN ('1ère Période', '2ème Période'))
            OR
            (f.number_of_periods = 3 AND NEW.period NOT IN ('1ère Période', '2ème Période', '3ème Période'))
        )
    ) THEN
        RAISE EXCEPTION 'Période invalide pour cette filière';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Table des notes
CREATE TABLE grades (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    subject VARCHAR(80) NOT NULL,
    moyenne_classe NUMERIC(4,2) DEFAULT 0 CHECK (moyenne_classe >= 0 AND moyenne_classe <= 20),  -- Notes des devoirs
    note_composition NUMERIC(4,2) DEFAULT 0 CHECK (note_composition >= 0 AND note_composition <= 20),  -- Notes des compositions
    is_moyenne_classe_active BOOLEAN DEFAULT true,  -- Indique si la note de devoir a été saisie
    is_composition_active BOOLEAN DEFAULT true,     -- Indique si la note de composition a été saisie
    coefficient INTEGER CHECK (coefficient > 0),
    appreciation TEXT,
    period VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_at_least_one_note_active CHECK (is_moyenne_classe_active = true OR is_composition_active = true),
    CONSTRAINT check_inactive_notes_are_zero CHECK (
        (is_moyenne_classe_active = false AND moyenne_classe = 0) OR is_moyenne_classe_active = true
        AND
        (is_composition_active = false AND note_composition = 0) OR is_composition_active = true
    )
);

-- Table des bulletins
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filiere_id INTEGER REFERENCES filieres(id) ON DELETE CASCADE,
    period VARCHAR(100) NOT NULL,
    averages JSONB NOT NULL,  -- Structure: {"group1": number, "group2": number, "final": number}
    class_statistics JSONB NOT NULL, -- Structure: {"min": number, "max": number, "average": number}
    rank INTEGER NOT NULL,
    total_students INTEGER NOT NULL,
    appreciation TEXT GENERATED ALWAYS AS (
        CASE 
            WHEN (averages->>'final')::numeric >= 16 THEN 'Très Bien'
            WHEN (averages->>'final')::numeric >= 14 THEN 'Bien'
            WHEN (averages->>'final')::numeric >= 12 THEN 'Assez Bien'
            WHEN (averages->>'final')::numeric >= 10 THEN 'Passable'
            WHEN (averages->>'final')::numeric >= 8 THEN 'Insuffisant'
            ELSE 'Faible'
        END
    ) STORED,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by INTEGER[] -- Array d'IDs des enseignants
);

-- Table de sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_session UNIQUE (user_id, refresh_token)
);

-- Table d'audit
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Triggers pour l'audit
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        user_id,
        action,
        table_name,
        record_id,
        old_values,
        new_values,
        ip_address
    ) VALUES (
        current_setting('app.current_user_id')::INTEGER,
        TG_OP,
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN OLD.id
            ELSE NEW.id
        END,
        CASE
            WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)
            WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD)
            ELSE NULL
        END,
        CASE
            WHEN TG_OP = 'DELETE' THEN NULL
            ELSE row_to_json(NEW)
        END,
        current_setting('app.current_ip_address')::INET
    ) RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Appliquer le trigger d'audit aux tables principales
CREATE TRIGGER audit_users_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_grades_trigger
    AFTER INSERT OR UPDATE OR DELETE ON grades
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER validate_period_trigger
    BEFORE INSERT OR UPDATE ON grades
    FOR EACH ROW EXECUTE FUNCTION validate_period();

CREATE TRIGGER audit_reports_trigger
    AFTER INSERT OR UPDATE OR DELETE ON reports
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Index pour optimiser les performances
CREATE INDEX idx_grades_student_id ON grades(student_id);
CREATE INDEX idx_grades_teacher_id ON grades(teacher_id);
CREATE INDEX idx_grades_period ON grades(period);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_filiere ON users(filiere_id) WHERE filiere_id IS NOT NULL;
CREATE INDEX idx_reports_student_filiere ON reports(student_id, filiere_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Vues pour faciliter les requêtes courantes
CREATE VIEW student_averages AS
SELECT 
    g.student_id,
    g.subject,
    g.period,
    f.id as filiere_id,
    f.name as filiere_name,
    AVG((g.moyenne_classe + 2 * g.note_composition) / 3.0) as average
FROM grades g
JOIN users u ON g.student_id = u.id
JOIN filieres f ON u.filiere_id = f.id
GROUP BY g.student_id, g.subject, g.period, f.id, f.name;

-- Vue pour les statistiques de classe
CREATE VIEW class_statistics AS
SELECT 
    f.id as filiere_id,
    period,
    MIN(final_avg) as min_average,
    MAX(final_avg) as max_average,
    AVG(final_avg) as class_average,
    COUNT(*) as total_students
FROM (
    SELECT 
        u.filiere_id,
        g.period,
        calculate_final_average(u.id, g.period) as final_avg
    FROM users u
    JOIN grades g ON g.student_id = u.id
    WHERE u.role = 'student'
    GROUP BY u.id, u.filiere_id, g.period
) as student_averages
JOIN filieres f ON f.id = student_averages.filiere_id
GROUP BY f.id, period;

CREATE VIEW class_rankings AS
WITH student_overall_averages AS (
    SELECT 
        student_id,
        period,
        filiere_id,
        AVG(average) as overall_average,
        RANK() OVER (PARTITION BY filiere_id, period ORDER BY AVG(average) DESC) as rank
    FROM student_averages
    GROUP BY student_id, period, filiere_id
)
SELECT 
    soa.*,
    u.first_name,
    u.last_name,
    f.name as filiere_name
FROM student_overall_averages soa
JOIN users u ON soa.student_id = u.id
JOIN filieres f ON soa.filiere_id = f.id;

-- Fonctions utilitaires
CREATE OR REPLACE FUNCTION calculate_appreciation(average NUMERIC)
RETURNS TEXT AS $$
BEGIN
    RETURN CASE
        WHEN average >= 16 THEN 'Très Bien'
        WHEN average >= 14 THEN 'Bien'
        WHEN average >= 12 THEN 'Assez Bien'
        WHEN average >= 10 THEN 'Passable'
        WHEN average >= 8 THEN 'Insuffisant'
        ELSE 'Faible'
    END;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour calculer la moyenne d'un groupe
CREATE OR REPLACE FUNCTION calculate_group_average(
    student_id INTEGER,
    period VARCHAR,
    group_number INTEGER
)
RETURNS NUMERIC AS $$
DECLARE
    group_avg NUMERIC;
BEGIN
    WITH subject_averages AS (
        SELECT 
            g.subject,
            ((g.moyenne_classe + 2 * g.note_composition) / 3.0) * 
            CASE 
                WHEN group_number = 1 THEN 
                    (f.subjects_group1->>'coefficient')::numeric
                ELSE 
                    (f.subjects_group2->>'coefficient')::numeric
            END as weighted_avg
        FROM grades g
        JOIN users u ON g.student_id = u.id
        JOIN filieres f ON u.filiere_id = f.id
        WHERE g.student_id = student_id 
        AND g.period = period
    )
    SELECT AVG(weighted_avg) INTO group_avg
    FROM subject_averages;
    
    RETURN group_avg;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour calculer la moyenne finale
CREATE OR REPLACE FUNCTION calculate_final_average(
    student_id INTEGER,
    period VARCHAR
)
RETURNS NUMERIC AS $$
DECLARE
    group1_avg NUMERIC;
    group2_avg NUMERIC;
BEGIN
    group1_avg := calculate_group_average(student_id, period, 1);
    group2_avg := calculate_group_average(student_id, period, 2);
    RETURN (COALESCE(group1_avg, 0) + COALESCE(group2_avg, 0)) / 2;
END;
$$ LANGUAGE plpgsql;
```

## Configuration de backup et maintenance

### Script de backup automatique
```bash
#!/bin/bash

# Configuration
DB_NAME="school_db"
BACKUP_DIR="/backups/database"
RETENTION_DAYS=30

# Créer le répertoire de backup si nécessaire
mkdir -p $BACKUP_DIR

# Nom du fichier de backup avec timestamp
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

# Effectuer le backup
pg_dump -U school_user -F c -b -v -f "$BACKUP_FILE" $DB_NAME

# Supprimer les vieux backups
find $BACKUP_DIR -name "backup_*.sql" -mtime +$RETENTION_DAYS -delete
```

### Maintenance planifiée
```sql
-- Nettoyage des sessions expirées
DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP;

-- Archivage des anciennes données
CREATE TABLE archived_grades (
    LIKE grades INCLUDING ALL
);

-- Déplacer les notes anciennes vers l'archive
INSERT INTO archived_grades
SELECT *
FROM grades
WHERE created_at < CURRENT_DATE - INTERVAL '2 years';

-- Supprimer les notes archivées
DELETE FROM grades
WHERE created_at < CURRENT_DATE - INTERVAL '2 years';
```

## Optimisation des performances

### Index additionnels pour les requêtes fréquentes
```sql
-- Index pour la recherche de notes par période et matière
CREATE INDEX idx_grades_period_subject ON grades(period, subject);

-- Index pour la recherche d'utilisateurs par nom
CREATE INDEX idx_users_names ON users(last_name, first_name);

-- Index pour les bulletins par période
CREATE INDEX idx_reports_period ON reports(period);

-- Index pour les recherches full-text dans les appréciations
CREATE INDEX idx_grades_appreciation_gin ON grades USING gin(to_tsvector('french', appreciation));
```

### Partitionnement des données
```sql
-- Partitionnement des notes par année académique
CREATE TABLE grades_partition (
    LIKE grades INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Créer les partitions
CREATE TABLE grades_2024 PARTITION OF grades_partition
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE grades_2025 PARTITION OF grades_partition
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

## Sécurité de la base de données

### Rôles et permissions
```sql
-- Création des rôles
CREATE ROLE school_admin;
CREATE ROLE school_teacher;
CREATE ROLE school_student;
CREATE ROLE school_api;

-- Permissions pour l'administrateur
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO school_admin;

-- Permissions pour les enseignants
GRANT SELECT, INSERT, UPDATE ON grades TO school_teacher;
GRANT SELECT ON users TO school_teacher;
GRANT SELECT ON filieres TO school_teacher;

-- Permissions pour les étudiants
GRANT SELECT ON grades TO school_student;
GRANT SELECT ON reports TO school_student;

-- Permissions pour l'API
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO school_api;
```

### Encryption des données sensibles
```sql
-- Fonction pour chiffrer les données sensibles
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour déchiffrer les données sensibles
CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_data::bytea, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
