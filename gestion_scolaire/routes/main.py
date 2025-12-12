"""
Routes principales - Dashboard et redirection selon rôle
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from gestion_scolaire.models import User, SchoolClass, Grade, Announcement, Attendance
from datetime import datetime, date

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Page d'accueil - Redirection vers login ou dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal - Redirection selon le rôle"""
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('teacher.dashboard'))
    elif current_user.role == 'student':
        return redirect(url_for('student.dashboard'))
    elif current_user.role == 'parent':
        return redirect(url_for('parent.dashboard'))
    else:
        return render_template('dashboard.html')


@main_bp.route('/announcements')
@login_required
def announcements():
    """Liste des annonces pour tous les utilisateurs"""
    # Filtrer les annonces selon le rôle
    query = Announcement.query.filter_by(is_active=True)
    
    if current_user.role == 'student':
        # Annonces pour tous, pour les étudiants, ou pour la classe de l'étudiant
        query = query.filter(
            (Announcement.target_audience == 'all') |
            (Announcement.target_audience == 'students') |
            (Announcement.target_class_id == current_user.current_class_id)
        )
    elif current_user.role == 'teacher':
        query = query.filter(
            (Announcement.target_audience == 'all') |
            (Announcement.target_audience == 'teachers')
        )
    elif current_user.role == 'parent':
        # Annonces pour tous, parents, ou classes des enfants
        children_class_ids = [child.current_class_id for child in current_user.children if child.current_class_id]
        query = query.filter(
            (Announcement.target_audience == 'all') |
            (Announcement.target_audience == 'parents') |
            (Announcement.target_class_id.in_(children_class_ids))
        )
    
    announcements = query.order_by(Announcement.created_at.desc()).all()
    return render_template('announcements.html', announcements=announcements)
