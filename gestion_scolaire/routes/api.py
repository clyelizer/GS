"""
Routes API - Endpoints REST pour les opérations AJAX
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from gestion_scolaire import db
from gestion_scolaire.models import (
    User, SchoolClass, Subject, Grade, BulletinStructure,
    Attendance, STANDARD_PERIODS
)

api_bp = Blueprint('api', __name__)


# ============================================
# API UTILISATEURS
# ============================================

@api_bp.route('/users')
@login_required
def get_users():
    """Récupérer la liste des utilisateurs"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Non autorisé'}), 403
    
    role = request.args.get('role')
    class_id = request.args.get('class_id', type=int)
    
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    if class_id:
        query = query.filter_by(current_class_id=class_id)
    
    users = query.order_by(User.last_name).all()
    
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'full_name': u.full_name,
        'role': u.role,
        'class_id': u.current_class_id,
        'class_name': u.current_class.name if u.current_class else None
    } for u in users])


@api_bp.route('/users/<int:user_id>')
@login_required
def get_user(user_id):
    """Récupérer un utilisateur"""
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'role': user.role,
        'phone': user.phone,
        'class_id': user.current_class_id,
        'class_name': user.current_class.name if user.current_class else None,
        'is_active': user.is_active
    })


# ============================================
# API CLASSES
# ============================================

@api_bp.route('/classes')
@login_required
def get_classes():
    """Récupérer la liste des classes"""
    classes = SchoolClass.query.order_by(SchoolClass.name).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'level': c.level,
        'section': c.section,
        'student_count': c.student_count,
        'has_bulletin_structure': c.bulletin_structure is not None
    } for c in classes])


@api_bp.route('/classes/<int:class_id>/students')
@login_required
def get_class_students(class_id):
    """Récupérer les élèves d'une classe"""
    students = User.query.filter_by(
        role='student',
        current_class_id=class_id
    ).order_by(User.last_name).all()
    
    return jsonify([{
        'id': s.id,
        'username': s.username,
        'full_name': s.full_name
    } for s in students])


@api_bp.route('/classes/<int:class_id>/subjects')
@login_required
def get_class_subjects(class_id):
    """Récupérer les matières d'une classe"""
    structure = BulletinStructure.query.filter_by(school_class_id=class_id).first()
    
    if not structure:
        return jsonify({'error': 'Aucune structure de bulletin pour cette classe'}), 404
    
    return jsonify({
        'subjects_part1': structure.get_subjects_part1_list(),
        'subjects_part2': structure.get_subjects_part2_list(),
        'all_subjects': structure.get_all_subjects()
    })


# ============================================
# API NOTES
# ============================================

@api_bp.route('/grades')
@login_required
def get_grades():
    """Récupérer les notes"""
    student_id = request.args.get('student_id', type=int)
    period = request.args.get('period')
    class_id = request.args.get('class_id', type=int)
    
    query = Grade.query
    
    if student_id:
        query = query.filter_by(student_id=student_id)
    
    if period:
        query = query.filter_by(period=period)
    
    if class_id:
        # Filtrer par classe (via les étudiants)
        student_ids = [s.id for s in User.query.filter_by(current_class_id=class_id).all()]
        query = query.filter(Grade.student_id.in_(student_ids))
    
    grades = query.order_by(Grade.subject_name).all()
    
    return jsonify([{
        'id': g.id,
        'student_id': g.student_id,
        'student_name': g.student.full_name,
        'subject_name': g.subject_name,
        'moy_cl': g.moy_cl,
        'n_compo': g.n_compo,
        'coef': g.coef,
        'average': g.average,
        'weighted_average': g.weighted_average,
        'appreciation': g.appreciation,
        'period': g.period
    } for g in grades])


