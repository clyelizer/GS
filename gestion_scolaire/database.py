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
        
        # Comptes enseignants
        if not User.query.filter_by(username='teacher1').first():
            teacher1 = User(
                username='teacher1',
                email='teacher1@ecole.com',
                password_hash=generate_password_hash('teacher123'),
                role='teacher',
                first_name='Jean',
                last_name='Professeur'
            )
            db.session.add(teacher1)
            print("✅ Compte enseignant créé: teacher1 / teacher123")
        
        if not User.query.filter_by(username='teacher2').first():
            teacher2 = User(
                username='teacher2',
                email='teacher2@ecole.com',
                password_hash=generate_password_hash('teacher123'),
                role='teacher',
                first_name='Marie',
                last_name='Dupont'
            )
            db.session.add(teacher2)
            print("✅ Compte enseignant créé: teacher2 / teacher123")
        
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
        
        # Commit les classes et matières d'abord
        db.session.commit()
        
        # Créer 2 étudiants avec des notes complètes pour bulletins
        from gestion_scolaire.models import Grade
        
        # Récupérer la classe 12e EXP
        classe_12exp = SchoolClass.query.filter_by(name='12e EXP').first()
        
        # Étudiant 1 - Alice Martin
        if not User.query.filter_by(username='student1').first():
            student1 = User(
                username='student1',
                email='alice.martin@ecole.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                first_name='Alice',
                last_name='Martin',
                current_class_id=classe_12exp.id if classe_12exp else None,
                matricule='2024001',
                date_of_birth=datetime(2007, 3, 15).date()
            )
            db.session.add(student1)
            db.session.flush()  # Pour obtenir l'ID
            
            # Ajouter des notes complètes pour période 1
            notes_alice_p1 = [
                ('Mathématiques', 5, 16, 18, 16.67),
                ('Physique', 4, 15, 17, 16.33),
                ('Chimie', 4, 14, 16, 15.33),
                ('Philosophie', 3, 13, 15, 14.33),
                ('Anglais', 3, 17, 18, 17.67),
                ('SVT', 3, 15, 16, 15.67),
            ]
            
            for subject_name, coef, moy_cl, n_compo, average in notes_alice_p1:
                grade = Grade(
                    student_id=student1.id,
                    subject_name=subject_name,
                    period='1',
                    moy_cl=moy_cl,
                    n_compo=n_compo,
                    average=average,
                    coef=coef,
                    appreciation='Excellent travail'
                )
                db.session.add(grade)
            
            print("✅ Étudiant créé: student1 / student123 (Alice Martin - 12e EXP)")
        
        # Étudiant 2 - Bob Durand
        if not User.query.filter_by(username='student2').first():
            student2 = User(
                username='student2',
                email='bob.durand@ecole.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                first_name='Bob',
                last_name='Durand',
                current_class_id=classe_12exp.id if classe_12exp else None,
                matricule='2024002',
                date_of_birth=datetime(2007, 8, 22).date()
            )
            db.session.add(student2)
            db.session.flush()  # Pour obtenir l'ID
            
            # Ajouter des notes complètes pour période 1
            notes_bob_p1 = [
                ('Mathématiques', 5, 14, 15, 14.67),
                ('Physique', 4, 13, 14, 13.67),
                ('Chimie', 4, 12, 13, 12.67),
                ('Philosophie', 3, 11, 12, 11.67),
                ('Anglais', 3, 15, 16, 15.67),
                ('SVT', 3, 13, 14, 13.67),
            ]
            
            for subject_name, coef, moy_cl, n_compo, average in notes_bob_p1:
                grade = Grade(
                    student_id=student2.id,
                    subject_name=subject_name,
                    period='1',
                    moy_cl=moy_cl,
                    n_compo=n_compo,
                    average=average,
                    coef=coef,
                    appreciation='Bon travail'
                )
                db.session.add(grade)
            
            print("✅ Étudiant créé: student2 / student123 (Bob Durand - 12e EXP)")
        
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