from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
from sqlalchemy.types import PickleType

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'exam_system.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # 'student', 'teacher', 'admin'
    exams = db.relationship('Exam', backref='creator', lazy=True)
    exam_results = db.relationship('ExamResult', backref='student', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Exam Model
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer, nullable=False)  # بالدقائق
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='exam', lazy=True)
    results = db.relationship('ExamResult', backref='exam', lazy=True)

# Question Model
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, true_false, text
    points = db.Column(db.Integer, nullable=False)
    options = db.Column(PickleType)  # لتخزين خيارات السؤال في حالة الاختيار من متعدد
    correct_answer = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f'<Question {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'points': self.points,
            'options': self.options if self.question_type == 'multiple_choice' else None
        }

# Exam Result Model
class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    answers = db.Column(db.PickleType)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email address already registered')
            return redirect(url_for('register'))

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Registration successful')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.')
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        # عرض جميع الامتحانات للمعلم
        exams = Exam.query.filter_by(creator_id=current_user.id).all()
    else:
        # عرض الامتحانات النشطة للطلاب
        exams = Exam.query.filter_by(is_active=True).all()
    return render_template('dashboard.html', exams=exams)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_exam', methods=['GET', 'POST'])
@login_required
def create_exam():
    if current_user.role != 'teacher':
        flash('غير مصرح لك بإنشاء امتحانات')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # إنشاء الاختبار
        exam = Exam(
            title=request.form['title'],
            description=request.form['description'],
            duration=int(request.form['duration']),
            creator_id=current_user.id,
            is_active=True
        )
        db.session.add(exam)
        db.session.flush()  # للحصول على exam.id

        # إضافة الأسئلة
        question_texts = request.form.getlist('question_text[]')
        question_types = request.form.getlist('question_type[]')
        points_list = request.form.getlist('points[]')
        options_list = request.form.getlist('options[]')
        correct_answers = request.form.getlist('correct_answer[]')

        option_index = 0
        for i in range(len(question_texts)):
            question = Question(
                exam_id=exam.id,
                question_text=question_texts[i],
                question_type=question_types[i],
                points=int(points_list[i])
            )

            if question_types[i] in ['multiple_choice', 'true_false']:
                if question_types[i] == 'multiple_choice':
                    num_options = 4
                else:
                    num_options = 2
                
                question.options = options_list[option_index:option_index + num_options]
                option_index += num_options
                question.correct_answer = correct_answers[i]

            db.session.add(question)

        db.session.commit()
        flash('تم إنشاء الاختبار بنجاح')
        return redirect(url_for('dashboard'))
    
    return render_template('create_exam.html')

@app.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def edit_exam(exam_id):
    if current_user.role != 'teacher':
        flash('غير مصرح لك بتعديل الامتحانات')
        return redirect(url_for('dashboard'))
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != current_user.id:
        flash('غير مصرح لك بتعديل هذا الامتحان')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        exam.title = request.form['title']
        exam.description = request.form['description']
        exam.duration = int(request.form['duration'])
        db.session.commit()
        flash('تم تحديث الامتحان بنجاح')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_exam.html', exam=exam)

@app.route('/toggle_exam/<int:exam_id>', methods=['POST'])
@login_required
def toggle_exam(exam_id):
    if current_user.role != 'teacher':
        return jsonify({'success': False, 'message': 'غير مصرح'})
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != current_user.id:
        return jsonify({'success': False, 'message': 'غير مصرح'})
    
    data = request.get_json()
    exam.is_active = data['is_active']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/take_exam/<int:exam_id>')
@login_required
def take_exam(exam_id):
    try:
        app.logger.info(f"Student {current_user.id} attempting to take exam {exam_id}")
        
        if current_user.role != 'student':
            app.logger.warning(f"Non-student user {current_user.id} tried to take exam")
            flash('غير مصرح لك بأخذ الامتحانات', 'error')
            return redirect(url_for('dashboard'))
        
        exam = Exam.query.get_or_404(exam_id)
        if not exam:
            app.logger.error(f"Exam {exam_id} not found")
            flash('الامتحان غير موجود', 'error')
            return redirect(url_for('dashboard'))
            
        app.logger.info(f"Found exam: {exam.title}")
        
        if not exam.is_active:
            app.logger.warning(f"Exam {exam_id} is not active")
            flash('هذا الامتحان غير متاح حالياً', 'error')
            return redirect(url_for('dashboard'))
        
        # التحقق من عدم أخذ الامتحان سابقاً
        previous_result = ExamResult.query.filter_by(
            student_id=current_user.id,
            exam_id=exam_id
        ).first()
        
        if previous_result:
            app.logger.warning(f"Student {current_user.id} already took exam {exam_id}")
            flash('لقد قمت بأخذ هذا الامتحان مسبقاً', 'error')
            return redirect(url_for('dashboard'))
        
        # التحقق من وجود أسئلة في الامتحان
        if not exam.questions:
            app.logger.error(f"Exam {exam_id} has no questions")
            flash('لا يوجد أسئلة في هذا الامتحان', 'error')
            return redirect(url_for('dashboard'))
            
        # إنشاء نتيجة امتحان جديدة
        result = ExamResult(
            exam_id=exam_id,
            student_id=current_user.id,
            start_time=datetime.utcnow(),
            answers={}  # تهيئة الإجابات كقاموس فارغ
        )
        db.session.add(result)
        db.session.commit()
        app.logger.info(f"Created new exam result for student {current_user.id}")
        
        return render_template('take_exam.html', exam=exam)
        
    except Exception as e:
        app.logger.error(f"Error in take_exam: {str(e)}", exc_info=True)
        db.session.rollback()
        flash('حدث خطأ أثناء تحميل الامتحان', 'error')
        return redirect(url_for('dashboard'))

