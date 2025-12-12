"""
Routes élève - Consultation des notes et bulletins
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from functools import wraps
from gestion_scolaire import db
from gestion_scolaire.models import (
    User, SchoolClass, Grade, BulletinStructure, Attendance, Announcement, STANDARD_PERIODS
)
from gestion_scolaire.pdf_generator import generate_bulletin_pdf
from datetime import datetime
import tempfile

student_bp = Blueprint('student', __name__)


def student_required(f):
    """Décorateur pour vérifier que l'utilisateur est élève"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Accès réservé aux élèves.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Tableau de bord élève"""
    # Notes récentes
    recent_grades = Grade.query.filter_by(student_id=current_user.id)\
        .order_by(Grade.created_at.desc()).limit(5).all()
    
    # Calculer la moyenne générale
    all_grades = Grade.query.filter_by(student_id=current_user.id).all()
    if all_grades:
        total_weighted = sum(g.weighted_average for g in all_grades)
        total_coef = sum(g.coef for g in all_grades)
        overall_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        overall_average = 0
    
    # Calculer le rang
    rank = None
    class_size = 0
    if current_user.current_class:
        class_students = User.query.filter_by(current_class_id=current_user.current_class_id, role='student').all()
        class_size = len(class_students)
        
        # Calculer les moyennes de tous les élèves
        student_averages = []
        for s in class_students:
            s_grades = Grade.query.filter_by(student_id=s.id).all()
            if s_grades:
                s_weighted = sum(g.weighted_average for g in s_grades)
                s_coef = sum(g.coef for g in s_grades)
                s_avg = s_weighted / s_coef if s_coef > 0 else 0
                student_averages.append((s.id, s_avg))
        
        # Trier et trouver le rang
        student_averages.sort(key=lambda x: x[1], reverse=True)
        for i, (sid, _) in enumerate(student_averages, 1):
            if sid == current_user.id:
                rank = i
                break
    
    # Nombre de matières notées
    subjects_count = len(set(g.subject_name for g in all_grades))
    
    # Taux de présence
    attendance_records = Attendance.query.filter_by(student_id=current_user.id).all()
    if attendance_records:
        present_count = sum(1 for a in attendance_records if a.status == 'present')
        attendance_rate = (present_count / len(attendance_records)) * 100
    else:
        attendance_rate = 100
    
    # Notes par matière
    grades_by_subject = {}
    for grade in all_grades:
        if grade.subject_name not in grades_by_subject:
            grades_by_subject[grade.subject_name] = {'coef': grade.coef}
        try:
            period_num = int(grade.period) if grade.period.isdigit() else 1
        except:
            period_num = 1
        grades_by_subject[grade.subject_name][period_num] = grade.average
    
    # Annonces
    announcements = Announcement.query.filter(
        Announcement.is_active == True,
        (Announcement.target_audience == 'all') | (Announcement.target_audience == 'students')
    ).order_by(Announcement.created_at.desc()).limit(5).all()
    
    return render_template('student/dashboard.html',
                          recent_grades=recent_grades,
                          overall_average=overall_average,
                          rank=rank,
                          class_size=class_size,
                          subjects_count=subjects_count,
                          attendance_rate=attendance_rate,
                          grades_by_subject=grades_by_subject,
                          announcements=announcements,
                          periods=STANDARD_PERIODS)


@student_bp.route('/grades')
@login_required
@student_required
def grades():
    """Voir mes notes"""
    selected_period = request.args.get('period', type=int)
    
    query = Grade.query.filter_by(student_id=current_user.id)
    if selected_period:
        query = query.filter_by(period=str(selected_period))
    
    grades_list = query.order_by(Grade.subject_name).all()
    
    # Calculer la moyenne générale
    if grades_list:
        total_weighted = sum(g.weighted_average for g in grades_list)
        total_coef = sum(g.coef for g in grades_list)
        overall_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        overall_average = 0
    
    return render_template('student/grades.html',
                          grades=grades_list,
                          overall_average=overall_average,
                          selected_period=selected_period)


