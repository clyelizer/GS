"""
Routes enseignant - Gestion des notes, présences et bulletins
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from functools import wraps
from gestion_scolaire import db
from gestion_scolaire.models import (
    User, SchoolClass, Subject, Grade, BulletinStructure,
    Attendance, Announcement, AuditLog, STANDARD_PERIODS
)
from gestion_scolaire.pdf_generator import generate_bulletin_pdf
from datetime import datetime, date
import tempfile
import os

teacher_bp = Blueprint('teacher', __name__)


def teacher_required(f):
    """Décorateur pour vérifier que l'utilisateur est enseignant"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['teacher', 'admin']:
            flash('Accès réservé aux enseignants.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# DASHBOARD
# ============================================

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    """Tableau de bord enseignant"""
    # Classes avec structure de bulletin
    classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    # Statistiques
    total_students = User.query.filter_by(role='student').count()
    total_grades = Grade.query.count()
    subjects = Subject.query.filter_by(is_active=True).all()
    
    # Annonces
    announcements = Announcement.query.filter_by(is_active=True).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()
    
    return render_template('teacher/dashboard.html', 
                          classes=classes,
                          total_students=total_students,
                          total_grades=total_grades,
                          subjects=subjects,
                          announcements=announcements,
                          periods=STANDARD_PERIODS)


# ============================================
# GESTION DES NOTES
# ============================================

@teacher_bp.route('/grades')
@login_required
@teacher_required
def grades():
    """Page de gestion des notes"""
    # Filtres
    class_id = request.args.get('class_id', type=int)
    period = request.args.get('period', '')
    
    # Classes avec structure de bulletin
    classes = SchoolClass.query.join(BulletinStructure).order_by(SchoolClass.name).all()
    
    students = []
    subjects = []
    
    if class_id:
        school_class = SchoolClass.query.get(class_id)
        if school_class and school_class.bulletin_structure:
            students = User.query.filter_by(role='student', current_class_id=class_id).order_by(User.last_name).all()
            subjects = school_class.bulletin_structure.get_all_subjects()
    
    return render_template('teacher/grades.html',
                          classes=classes,
                          students=students,
                          subjects=subjects,
                          periods=STANDARD_PERIODS,
                          selected_class_id=class_id,
                          selected_period=period)


@teacher_bp.route('/grades/add', methods=['POST'])
@login_required
@teacher_required
def add_grade():
    """Ajouter une note"""
    student_id = request.form.get('student_id', type=int)
    subject_name = request.form.get('subject', '').strip()
    period = request.form.get('period', '')
    
    # Permettre la saisie d'une autre matière
    if subject_name == 'Other':
        subject_name = request.form.get('other_subject_name', '').strip()
    
    try:
        moy_cl = float(request.form.get('moy_cl', 0))
        n_compo = float(request.form.get('n_compo', 0))
        coef = int(request.form.get('coef', 1))
    except (ValueError, TypeError):
        flash('Format de nombre invalide.', 'danger')
        return redirect(url_for('teacher.grades'))
    
    # Validations
    if not all([student_id, subject_name, period]):
        flash('Tous les champs sont requis.', 'danger')
        return redirect(url_for('teacher.grades'))
    
    if not (0 <= moy_cl <= 20 and 0 <= n_compo <= 20):
        flash('Les notes doivent être entre 0 et 20.', 'danger')
        return redirect(url_for('teacher.grades'))
    
    if coef < 1:
        flash('Le coefficient doit être au moins 1.', 'danger')
        return redirect(url_for('teacher.grades'))
    
    # Vérifier si une note existe déjà pour cette matière/période
    existing = Grade.query.filter_by(
        student_id=student_id,
        subject_name=subject_name,
        period=period
    ).first()
    
    if existing:
        # Mettre à jour la note existante
        existing.moy_cl = moy_cl
        existing.n_compo = n_compo
        existing.coef = coef
        existing.teacher_id = current_user.id
        existing.appreciation = Grade.get_appreciation(existing.average)
        existing.updated_at = datetime.utcnow()
        flash('Note mise à jour avec succès.', 'success')
    else:
        # Créer une nouvelle note
        grade = Grade(
            student_id=student_id,
            subject_name=subject_name,
            moy_cl=moy_cl,
            n_compo=n_compo,
            coef=coef,
            period=period,
            teacher_id=current_user.id
        )
        grade.appreciation = Grade.get_appreciation(grade.average)
        db.session.add(grade)
        flash('Note ajoutée avec succès.', 'success')
    
    db.session.commit()
    
    # Redirection avec les filtres
    return redirect(request.referrer or url_for('teacher.grades'))


@teacher_bp.route('/grades/<int:grade_id>/edit', methods=['POST'])
@login_required
@teacher_required
def edit_grade(grade_id):
    """Modifier une note"""
    grade = Grade.query.get_or_404(grade_id)
    
    try:
        grade.moy_cl = float(request.form.get('moy_cl', grade.moy_cl))
        grade.n_compo = float(request.form.get('n_compo', grade.n_compo))
        grade.coef = int(request.form.get('coef', grade.coef))
    except (ValueError, TypeError):
        flash('Format de nombre invalide.', 'danger')
        return redirect(url_for('teacher.grades'))
    
    grade.appreciation = Grade.get_appreciation(grade.average)
    grade.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('Note modifiée avec succès.', 'success')
    
    return redirect(request.referrer or url_for('teacher.grades'))


@teacher_bp.route('/grades/<int:grade_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_grade(grade_id):
    """Supprimer une note"""
    grade = Grade.query.get_or_404(grade_id)
    
    db.session.delete(grade)
    db.session.commit()
    
    flash('Note supprimée avec succès.', 'success')
    return redirect(request.referrer or url_for('teacher.grades'))


# ============================================
# VUE PAR ÉLÈVE
# ============================================

@teacher_bp.route('/student/<int:student_id>/grades')
@login_required
@teacher_required
def student_grades(student_id):
    """Voir les notes d'un élève spécifique"""
    student = User.query.get_or_404(student_id)
    
    if student.role != 'student':
        flash('Cet utilisateur n\'est pas un élève.', 'warning')
        return redirect(url_for('teacher.grades'))
    
    period = request.args.get('period', '')
    
    query = Grade.query.filter_by(student_id=student_id)
    if period:
        query = query.filter_by(period=period)
    
    grades = query.order_by(Grade.subject_name).all()
    
    # Calculer les statistiques
    if grades:
        total_weighted = sum(g.weighted_average for g in grades)
        total_coef = sum(g.coef for g in grades)
        general_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        general_average = 0
    
    return render_template('teacher/student_grades.html',
                          student=student,
                          grades=grades,
                          general_average=general_average,
                          periods=STANDARD_PERIODS,
                          selected_period=period)


# ============================================
# GÉNÉRATION DE BULLETINS
# ============================================

@teacher_bp.route('/bulletin/<int:student_id>/<period>')
@login_required
@teacher_required
def generate_bulletin(student_id, period):
    """Générer le bulletin PDF d'un élève"""
    student = User.query.get_or_404(student_id)
    
    if student.role != 'student':
        flash('Cet utilisateur n\'est pas un élève.', 'warning')
        return redirect(url_for('teacher.grades'))
    
    if not student.current_class:
        flash('Cet élève n\'est assigné à aucune classe.', 'warning')
        return redirect(url_for('teacher.grades'))
    
    # Récupérer la structure du bulletin
    structure = BulletinStructure.query.filter_by(school_class_id=student.current_class_id).first()
    if not structure:
        flash('Aucune structure de bulletin définie pour cette classe.', 'warning')
        return redirect(url_for('teacher.grades'))
    
    # Récupérer les notes
    grades = Grade.query.filter_by(student_id=student_id, period=period).all()
    grades_dict = {g.subject_name: g for g in grades}
    
    # Préparer les données pour le PDF
    student_data = {
        'name': student.full_name,
        'class': student.current_class.name,
        'period': period,
        'school_name': structure.school_name or 'Lycée Michel ALLAIRE'
    }
    
    # Construire les tableaux de notes
    subjects_part1 = structure.get_subjects_part1_list()
    subjects_part2 = structure.get_subjects_part2_list()
    
    def build_grades_table(subjects):
        table = []
        for subject in subjects:
            grade = grades_dict.get(subject)
            if grade:
                row = {
                    'subject': subject,
                    'moy_cl': grade.moy_cl,
                    'n_compo': grade.n_compo,
                    'coef': grade.coef,
                    'mg': grade.average,
                    'moy_coef': grade.weighted_average,
                    'appreciation': grade.appreciation or grade.auto_appreciation()
                }
            else:
                row = {
                    'subject': subject,
                    'moy_cl': '-',
                    'n_compo': '-',
                    'coef': '-',
                    'mg': '-',
                    'moy_coef': '-',
                    'appreciation': '-'
                }
            table.append(row)
        return table
    
    grades_part1 = build_grades_table(subjects_part1)
    grades_part2 = build_grades_table(subjects_part2)
    
    # Calculer le résumé
    valid_grades = [g for g in grades if g.moy_cl is not None and g.n_compo is not None]
    
    if valid_grades:
        total_weighted = sum(g.weighted_average for g in valid_grades)
        total_coef = sum(g.coef for g in valid_grades)
        general_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        total_weighted = 0
        total_coef = 0
        general_average = 0
    
    summary_data = {
        'total_points': round(total_weighted, 2),
        'total_coef': total_coef,
        'general_average': general_average,
        'appreciation': Grade.get_appreciation(general_average) if general_average > 0 else '-',
        'rank': '-',  # À implémenter si nécessaire
        'class_average': '-'  # À implémenter si nécessaire
    }
    
    # Générer le PDF
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            generate_bulletin_pdf(tmp.name, student_data, grades_part1, grades_part2, summary_data)
            
            return send_file(
                tmp.name,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'bulletin_{student.username}_{period.replace(" ", "_")}.pdf'
            )
    except Exception as e:
        flash(f'Erreur lors de la génération du bulletin: {str(e)}', 'danger')
        return redirect(url_for('teacher.student_grades', student_id=student_id))


# ============================================
# GESTION DES PRÉSENCES
# ============================================

@teacher_bp.route('/attendance')
@login_required
@teacher_required
def attendance():
    """Page de gestion des présences"""
    class_id = request.args.get('class_id', type=int)
    date_str = request.args.get('date', date.today().isoformat())
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()
    
    classes = SchoolClass.query.order_by(SchoolClass.name).all()
    students = []
    attendance_records = {}
    
    if class_id:
        students = User.query.filter_by(role='student', current_class_id=class_id).order_by(User.last_name).all()
        
        # Récupérer les présences existantes
        records = Attendance.query.filter_by(class_id=class_id, date=selected_date).all()
        attendance_records = {r.student_id: r for r in records}
    
    return render_template('teacher/attendance.html',
                          classes=classes,
                          students=students,
                          attendance_records=attendance_records,
                          selected_class_id=class_id,
                          selected_date=selected_date)


@teacher_bp.route('/attendance/save', methods=['POST'])
@login_required
@teacher_required
def save_attendance():
    """Enregistrer les présences"""
    class_id = request.form.get('class_id', type=int)
    date_str = request.form.get('date')
    
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Date invalide.', 'danger')
        return redirect(url_for('teacher.attendance'))
    
    students = User.query.filter_by(role='student', current_class_id=class_id).all()
    
    for student in students:
        status = request.form.get(f'status_{student.id}', 'present')
        reason = request.form.get(f'reason_{student.id}', '').strip()
        
        # Chercher un enregistrement existant
        record = Attendance.query.filter_by(
            student_id=student.id,
            class_id=class_id,
            date=attendance_date
        ).first()
        
        if record:
            record.status = status
            record.reason = reason if reason else None
        else:
            record = Attendance(
                student_id=student.id,
                class_id=class_id,
                date=attendance_date,
                status=status,
                reason=reason if reason else None,
                recorded_by=current_user.id
            )
            db.session.add(record)
    
    db.session.commit()
    flash('Présences enregistrées avec succès.', 'success')
    
    return redirect(url_for('teacher.attendance', class_id=class_id, date=date_str))


# ============================================
# LISTE DES CLASSES
# ============================================

@teacher_bp.route('/classes')
@login_required
@teacher_required
def classes():
    """Liste des classes"""
    classes = SchoolClass.query.order_by(SchoolClass.name).all()
    return render_template('teacher/classes.html', classes=classes)


@teacher_bp.route('/classes/<int:class_id>')
@login_required
@teacher_required
def class_detail(class_id):
    """Détail d'une classe"""
    school_class = SchoolClass.query.get_or_404(class_id)
    students = User.query.filter_by(role='student', current_class_id=class_id).order_by(User.last_name).all()
    
    return render_template('teacher/class_detail.html',
                          school_class=school_class,
                          students=students)