@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
@login_required
def submit_exam(exam_id):
    if current_user.role != 'student':
        flash('غير مصرح لك بتسليم الامتحانات', 'error')
        return redirect(url_for('dashboard'))
    
    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_active:
        flash('هذا الامتحان غير متاح حالياً', 'error')
        return redirect(url_for('dashboard'))
    
    result = ExamResult.query.filter_by(
        student_id=current_user.id,
        exam_id=exam_id,
        end_time=None
    ).first()
    
    if not result:
        flash('لم يتم العثور على جلسة امتحان نشطة', 'error')
        return redirect(url_for('dashboard'))
    
    total_points = 0
    answers = []
    
    # تصحيح الإجابات
    for question in exam.questions:
        answer = request.form.get(f'answer_{question.id}')
        is_correct = False
        
        if question.question_type in ['multiple_choice', 'true_false']:
            is_correct = answer == question.correct_answer
            points = question.points if is_correct else 0
        else:  # essay
            points = 0  # يتم تصحيح الأسئلة المقالية يدوياً
        
        total_points += points
        answers.append({
            'question_id': question.id,
            'student_answer': answer,
            'is_correct': is_correct,
            'points': points
        })
    
    # تحديث النتيجة
    result.score = total_points
    result.max_score = sum(q.points for q in exam.questions)
    result.answers = answers
    result.end_time = datetime.utcnow()
    db.session.commit()
    
    flash(f'تم تسليم الامتحان بنجاح! النتيجة: {total_points} من {result.max_score}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/view_exam_results/<int:exam_id>')
@login_required
def view_exam_results(exam_id):
    if current_user.role != 'teacher':
        flash('غير مصرح لك بعرض نتائج الامتحانات')
        return redirect(url_for('dashboard'))
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != current_user.id:
        flash('غير مصرح لك بعرض نتائج هذا الامتحان')
        return redirect(url_for('dashboard'))
    
    return render_template('exam_results.html', exam=exam)

def create_sample_data():
    # حذف جميع البيانات الموجودة
    ExamResult.query.delete()
    Question.query.delete()
    Exam.query.delete()
    User.query.delete()
    db.session.commit()
    
    # إنشاء حساب معلم افتراضي
    teacher = User(
        username='teacher',
        email='teacher@example.com',
        role='teacher'
    )
    teacher.set_password('password123')
    db.session.add(teacher)
    
    # إنشاء حساب طالب افتراضي
    student = User(
        username='student',
        email='student@example.com',
        role='student'
    )
    student.set_password('password123')
    db.session.add(student)
    db.session.commit()
    
    # إنشاء امتحان رياضيات نموذجي
    math_exam = Exam(
        title='امتحان الرياضيات',
        description='امتحان شامل في الرياضيات يغطي الجبر والهندسة وحساب المثلثات',
        duration=60,
        creator_id=teacher.id,
        is_active=True
    )
    db.session.add(math_exam)
    db.session.flush()
    
    # إضافة أسئلة متنوعة
    questions = [
        {
            'text': 'ما هو ناتج 5 × 7 ؟',
            'type': 'multiple_choice',
            'options': ['25', '35', '40', '45'],
            'correct': '35',
            'points': 2
        },
        {
            'text': 'هل المثلث المتساوي الأضلاع جميع زواياه 60 درجة؟',
            'type': 'true_false',
            'correct': 'صح',
            'points': 1
        },
        {
            'text': 'احسب مساحة مثلث طول قاعدته 6 سم وارتفاعه 8 سم.',
            'type': 'multiple_choice',
            'options': ['24 سم²', '48 سم²', '12 سم²', '36 سم²'],
            'correct': '24 سم²',
            'points': 2
        },
        {
            'text': 'اشرح كيفية حل المعادلة التربيعية: x² + 5x + 6 = 0',
            'type': 'essay',
            'correct': '',
            'points': 5
        }
    ]
    
    for q in questions:
        question = Question(
            exam_id=math_exam.id,
            question_text=q['text'],
            question_type=q['type'],
            correct_answer=q['correct'],
            points=q['points']
        )
        if q['type'] == 'multiple_choice':
            question.options = q['options']
        db.session.add(question)
    
    db.session.commit()

if __name__ == '__main__':
    # Ensure instance folder exists
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    with app.app_context():
        db.create_all()
        # Create sample data if database is empty
        if not User.query.first():
            create_sample_data()
    
    app.run(debug=True)
