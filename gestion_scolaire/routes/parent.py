"""
Routes parent - Suivi des enfants
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from functools import wraps
from gestion_scolaire import db
from gestion_scolaire.models import (
    User, Grade, Attendance, Message, Announcement, STANDARD_PERIODS
)
from gestion_scolaire.pdf_generator import generate_bulletin_pdf
from datetime import datetime
from io import BytesIO

parent_bp = Blueprint('parent', __name__)


def parent_required(f):
    """Décorateur pour vérifier que l'utilisateur est parent"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'parent':
            flash('Accès réservé aux parents.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@parent_bp.route('/dashboard')
@login_required
@parent_required
def dashboard():
    """Tableau de bord parent"""
    children = current_user.children
    
    children_data = []
    for child in children:
        # Notes récentes
        recent_grades = Grade.query.filter_by(student_id=child.id)\
            .order_by(Grade.created_at.desc()).limit(3).all()
        
        # Moyenne générale
        all_grades = Grade.query.filter_by(student_id=child.id).all()
        if all_grades:
            total_weighted = sum(g.weighted_average for g in all_grades)
            total_coef = sum(g.coef for g in all_grades)
            avg = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
        else:
            avg = 0
        
        # Rang dans la classe
        rank = None
        class_size = 0
        if child.school_class:
            class_students = User.query.filter_by(school_class_id=child.school_class_id, role='student').all()
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
                if sid == child.id:
                    rank = i
                    break
        
        child.average = avg
        child.rank = rank
        child.class_size = class_size
        children_data.append(child)
    
    # Annonces
    announcements = Announcement.query.filter(
        Announcement.is_active == True,
        (Announcement.target_role == 'all') | (Announcement.target_role == 'parent')
    ).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(5).all()
    
    # Messages non lus
    unread_messages = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    
    # Notes récentes de tous les enfants
    recent_grades = []
    for child in children:
        child_grades = Grade.query.filter_by(student_id=child.id)\
            .order_by(Grade.updated_at.desc()).limit(3).all()
        recent_grades.extend(child_grades)
    recent_grades.sort(key=lambda x: x.updated_at if x.updated_at else x.created_at, reverse=True)
    
    return render_template('parent/dashboard.html',
                          children=children_data,
                          announcements=announcements,
                          unread_messages=unread_messages,
                          recent_grades=recent_grades[:10])


@parent_bp.route('/children')
@login_required
@parent_required
def children():
    """Liste des enfants"""
    children_list = current_user.children
    
    children_data = []
    global_avg_sum = 0
    global_attendance_sum = 0
    count_with_avg = 0
    count_with_attendance = 0
    
    for child in children_list:
        # Moyenne
        all_grades = Grade.query.filter_by(student_id=child.id).all()
        if all_grades:
            total_weighted = sum(g.weighted_average for g in all_grades)
            total_coef = sum(g.coef for g in all_grades)
            avg = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
            global_avg_sum += avg
            count_with_avg += 1
        else:
            avg = None
        
        # Rang
        rank = None
        class_size = 0
        if child.school_class:
            class_students = User.query.filter_by(school_class_id=child.school_class_id, role='student').all()
            class_size = len(class_students)
        
        # Présence
        all_attendance = Attendance.query.filter_by(student_id=child.id).all()
        if all_attendance:
            present_count = sum(1 for a in all_attendance if a.status == 'present')
            attendance_rate = (present_count / len(all_attendance)) * 100
            global_attendance_sum += attendance_rate
            count_with_attendance += 1
        else:
            attendance_rate = None
        
        child.average = avg
        child.rank = rank
        child.class_size = class_size
        child.attendance_rate = attendance_rate
        children_data.append(child)
    
    global_average = global_avg_sum / count_with_avg if count_with_avg > 0 else None
    global_attendance = global_attendance_sum / count_with_attendance if count_with_attendance > 0 else None
    
    return render_template('parent/children.html',
                          children=children_data,
                          global_average=global_average,
                          global_attendance=global_attendance)


@parent_bp.route('/child/<int:child_id>/grades')
@login_required
@parent_required
def child_grades(child_id):
    """Voir les notes d'un enfant"""
    child = User.query.get_or_404(child_id)
    
    # Vérifier que c'est bien un enfant du parent
    if child not in current_user.children:
        flash('Vous n\'êtes pas autorisé à voir ces informations.', 'danger')
        return redirect(url_for('parent.dashboard'))
    
    period = request.args.get('period', '')
    
    query = Grade.query.filter_by(student_id=child_id)
    if period:
        query = query.filter_by(period=period)
    
    grades = query.order_by(Grade.subject_name).all()
    
    # Calculer la moyenne
    if grades:
        total_weighted = sum(g.weighted_average for g in grades)
        total_coef = sum(g.coef for g in grades)
        general_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        general_average = 0
    
    return render_template('parent/child_grades.html',
                          child=child,
                          grades=grades,
                          general_average=general_average,
                          periods=STANDARD_PERIODS,
                          selected_period=period)


@parent_bp.route('/child/<int:child_id>/attendance')
@login_required
@parent_required
def child_attendance(child_id):
    """Voir les présences d'un enfant"""
    child = User.query.get_or_404(child_id)
    
    if child not in current_user.children:
        flash('Vous n\'êtes pas autorisé à voir ces informations.', 'danger')
        return redirect(url_for('parent.dashboard'))
    
    records = Attendance.query.filter_by(student_id=child_id)\
        .order_by(Attendance.date.desc()).all()
    
    stats = {
        'total': len(records),
        'present': sum(1 for r in records if r.status == 'present'),
        'absent': sum(1 for r in records if r.status == 'absent'),
        'late': sum(1 for r in records if r.status == 'late'),
        'excused': sum(1 for r in records if r.status == 'excused')
    }
    
    if stats['total'] > 0:
        stats['presence_rate'] = round((stats['present'] / stats['total']) * 100, 1)
    else:
        stats['presence_rate'] = 100
    
    return render_template('parent/child_attendance.html',
                          child=child,
                          records=records,
                          stats=stats)


@parent_bp.route('/child/<int:child_id>/bulletin')
@login_required
@parent_required
def child_bulletin(child_id):
    """Voir/télécharger le bulletin d'un enfant"""
    child = User.query.get_or_404(child_id)
    
    if child not in current_user.children:
        flash('Vous n\'êtes pas autorisé à voir ces informations.', 'danger')
        return redirect(url_for('parent.dashboard'))
    
    period = request.args.get('period', 1, type=int)
    download = request.args.get('download', False, type=bool)
    
    grades = Grade.query.filter_by(student_id=child_id, period=period).all()
    
    # Calculer la moyenne
    if grades:
        total_weighted = sum(g.weighted_average for g in grades)
        total_coef = sum(g.coef for g in grades)
        overall_average = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
    else:
        overall_average = 0
    
    if download and grades:
        # Générer le PDF
        pdf_buffer = generate_bulletin_pdf(child, grades, period)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'bulletin_{child.full_name}_{period}.pdf'
        )
    
    return render_template('parent/child_bulletin.html',
                          child=child,
                          grades=grades,
                          overall_average=overall_average,
                          selected_period=period,
                          periods=STANDARD_PERIODS)


