"""
Routes administrateur - Gestion complète du système
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from gestion_scolaire import db
from gestion_scolaire.models import (
    User, SchoolClass, Subject, Grade, BulletinStructure,
    Announcement, AcademicYear, Attendance, AuditLog, STANDARD_PERIODS
)
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# DASHBOARD
# ============================================

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    stats = {
        'total_students': User.query.filter_by(role='student').count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_parents': User.query.filter_by(role='parent').count(),
        'total_classes': SchoolClass.query.count(),
        'total_subjects': Subject.query.count(),
        'total_grades': Grade.query.count(),
        'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
        'recent_announcements': Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    }
    return render_template('admin/dashboard.html', stats=stats)


# ============================================
# GESTION DES UTILISATEURS
# ============================================

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Liste des utilisateurs"""
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '')
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, role_filter=role_filter, search=search)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Ajouter un utilisateur"""
    school_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', 'student')
        class_id = request.form.get('class_id')
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà.', 'danger')
            return render_template('admin/user_form.html', school_classes=school_classes, action='add')
        
        user = User(
            username=username,
            email=email if email else None,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone=phone if phone else None
        )
        user.set_password(password)
        
        if role == 'student' and class_id:
            user.current_class_id = int(class_id)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Utilisateur "{username}" créé avec succès.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', school_classes=school_classes, action='add')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Modifier un utilisateur"""
    user = User.query.get_or_404(user_id)
    school_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.email = request.form.get('email', '').strip() or None
        user.phone = request.form.get('phone', '').strip() or None
        user.role = request.form.get('role', user.role)
        user.is_active = request.form.get('is_active') == 'on'
        
        class_id = request.form.get('class_id')
        if user.role == 'student' and class_id:
            user.current_class_id = int(class_id)
        else:
            user.current_class_id = None
        
        # Changement de mot de passe optionnel
        new_password = request.form.get('new_password', '')
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash('Utilisateur modifié avec succès.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', user=user, school_classes=school_classes, action='edit')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Supprimer un utilisateur"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin.users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Utilisateur "{username}" supprimé avec succès.', 'success')
    return redirect(url_for('admin.users'))


# ============================================
# GESTION DES CLASSES
# ============================================

@admin_bp.route('/classes')
@login_required
@admin_required
def classes():
    """Liste des classes"""
    classes = SchoolClass.query.order_by(SchoolClass.name).all()
    return render_template('admin/classes.html', classes=classes)