@api_bp.route('/grades', methods=['POST'])
@login_required
def create_grade():
    """Créer une note"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Non autorisé'}), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400
    
    required_fields = ['student_id', 'subject_name', 'moy_cl', 'n_compo', 'coef', 'period']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Champ requis: {field}'}), 400
    
    try:
        moy_cl = float(data['moy_cl'])
        n_compo = float(data['n_compo'])
        coef = int(data['coef'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Format de nombre invalide'}), 400
    
    if not (0 <= moy_cl <= 20 and 0 <= n_compo <= 20):
        return jsonify({'error': 'Les notes doivent être entre 0 et 20'}), 400
    
    grade = Grade(
        student_id=data['student_id'],
        subject_name=data['subject_name'],
        moy_cl=moy_cl,
        n_compo=n_compo,
        coef=coef,
        period=data['period'],
        teacher_id=current_user.id
    )
    grade.appreciation = Grade.get_appreciation(grade.average)
    
    db.session.add(grade)
    db.session.commit()
    
    return jsonify({
        'message': 'Note créée avec succès',
        'grade': {
            'id': grade.id,
            'average': grade.average,
            'appreciation': grade.appreciation
        }
    }), 201


@api_bp.route('/grades/<int:grade_id>', methods=['PUT'])
@login_required
def update_grade(grade_id):
    """Modifier une note"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Non autorisé'}), 403
    
    grade = Grade.query.get_or_404(grade_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400
    
    try:
        if 'moy_cl' in data:
            grade.moy_cl = float(data['moy_cl'])
        if 'n_compo' in data:
            grade.n_compo = float(data['n_compo'])
        if 'coef' in data:
            grade.coef = int(data['coef'])
        if 'period' in data:
            grade.period = data['period']
    except (ValueError, TypeError):
        return jsonify({'error': 'Format de nombre invalide'}), 400
    
    if not (0 <= grade.moy_cl <= 20 and 0 <= grade.n_compo <= 20):
        return jsonify({'error': 'Les notes doivent être entre 0 et 20'}), 400
    
    grade.appreciation = Grade.get_appreciation(grade.average)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Note mise à jour',
        'grade': {
            'id': grade.id,
            'average': grade.average,
            'appreciation': grade.appreciation
        }
    })


@api_bp.route('/grades/<int:grade_id>', methods=['DELETE'])
@login_required
def delete_grade(grade_id):
    """Supprimer une note"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Non autorisé'}), 403
    
    grade = Grade.query.get_or_404(grade_id)
    
    db.session.delete(grade)
    db.session.commit()
    
    return jsonify({'message': 'Note supprimée'})


# ============================================
# API STATISTIQUES
# ============================================

@api_bp.route('/stats/student/<int:student_id>')
@login_required
def get_student_stats(student_id):
    """Statistiques d'un élève"""
    student = User.query.get_or_404(student_id)
    
    # Vérifier les droits d'accès
    if current_user.role == 'student' and current_user.id != student_id:
        return jsonify({'error': 'Non autorisé'}), 403
    if current_user.role == 'parent' and student not in current_user.children:
        return jsonify({'error': 'Non autorisé'}), 403
    
    stats = {}
    
    for period in STANDARD_PERIODS:
        grades = Grade.query.filter_by(student_id=student_id, period=period).all()
        
        if grades:
            total_weighted = sum(g.weighted_average for g in grades)
            total_coef = sum(g.coef for g in grades)
            avg = round(total_weighted / total_coef, 2) if total_coef > 0 else 0
            
            stats[period] = {
                'average': avg,
                'grade_count': len(grades),
                'appreciation': Grade.get_appreciation(avg)
            }
        else:
            stats[period] = {
                'average': 0,
                'grade_count': 0,
                'appreciation': '-'
            }
    
    return jsonify(stats)


@api_bp.route('/stats/class/<int:class_id>')
@login_required
def get_class_stats(class_id):
    """Statistiques d'une classe"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'error': 'Non autorisé'}), 403
    
    school_class = SchoolClass.query.get_or_404(class_id)
    students = User.query.filter_by(role='student', current_class_id=class_id).all()
    
    stats = {
        'student_count': len(students),
        'periods': {}
    }
    
    for period in STANDARD_PERIODS:
        period_averages = []
        
        for student in students:
            grades = Grade.query.filter_by(student_id=student.id, period=period).all()
            if grades:
                total_weighted = sum(g.weighted_average for g in grades)
                total_coef = sum(g.coef for g in grades)
                if total_coef > 0:
                    period_averages.append(total_weighted / total_coef)
        
        if period_averages:
            stats['periods'][period] = {
                'class_average': round(sum(period_averages) / len(period_averages), 2),
                'highest': round(max(period_averages), 2),
                'lowest': round(min(period_averages), 2),
                'student_with_grades': len(period_averages)
            }
        else:
            stats['periods'][period] = {
                'class_average': 0,
                'highest': 0,
                'lowest': 0,
                'student_with_grades': 0
            }
    
    return jsonify(stats)


# ============================================
# API PÉRIODES
# ============================================

@api_bp.route('/periods')
@login_required
def get_periods():
    """Récupérer les périodes"""
    return jsonify(STANDARD_PERIODS)


# ============================================
# API MATIÈRES
# ============================================

@api_bp.route('/subjects')
@login_required
def get_subjects():
    """Récupérer les matières"""
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.category, Subject.name).all()
    
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'code': s.code,
        'category': s.category,
        'default_coef': s.default_coef
    } for s in subjects])