@parent_bp.route('/messages')
@login_required
@parent_required
def messages():
    """Messagerie"""
    received = Message.query.filter_by(recipient_id=current_user.id)\
        .order_by(Message.created_at.desc()).all()
    sent = Message.query.filter_by(sender_id=current_user.id)\
        .order_by(Message.created_at.desc()).all()
    
    return render_template('parent/messages.html', received=received, sent=sent)


@parent_bp.route('/messages/compose', methods=['GET', 'POST'])
@login_required
@parent_required
def compose_message():
    """Composer un message"""
    # Destinataires possibles: enseignants et admin
    recipients = User.query.filter(User.role.in_(['teacher', 'admin'])).order_by(User.last_name).all()
    
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        
        if not all([recipient_id, subject, content]):
            flash('Tous les champs sont requis.', 'danger')
            return render_template('parent/compose_message.html', recipients=recipients)
        
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('Message envoyé avec succès.', 'success')
        return redirect(url_for('parent.messages'))
    
    return render_template('parent/compose_message.html', recipients=recipients)


@parent_bp.route('/messages/<int:message_id>')
@login_required
@parent_required
def view_message(message_id):
    """Voir un message"""
    message = Message.query.get_or_404(message_id)
    
    # Vérifier les droits d'accès
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('Vous n\'êtes pas autorisé à voir ce message.', 'danger')
        return redirect(url_for('parent.messages'))
    
    # Marquer comme lu si c'est le destinataire
    if message.recipient_id == current_user.id and not message.is_read:
        message.mark_as_read()
        db.session.commit()
    
    return render_template('parent/view_message.html', message=message)