@admin_bp.route('/classes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_class():
    """Ajouter une classe"""
    teachers = User.query.filter_by(role='teacher').order_by(User.last_name).all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        level = request.form.get('level', '').strip()
        section = request.form.get('section', '').strip()
        description = request.form.get('description', '').strip()
        capacity = request.form.get('capacity', 50)
        main_teacher_id = request.form.get('main_teacher_id')
        
        if SchoolClass.query.filter_by(name=name).first():
            flash('Une classe avec ce nom existe déjà.', 'danger')
            return render_template('admin/class_form.html', teachers=teachers, action='add')
        
        school_class = SchoolClass(
            name=name,
            level=level if level else None,
            section=section if section else None,
            description=description if description else None,
            capacity=int(capacity) if capacity else 50,
            main_teacher_id=int(main_teacher_id) if main_teacher_id else None
        )
        
        db.session.add(school_class)
        db.session.commit()
        
        flash(f'Classe "{name}" créée avec succès.', 'success')
        return redirect(url_for('admin.classes'))
    
    return render_template('admin/class_form.html', teachers=teachers, action='add')


@admin_bp.route('/classes/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_class(class_id):
    """Modifier une classe"""
    school_class = SchoolClass.query.get_or_404(class_id)
    teachers = User.query.filter_by(role='teacher').order_by(User.last_name).all()
    
    if request.method == 'POST':
        school_class.name = request.form.get('name', '').strip()
        school_class.level = request.form.get('level', '').strip() or None
        school_class.section = request.form.get('section', '').strip() or None
        school_class.description = request.form.get('description', '').strip() or None
        school_class.capacity = int(request.form.get('capacity', 50))
        main_teacher_id = request.form.get('main_teacher_id')
        school_class.main_teacher_id = int(main_teacher_id) if main_teacher_id else None
        
        db.session.commit()
        flash('Classe modifiée avec succès.', 'success')
        return redirect(url_for('admin.classes'))
    
    return render_template('admin/class_form.html', school_class=school_class, teachers=teachers, action='edit')


@admin_bp.route('/classes/<int:class_id>/students')
@login_required
@admin_required
def class_students(class_id):
    """Liste des élèves d'une classe"""
    school_class = SchoolClass.query.get_or_404(class_id)
    students = User.query.filter_by(role='student', current_class_id=class_id).order_by(User.last_name).all()
    return render_template('admin/class_students.html', school_class=school_class, students=students)


@admin_bp.route('/classes/<int:class_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_class(class_id):
    """Supprimer une classe"""
    school_class = SchoolClass.query.get_or_404(class_id)
    
    # Vérifier si la classe a des élèves
    if school_class.students.count() > 0:
        flash('Impossible de supprimer une classe avec des élèves.', 'danger')
        return redirect(url_for('admin.classes'))
    
    name = school_class.name
    db.session.delete(school_class)
    db.session.commit()
    
    flash(f'Classe "{name}" supprimée avec succès.', 'success')
    return redirect(url_for('admin.classes'))


# ============================================
# GESTION DES MATIÈRES
# ============================================

@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects():
    """Liste des matières"""
    subjects = Subject.query.order_by(Subject.category, Subject.name).all()
    return render_template('admin/subjects.html', subjects=subjects)


@admin_bp.route('/subjects/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_subject():
    """Ajouter une matière"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        default_coef = request.form.get('default_coef', 1)
        
        if Subject.query.filter_by(code=code).first():
            flash('Une matière avec ce code existe déjà.', 'danger')
            return render_template('admin/subject_form.html', action='add')
        
        subject = Subject(
            name=name,
            code=code,
            category=category if category else None,
            description=description if description else None,
            default_coef=int(default_coef) if default_coef else 1
        )
        
        db.session.add(subject)
        db.session.commit()
        
        flash(f'Matière "{name}" créée avec succès.', 'success')
        return redirect(url_for('admin.subjects'))
    
    return render_template('admin/subject_form.html', action='add')


@admin_bp.route('/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_subject(subject_id):
    """Modifier une matière"""
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'POST':
        subject.name = request.form.get('name', '').strip()
        subject.code = request.form.get('code', '').strip().upper()
        subject.category = request.form.get('category', '').strip() or None
        subject.description = request.form.get('description', '').strip() or None
        subject.default_coef = int(request.form.get('default_coef', 1))
        subject.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Matière modifiée avec succès.', 'success')
        return redirect(url_for('admin.subjects'))
    
    return render_template('admin/subject_form.html', subject=subject, action='edit')


@admin_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subject(subject_id):
    """Supprimer une matière"""
    subject = Subject.query.get_or_404(subject_id)
    name = subject.name
    
    db.session.delete(subject)
    db.session.commit()
    
    flash(f'Matière "{name}" supprimée avec succès.', 'success')
    return redirect(url_for('admin.subjects'))


# ============================================
# GESTION DES STRUCTURES DE BULLETIN
# ============================================

@admin_bp.route('/bulletin-structures')
@login_required
@admin_required
def bulletin_structures():
    """Liste des structures de bulletin"""
    structures = BulletinStructure.query.join(SchoolClass).order_by(SchoolClass.name).all()
    classes_without_structure = SchoolClass.query.filter(
        ~SchoolClass.id.in_([s.school_class_id for s in structures])
    ).order_by(SchoolClass.name).all()
    
    return render_template('admin/bulletin_structures.html', 
                          structures=structures, 
                          classes_without_structure=classes_without_structure)


@admin_bp.route('/bulletin-structures/add', methods=['POST'])
@login_required
@admin_required
def add_bulletin_structure():
    """Ajouter une structure de bulletin"""
    school_class_id = request.form.get('school_class_id')
    subjects_part1 = request.form.get('subjects_part1', '').strip()
    subjects_part2 = request.form.get('subjects_part2', '').strip()
    
    if not school_class_id or not subjects_part1 or not subjects_part2:
        flash('Tous les champs sont requis.', 'danger')
        return redirect(url_for('admin.bulletin_structures'))
    
    # Vérifier si une structure existe déjà pour cette classe
    existing = BulletinStructure.query.filter_by(school_class_id=int(school_class_id)).first()
    if existing:
        flash('Une structure existe déjà pour cette classe.', 'warning')
        return redirect(url_for('admin.bulletin_structures'))
    
    structure = BulletinStructure(
        school_class_id=int(school_class_id),
        subjects_part1=subjects_part1,
        subjects_part2=subjects_part2
    )
    
    db.session.add(structure)
    db.session.commit()
    
    flash('Structure de bulletin créée avec succès.', 'success')
    return redirect(url_for('admin.bulletin_structures'))


@admin_bp.route('/bulletin-structures/<int:structure_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_bulletin_structure(structure_id):
    """Modifier une structure de bulletin"""
    structure = BulletinStructure.query.get_or_404(structure_id)
    
    structure.subjects_part1 = request.form.get('subjects_part1', '').strip()
    structure.subjects_part2 = request.form.get('subjects_part2', '').strip()
    
    db.session.commit()
    flash('Structure de bulletin modifiée avec succès.', 'success')
    return redirect(url_for('admin.bulletin_structures'))


@admin_bp.route('/bulletin-structures/<int:structure_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_bulletin_structure(structure_id):
    """Supprimer une structure de bulletin"""
    structure = BulletinStructure.query.get_or_404(structure_id)
    
    db.session.delete(structure)
    db.session.commit()
    
    flash('Structure de bulletin supprimée avec succès.', 'success')
    return redirect(url_for('admin.bulletin_structures'))


# ============================================
# GESTION DES ANNONCES
# ============================================

@admin_bp.route('/announcements')
@login_required
@admin_required
def announcements():
    """Liste des annonces"""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=announcements)


@admin_bp.route('/announcements/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_announcement():
    """Ajouter une annonce"""
    school_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        target_audience = request.form.get('target_audience', 'all')
        target_class_id = request.form.get('target_class_id')
        priority = request.form.get('priority', 'normal')
        
        announcement = Announcement(
            title=title,
            content=content,
            target_audience=target_audience,
            target_class_id=int(target_class_id) if target_class_id else None,
            priority=priority,
            author_id=current_user.id
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Annonce créée avec succès.', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/announcement_form.html', school_classes=school_classes, action='add')


@admin_bp.route('/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_announcement(announcement_id):
    """Modifier une annonce"""
    announcement = Announcement.query.get_or_404(announcement_id)
    school_classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    if request.method == 'POST':
        announcement.title = request.form.get('title', '').strip()
        announcement.content = request.form.get('content', '').strip()
        announcement.target_audience = request.form.get('target_audience', 'all')
        target_class_id = request.form.get('target_class_id')
        announcement.target_class_id = int(target_class_id) if target_class_id else None
        announcement.priority = request.form.get('priority', 'normal')
        announcement.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Annonce modifiée avec succès.', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/announcement_form.html', announcement=announcement, 
                          school_classes=school_classes, action='edit')


@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    """Supprimer une annonce"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    db.session.delete(announcement)
    db.session.commit()
    
    flash('Annonce supprimée avec succès.', 'success')
    return redirect(url_for('admin.announcements'))


# ============================================
# ANNÉES SCOLAIRES
# ============================================

@admin_bp.route('/academic-years')
@login_required
@admin_required
def academic_years():
    """Gestion des années scolaires"""
    years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    return render_template('admin/academic_years.html', years=years)


@admin_bp.route('/academic-years/add', methods=['POST'])
@login_required
@admin_required
def add_academic_year():
    """Ajouter une année scolaire"""
    name = request.form.get('name', '').strip()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    is_current = request.form.get('is_current') == 'on'
    
    if AcademicYear.query.filter_by(name=name).first():
        flash('Cette année scolaire existe déjà.', 'danger')
        return redirect(url_for('admin.academic_years'))
    
    # Si c'est l'année courante, désactiver les autres
    if is_current:
        AcademicYear.query.update({AcademicYear.is_current: False})
    
    year = AcademicYear(
        name=name,
        start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
        end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
        is_current=is_current
    )
    
    db.session.add(year)
    db.session.commit()
    
    flash(f'Année scolaire "{name}" créée avec succès.', 'success')
    return redirect(url_for('admin.academic_years'))


@admin_bp.route('/academic-years/<int:year_id>/set-current', methods=['POST'])
@login_required
@admin_required
def set_current_year(year_id):
    """Définir l'année scolaire courante"""
    # Désactiver toutes les années
    AcademicYear.query.update({AcademicYear.is_current: False})
    
    # Activer l'année sélectionnée
    year = AcademicYear.query.get_or_404(year_id)
    year.is_current = True
    
    db.session.commit()
    flash(f'Année scolaire "{year.name}" définie comme courante.', 'success')
    return redirect(url_for('admin.academic_years'))


# ============================================
# JOURNAL D'AUDIT
# ============================================

@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """Journal des actions"""
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('admin/audit_logs.html', logs=logs)
