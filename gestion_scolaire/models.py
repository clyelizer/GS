"""
Gestion Scolaire - Modèles de données SQLAlchemy
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Instance globale de la base de données (sera initialisée dans app.py)
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Modèle utilisateur pour enseignants et étudiants"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    current_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=True)
    current_class = db.relationship('SchoolClass', backref=db.backref('students', lazy='dynamic'))
    grades = db.relationship('Grade', backref='student', lazy=True, cascade='all, delete-orphan')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """Hache et stocke le mot de passe"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifie le mot de passe"""
        return check_password_hash(self.password, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class SchoolClass(db.Model):
    """Modèle pour les classes scolaires"""
    __tablename__ = 'school_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SchoolClass {self.name}>'

class Grade(db.Model):
    """Modèle pour les notes des étudiants"""
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    moy_cl = db.Column(db.Float, nullable=False)  # Moyenne de classe/continue
    n_compo = db.Column(db.Float, nullable=False) # Note de composition
    coef = db.Column(db.Integer, nullable=False)   # Coefficient
    appreciation = db.Column(db.String(100), nullable=True) # Appréciation par matière
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    period = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_subject_average(self):
        """Calcule la moyenne de la matière"""
        return (self.moy_cl + 2 * self.n_compo) / 3.0
    
    def __repr__(self):
        return f'<Grade {self.subject} for student {self.student_id}>'

class BulletinStructure(db.Model):
    """Modèle pour la structure des bulletins par classe"""
    __tablename__ = 'bulletin_structures'
    
    id = db.Column(db.Integer, primary_key=True)
    school_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), unique=True, nullable=False)
    school_class = db.relationship('SchoolClass', backref=db.backref('bulletin_structure', uselist=False, lazy='joined'))
    # Store subject lists as comma-separated strings
    subjects_part1 = db.Column(db.Text, nullable=False) # Matières principales
    subjects_part2 = db.Column(db.Text, nullable=False) # Matières secondaires
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
        return list(set(self.get_subjects_part1_list() + self.get_subjects_part2_list()))
    
    def __repr__(self):
        return f'<BulletinStructure for class {self.school_class.name if self.school_class else "Unknown"}>'