"""
Gestion Scolaire - Module de gestion de base de données
"""

import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash

# Instance globale de la base de données
db = SQLAlchemy()

def init_db(app=None):
    """Initialise la base de données avec les tables et données par défaut"""
    if app is None:
        from gestion_scolaire.app import create_app
        app = create_app()
    
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        
        # Créer les comptes par défaut
        from gestion_scolaire.models import User, SchoolClass, BulletinStructure, Subject
        
        # Compte Admin
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@ecole.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                first_name='Administrateur',
                last_name='Système'
            )
            db.session.add(admin)
            print("✅ Compte admin créé: admin / admin123")
        
        # Compte enseignant
        if not User.query.filter_by(username='teacher1').first():
            teacher = User(
                username='teacher1',
                email='teacher@ecole.com',
                password_hash=generate_password_hash('teacher123'),
                role='teacher',
                first_name='Jean',
                last_name='Professeur'
            )
            db.session.add(teacher)
            print("✅ Compte enseignant créé: teacher1 / teacher123")
        
        # Créer les classes par défaut
        default_classes = [
            "10e", "11e Sc", "11e L", "11e SES", "11e SS", 
            "12e SE", "12e EXP", "12e SEco", "12e SS"
        ]
        
        for class_name in default_classes:
            if not SchoolClass.query.filter_by(name=class_name).first():
                new_class = SchoolClass(name=class_name)
                db.session.add(new_class)
        
        # Créer les matières par défaut
        default_subjects = [
            ("Mathématiques", 5),
            ("Physique", 4),
            ("Chimie", 4),
            ("SVT", 3),
            ("Français", 4),
            ("Anglais", 3),
            ("Philosophie", 3),
            ("Histoire-Géographie", 3),
            ("E.C.M", 2),
            ("EPS", 2),
            ("Informatique", 2),
            ("Espagnol", 2),
            ("Allemand", 2),
        ]
        
        for subject_name, coef in default_subjects:
            if not Subject.query.filter_by(name=subject_name).first():
                new_subject = Subject(name=subject_name, coefficient=coef)
                db.session.add(new_subject)
        
        # Créer quelques structures de bulletin par défaut
        default_structures_data = [
            {
                'class_name_to_find': '12e EXP', 
                'subjects_part1': 'MATHS,PHYSIQUE,CHIMIE,PHILOSOPHIE,ANGLAIS,SVT',
                'subjects_part2': 'E.C.M,EPS,INFORMATIQUE,CONDUITE'
            },
            {
                'class_name_to_find': '10e',
                'subjects_part1': 'MATHS,FRANCAIS,ANGLAIS,HIST-GEO,PHYSIQUE-CHIMIE,SVT',
                'subjects_part2': 'E.C.M,EPS,LV2,ART PLASTIQUE'
            }
        ]
        
        for struct_data in default_structures_data:
            school_class_obj = SchoolClass.query.filter_by(name=struct_data['class_name_to_find']).first()
            if school_class_obj:
                if not BulletinStructure.query.filter_by(school_class_id=school_class_obj.id).first():
                    new_struct = BulletinStructure(
                        school_class_id=school_class_obj.id,
                        subjects_part1=struct_data['subjects_part1'],
                        subjects_part2=struct_data['subjects_part2']
                    )
                    db.session.add(new_struct)
        
        # Commit toutes les données
        db.session.commit()
        print("✅ Base de données initialisée avec succès")

def setup_database():
    """Point d'entrée CLI pour la configuration de la base de données"""
    print("🔧 Configuration de la base de données...")
    
    # Supprimer l'ancienne base si elle existe
    if os.path.exists('school.db'):
        os.remove('school.db')
        print("🗑️ Ancienne base de données supprimée")
    
    # Initialiser la nouvelle base
    init_db()
    print("✅ Configuration terminée!")

def reset_database():
    """Reset complet de la base de données"""
    if os.path.exists('school.db'):
        os.remove('school.db')
        print("🗑️ Base de données supprimée")
    
    init_db()
    print("🔄 Base de données réinitialisée")