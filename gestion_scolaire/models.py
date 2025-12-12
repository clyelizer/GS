"""
Gestion Scolaire - Modèles de données SQLAlchemy
Version 2.0 - Modèles complets avec support multi-rôles
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from gestion_scolaire import db


# ============================================
# MODÈLES UTILISATEURS
# ============================================

class User(UserMixin, db.Model):
    """Modèle utilisateur pour tous les rôles (admin, enseignant, élève, parent)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Informations personnelles
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # 'M', 'F', 'Autre'
    
    # Rôle: 'admin', 'teacher', 'student', 'parent'
    role = db.Column(db.String(20), nullable=False, default='student', index=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relations pour les étudiants
    current_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=True)
    current_class = db.relationship('SchoolClass', backref=db.backref('students', lazy='dynamic'), foreign_keys=[current_class_id])
    
    # Alias pour compatibilité
    @property
    def school_class_id(self):
        return self.current_class_id
    
    @school_class_id.setter
    def school_class_id(self, value):
        self.current_class_id = value
    
    @property
    def school_class(self):
        return self.current_class
    
    # Matricule pour les étudiants
    matricule = db.Column(db.String(50), unique=True, nullable=True)
    
    # Relations pour les parents (un parent peut avoir plusieurs enfants)
    children = db.relationship('User', secondary='parent_student',
                              primaryjoin='User.id==parent_student.c.parent_id',
                              secondaryjoin='User.id==parent_student.c.student_id',
                              backref='parents')
    
    # Relations pour les enseignants (matières enseignées)
    subjects_taught = db.relationship('Subject', secondary='teacher_subject',
                                     backref=db.backref('teachers', lazy='dynamic'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Hache et stocke le mot de passe"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifie le mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'
    
    def is_parent(self):
        return self.role == 'parent'
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# Table d'association parent-élève
parent_student = db.Table('parent_student',
    db.Column('parent_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

# Table d'association enseignant-matière
teacher_subject = db.Table('teacher_subject',
    db.Column('teacher_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True)
)


# ============================================
# MODÈLES ACADÉMIQUES
# ============================================

class AcademicYear(db.Model):
    """Modèle pour les années scolaires"""
    __tablename__ = 'academic_years'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # Ex: "2024-2025"
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AcademicYear {self.name}>'


class SchoolClass(db.Model):
    """Modèle pour les classes scolaires"""
    __tablename__ = 'school_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    level = db.Column(db.String(50), nullable=True)  # "Seconde", "Première", "Terminale"
    section = db.Column(db.String(10), nullable=True)  # "A", "C", "D"
    description = db.Column(db.Text, nullable=True)
    capacity = db.Column(db.Integer, default=50)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=True)
    
    # Professeur principal
    main_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    main_teacher = db.relationship('User', foreign_keys=[main_teacher_id])
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def student_count(self):
        """Retourne le nombre d'élèves dans la classe"""
        return self.students.count()
    
    def __repr__(self):
        return f'<SchoolClass {self.name}>'


class Subject(db.Model):
    """Modèle pour les matières"""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # "Sciences", "Lettres", "Langues", etc.
    default_coef = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def coefficient(self):
        """Alias pour default_coef"""
        return self.default_coef
    
    @coefficient.setter
    def coefficient(self, value):
        self.default_coef = value
    
    def __repr__(self):
        return f'<Subject {self.name}>'


# ============================================
# MODÈLES NOTES ET BULLETINS
# ============================================

class Grade(db.Model):
    """Modèle pour les notes des étudiants"""
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    subject_name = db.Column(db.String(100), nullable=False)  # Nom de la matière (pour flexibilité)
    
    # Notes
    moy_cl = db.Column(db.Float, nullable=False)  # Moyenne de classe/continue
    n_compo = db.Column(db.Float, nullable=False)  # Note de composition
    coef = db.Column(db.Integer, nullable=False, default=1)
    
    # Métadonnées
    period = db.Column(db.String(50), nullable=False)  # "1ère Période", "2e Période", "3e Période"
    academic_year = db.Column(db.String(20), nullable=True)  # "2024-2025"
    appreciation = db.Column(db.String(200), nullable=True)
    
    # Enseignant qui a saisi la note
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    student = db.relationship('User', foreign_keys=[student_id], backref='grades')
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    subject = db.relationship('Subject', backref='grades')
    
    @property
    def average(self):
        """Calcule la moyenne pondérée (MG = (Moy.CL + 2*N.Compo) / 3)"""
        return round((self.moy_cl + 2 * self.n_compo) / 3, 2)
    
    @property
    def weighted_average(self):
        """Calcule la moyenne coefficientée"""
        return round(self.average * self.coef, 2)
    
    @staticmethod
    def get_appreciation(average):
        """Retourne l'appréciation basée sur la moyenne"""
        if average >= 18:
            return "Excellent"
        elif average >= 16:
            return "Très Bien"
        elif average >= 14:
            return "Bien"
        elif average >= 12:
            return "Assez Bien"
        elif average >= 10:
            return "Passable"
        elif average >= 8:
            return "Insuffisant"
        else:
            return "Faible"
    
    def auto_appreciation(self):
        """Génère automatiquement l'appréciation"""
        return self.get_appreciation(self.average)
    
    def __repr__(self):
        return f'<Grade {self.subject_name} for student {self.student_id}: {self.average}>'


class BulletinStructure(db.Model):
    """Modèle pour la structure des bulletins par classe"""
    __tablename__ = 'bulletin_structures'
    
    id = db.Column(db.Integer, primary_key=True)
    school_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), unique=True, nullable=False)
    school_class = db.relationship('SchoolClass', backref=db.backref('bulletin_structure', uselist=False, lazy='joined'))
    
    # Matières stockées en JSON ou texte séparé par virgules
    subjects_part1 = db.Column(db.Text, nullable=False)  # Matières principales
    subjects_part2 = db.Column(db.Text, nullable=False)  # Matières secondaires
    
    # Configuration du bulletin
    title = db.Column(db.String(200), nullable=True)
    school_name = db.Column(db.String(200), default="Lycée Michel ALLAIRE")
    school_address = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_subjects_part1_list(self):
        """Retourne la liste des matières de la partie 1"""
        return [s.strip() for s in self.subjects_part1.split(',') if s.strip()]
    
    def get_subjects_part2_list(self):
        """Retourne la liste des matières de la partie 2"""
        return [s.strip() for s in self.subjects_part2.split(',') if s.strip()]
    
    def get_all_subjects(self):
        """Retourne toutes les matières (parties 1 et 2 combinées)"""
        return sorted(list(set(self.get_subjects_part1_list() + self.get_subjects_part2_list())))
    
    def __repr__(self):
        return f'<BulletinStructure for class {self.school_class.name if self.school_class else "Unknown"}>'


# ============================================
# MODÈLES PRÉSENCE ET COMMUNICATION
# ============================================

class Attendance(db.Model):
    """Modèle pour le suivi des présences"""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # Statut: 'present', 'absent', 'late', 'excused'
    status = db.Column(db.String(20), nullable=False, default='present')
    reason = db.Column(db.Text, nullable=True)
    
    # Période de la journée (optionnel)
    period = db.Column(db.String(20), nullable=True)  # 'morning', 'afternoon'
    
    # Enregistré par
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    student = db.relationship('User', foreign_keys=[student_id], backref='attendance_records')
    school_class = db.relationship('SchoolClass', backref='attendance_records')
    recorder = db.relationship('User', foreign_keys=[recorded_by])
    
    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.date}: {self.status}>'


class Message(db.Model):
    """Modèle pour la messagerie interne"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    
    def mark_as_read(self):
        """Marque le message comme lu"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<Message from {self.sender_id} to {self.recipient_id}>'


class Announcement(db.Model):
    """Modèle pour les annonces générales"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Cible: 'all', 'teachers', 'students', 'parents' ou ID de classe spécifique
    target_audience = db.Column(db.String(50), default='all')
    target_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=True)
    
    # Priorité: 'low', 'normal', 'high', 'urgent'
    priority = db.Column(db.String(20), default='normal')
    
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    author = db.relationship('User', backref='announcements')
    target_class = db.relationship('SchoolClass', backref='announcements')
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


# ============================================
# MODÈLE JOURNAL D'AUDIT
# ============================================

class AuditLog(db.Model):
    """Modèle pour tracer les actions importantes"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # Ex: "grade_created", "user_login"
    entity_type = db.Column(db.String(50), nullable=True)  # Ex: "Grade", "User"
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON pour détails supplémentaires
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by user {self.user_id}>'


# ============================================
# CONSTANTES
# ============================================

# Périodes standards
STANDARD_PERIODS = ["1ère Période", "2e Période", "3e Période"]

# Rôles disponibles
USER_ROLES = ['admin', 'teacher', 'student', 'parent']

# Statuts de présence
ATTENDANCE_STATUS = ['present', 'absent', 'late', 'excused']