@student_bp.route('/bulletin')
@login_required
@student_required
def bulletin():
    """Voir mon bulletin"""
    selected_period = request.args.get('period', 1, type=int)
    
    # Récupérer les notes
    grades_list = Grade.query.filter_by(student_id=current_user.id, period=str(selected_period)).all()
    
    # Vérifier si le bulletin est disponible
    bulletin_available = len(grades_list) > 0
    
    # Calculer la moyenne
    if grades_list:
        total_weighted = sum(g.weighted_average for g in grades_list)
        total_coef = sum(g.coef for g in grades_list)
        overall_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        overall_average = 0
        total_coef = 0
    
    # Statuts des bulletins par période
    bulletins_status = {}
    for p in [1, 2, 3]:
        p_grades = Grade.query.filter_by(student_id=current_user.id, period=str(p)).count()
        bulletins_status[p] = p_grades > 0
    
    return render_template('student/bulletin.html',
                          grades=grades_list,
                          overall_average=overall_average,
                          total_coef=total_coef,
                          selected_period=selected_period,
                          bulletin_available=bulletin_available,
                          bulletins_status=bulletins_status,
                          subjects_part1=grades_list,
                          subjects_part2=[])


@student_bp.route('/bulletin/download')
@login_required
@student_required
def download_bulletin():
    """Télécharger mon bulletin en PDF"""
    period = request.args.get('period', 1, type=int)
    
    if not current_user.current_class:
        flash('Vous n\'êtes assigné à aucune classe.', 'warning')
        return redirect(url_for('student.grades'))
    
    # Récupérer les notes
    grades_list = Grade.query.filter_by(student_id=current_user.id, period=str(period)).all()
    
    if not grades_list:
        flash('Aucune note disponible pour cette période.', 'warning')
        return redirect(url_for('student.bulletin', period=period))
    
    # Calculer la moyenne
    total_weighted = sum(g.weighted_average for g in grades_list)
    total_coef = sum(g.coef for g in grades_list)
    general_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    
    # Préparer les données pour le PDF
    student_data = {
        'name': current_user.full_name,
        'matricule': current_user.matricule or '-',
        'class': current_user.current_class.name,
        'period': period,
        'school_name': 'Lycée Michel ALLAIRE'
    }
    
    grades_data = []
    for g in grades_list:
        grades_data.append({
            'subject': g.subject_name,
            'moy_cl': g.moy_cl,
            'n_compo': g.n_compo,
            'coef': g.coef,
            'mg': g.average,
            'appreciation': g.appreciation or g.auto_appreciation()
        })
    
    summary_data = {
        'total_points': round(total_weighted, 2),
        'total_coef': total_coef,
        'general_average': general_average,
        'appreciation': Grade.get_appreciation(general_average)
    }
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            generate_bulletin_pdf(tmp.name, student_data, grades_data, [], summary_data)
            
            return send_file(
                tmp.name,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'bulletin_{current_user.username}_P{period}.pdf'
            )
    except Exception as e:
        flash(f'Erreur lors de la génération du bulletin: {str(e)}', 'danger')
        return redirect(url_for('student.bulletin', period=period))


@student_bp.route('/attendance')
@login_required
@student_required
def attendance():
    """Voir mes présences"""
    selected_month = request.args.get('month', type=int)
    selected_status = request.args.get('status', '')
    
    query = Attendance.query.filter_by(student_id=current_user.id)
    
    if selected_month:
        query = query.filter(db.extract('month', Attendance.date) == selected_month)
    
    if selected_status:
        query = query.filter_by(status=selected_status)
    
    attendance_records = query.order_by(Attendance.date.desc()).all()
    
    # Statistiques globales
    all_records = Attendance.query.filter_by(student_id=current_user.id).all()
    stats = {
        'total': len(all_records),
        'present': sum(1 for r in all_records if r.status == 'present'),
        'absent': sum(1 for r in all_records if r.status == 'absent'),
        'late': sum(1 for r in all_records if r.status == 'late'),
        'excused': sum(1 for r in all_records if r.status == 'excused')
    }
    
    if stats['total'] > 0:
        attendance_rate = round((stats['present'] / stats['total']) * 100, 1)
    else:
        attendance_rate = 100
    
    return render_template('student/attendance.html',
                          attendance_records=attendance_records,
                          stats=stats,
                          attendance_rate=attendance_rate,
                          selected_month=selected_month,
                          selected_status=selected_status)
