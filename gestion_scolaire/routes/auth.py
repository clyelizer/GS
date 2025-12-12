"""
Routes d'authentification - Login, Logout, Inscription, Profil
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from gestion_scolaire import db
from gestion_scolaire.models import User, SchoolClass, AuditLog

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Veuillez remplir tous les champs.', 'warning')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Votre compte a été désactivé. Contactez l\'administrateur.', 'danger')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            
            # Log de l'action
            audit = AuditLog(
                user_id=user.id,
                action='user_login',
                entity_type='User',
                entity_id=user.id,
                ip_address=request.remote_addr
            )
            db.session.add(audit)
            db.session.commit()
            
            flash(f'Bienvenue, {user.full_name}!', 'success')
            
            # Redirection selon le rôle
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        
        flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    # Log de l'action
    audit = AuditLog(
        user_id=current_user.id,
        action='user_logout',
        entity_type='User',
        entity_id=current_user.id,
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    logout_user()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    school_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', 'student')
        class_id = request.form.get('class_id')
        registration_code = request.form.get('registration_code', '').strip()
        
        # Validations
        errors = []
        
        if len(username) < 3:
            errors.append('Le nom d\'utilisateur doit contenir au moins 3 caractères.')
        
        if len(password) < 6:
            errors.append('Le mot de passe doit contenir au moins 6 caractères.')
        
        if password != confirm_password:
            errors.append('Les mots de passe ne correspondent pas.')
        
        if User.query.filter_by(username=username).first():
            errors.append('Ce nom d\'utilisateur existe déjà.')
        
        if email and User.query.filter_by(email=email).first():
            errors.append('Cette adresse email est déjà utilisée.')
        
        # Vérification du code d'inscription pour enseignant/admin
        from flask import current_app
        if role == 'teacher':
            if registration_code != current_app.config.get('TEACHER_CODE', 'PROF2025'):
                errors.append('Code d\'inscription enseignant invalide.')
        elif role == 'admin':
            if registration_code != current_app.config.get('ADMIN_CODE', 'ADMIN2025'):
                errors.append('Code d\'inscription administrateur invalide.')
        
        if role == 'student' and not class_id:
            errors.append('Veuillez sélectionner une classe.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html', school_classes=school_classes)
        
        # Création de l'utilisateur
        user = User(
            username=username,
            email=email if email else None,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        user.set_password(password)
        
        if role == 'student' and class_id:
            user.current_class_id = int(class_id)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Inscription réussie! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', school_classes=school_classes)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Page de profil utilisateur"""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        # Vérifier l'unicité de l'email
        if email and email != current_user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Cette adresse email est déjà utilisée.', 'danger')
                return render_template('auth/profile.html')
        
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.email = email if email else None
        current_user.phone = phone if phone else None
        current_user.address = address if address else None
        
        db.session.commit()
        flash('Profil mis à jour avec succès.', 'success')
    
    return render_template('auth/profile.html')


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Changement de mot de passe"""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not current_user.check_password(current_password):
        flash('Mot de passe actuel incorrect.', 'danger')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
        return redirect(url_for('auth.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Mot de passe modifié avec succès.', 'success')
    return redirect(url_for('auth.profile'))
