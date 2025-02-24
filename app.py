from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
from sqlalchemy.types import PickleType
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Get the base directory
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# Database configuration
if os.environ.get('DATABASE_URL'):
    # Use PostgreSQL in production (Render)
    db_url = os.environ.get('DATABASE_URL')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    # Use SQLite in development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'exam_system.db')

# Ensure the instance folder exists
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
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

# Question Folder Model
class QuestionFolder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('question_folder.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='folder', lazy=True)
    children = db.relationship('QuestionFolder', backref=db.backref('parent', remote_side=[id]))

    def __repr__(self):
        return f'<QuestionFolder {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Question Model
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=True)  # Make nullable for question bank
    folder_id = db.Column(db.Integer, db.ForeignKey('question_folder.id'), nullable=True)
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, essay, etc.
    correct_answer = db.Column(db.String(500), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    options = db.Column(PickleType)
    difficulty_level = db.Column(db.String(20), nullable=False, default='medium')  # easy, medium, hard
    subject_tags = db.Column(db.String(200))  # Comma-separated tags
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:30]}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'folder_id': self.folder_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'points': self.points,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'difficulty_level': self.difficulty_level,
            'subject_tags': self.subject_tags,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
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
    is_graded = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=False)
    auto_graded_score = db.Column(db.Float)  # Score from auto-graded questions
    essay_score = db.Column(db.Float)  # Score from manually graded essay questions

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    student_count = User.query.filter_by(role='student').count()
    exam_count = Exam.query.filter_by(is_active=True).count()
    return render_template('index.html', student_count=student_count, exam_count=exam_count)

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
        flash('Only teachers can create exams.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        duration = request.form.get('duration')
        
        if not all([title, description, duration]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('create_exam'))
        
        try:
            duration = int(duration)
        except ValueError:
            flash('Duration must be a number.', 'error')
            return redirect(url_for('create_exam'))
        
        exam = Exam(
            title=title,
            description=description,
            duration=duration,
            creator_id=current_user.id
        )
        db.session.add(exam)
        db.session.flush()  # Get the exam ID without committing
        
        # Process questions
        question_texts = request.form.getlist('question_text[]')
        question_types = request.form.getlist('question_type[]')
        correct_answers = request.form.getlist('correct_answer[]')
        points_list = request.form.getlist('points[]')
        options_list = request.form.getlist('options[]')
        difficulty_levels = request.form.getlist('difficulty_level[]')
        subject_tags_list = request.form.getlist('subject_tags[]')
        from_bank_list = request.form.getlist('from_bank[]')
        question_ids = request.form.getlist('question_id[]')
        
        for i in range(len(question_texts)):
            if question_texts[i].strip():  # Only add non-empty questions
                # Check if this is a bank question
                is_bank_question = i < len(from_bank_list) and from_bank_list[i] == 'true'
                
                if is_bank_question and i < len(question_ids):
                    # Copy question from bank
                    bank_question = Question.query.get(question_ids[i])
                    if bank_question:
                        question = Question(
                            exam_id=exam.id,
                            question_text=bank_question.question_text,
                            question_type=bank_question.question_type,
                            correct_answer=bank_question.correct_answer,
                            points=int(points_list[i]),  # Allow point override
                            options=bank_question.options,
                            difficulty_level=bank_question.difficulty_level,
                            subject_tags=bank_question.subject_tags,
                            created_by=current_user.id
                        )
                        db.session.add(question)
                else:
                    # Create new question
                    options = options_list[i].split(',') if i < len(options_list) and options_list[i] else None
                    correct_answer = correct_answers[i] if i < len(correct_answers) else ''
                    difficulty = difficulty_levels[i] if i < len(difficulty_levels) else 'medium'
                    subject_tags = subject_tags_list[i] if i < len(subject_tags_list) else ''
                    
                    question = Question(
                        exam_id=exam.id,
                        question_text=question_texts[i],
                        question_type=question_types[i],
                        correct_answer=correct_answer,
                        points=int(points_list[i]),
                        options=options,
                        difficulty_level=difficulty,
                        subject_tags=subject_tags,
                        created_by=current_user.id
                    )
                    db.session.add(question)
        
        try:
            db.session.commit()
            flash('Exam created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the exam.', 'error')
            return redirect(url_for('create_exam'))
    
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
        try:
            # Update exam details
            exam.title = request.form['title']
            exam.description = request.form['description']
            exam.duration = int(request.form['duration'])
            
            # Get form data
            question_texts = request.form.getlist('question_text[]')
            question_types = request.form.getlist('question_type[]')
            points = request.form.getlist('points[]')
            difficulty_levels = request.form.getlist('difficulty_level[]')
            subject_tags = request.form.getlist('subject_tags[]')
            options = request.form.getlist('options[]')
            correct_answers = request.form.getlist('correct_answer[]')
            question_ids = request.form.getlist('question_id[]')
            
            # Delete existing questions that are not in the form
            existing_question_ids = set(int(qid) for qid in question_ids if qid)
            for question in exam.questions:
                if question.id not in existing_question_ids:
                    db.session.delete(question)
            
            # Update or create questions
            for i in range(len(question_texts)):
                question_id = question_ids[i] if i < len(question_ids) else None
                
                if question_id:
                    # Update existing question
                    question = Question.query.get(int(question_id))
                    if not question:
                        continue
                else:
                    # Create new question
                    question = Question(
                        exam_id=exam_id,
                        created_by=current_user.id
                    )
                    db.session.add(question)
                
                # Update question fields
                question.question_text = question_texts[i]
                question.question_type = question_types[i]
                question.points = int(points[i])
                question.difficulty_level = difficulty_levels[i]
                question.subject_tags = subject_tags[i]
                
                # Handle options for multiple choice questions
                if question_types[i] == 'multiple_choice':
                    question.options = options[i].split(',') if options[i] else []
                else:
                    question.options = None
                
                question.correct_answer = correct_answers[i]
            
            db.session.commit()
            flash('تم تحديث الامتحان بنجاح')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating exam: {str(e)}")
            flash('حدث خطأ أثناء تحديث الامتحان')
            return render_template('edit_exam.html', exam=exam)
    
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
        db.session.rollback()
        app.logger.error(f"Error in take_exam: {str(e)}", exc_info=True)
        flash('حدث خطأ أثناء تحميل الامتحان', 'error')
        return redirect(url_for('dashboard'))

@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
@login_required
def submit_exam(exam_id):
    if current_user.role != 'student':
        return jsonify({'error': 'غير مصرح لك بتقديم الامتحانات'}), 403
    
    try:
        exam = Exam.query.get_or_404(exam_id)
        if not exam.is_active:
            return jsonify({'error': 'هذا الامتحان غير متاح حالياً'}), 400
        
        # Get student's answers from form data
        answers = {}
        for question in exam.questions:
            answer_key = f'answer_{question.id}'
            if question.question_type == 'multiple_choice':
                answer = request.form.get(answer_key)
                if answer is not None:
                    # Convert the option index to the actual option text
                    try:
                        answer_index = int(answer)
                        if question.options and 0 <= answer_index < len(question.options):
                            answers[str(question.id)] = question.options[answer_index]
                    except (ValueError, IndexError):
                        pass
            elif question.question_type == 'true_false':
                answer = request.form.get(answer_key)
                if answer:
                    answers[str(question.id)] = answer
            elif question.question_type == 'essay':
                answer = request.form.get(answer_key)
                if answer:
                    answers[str(question.id)] = answer.strip()
        
        # Get exam result
        result = ExamResult.query.filter_by(
            exam_id=exam_id,
            student_id=current_user.id
        ).first()
        
        if not result:
            return jsonify({'error': 'لم يتم العثور على نتيجة الامتحان'}), 404
        
        # Save answers
        result.answers = answers
        result.end_time = datetime.utcnow()
        
        # Calculate score for non-essay questions
        auto_graded_score = 0
        max_score = 0
        
        for question in exam.questions:
            max_score += question.points
            if question.question_type != 'essay':
                answer = answers.get(str(question.id))
                if answer:
                    if question.question_type == 'multiple_choice':
                        if answer == question.correct_answer:
                            auto_graded_score += question.points
                    elif question.question_type == 'true_false':
                        if answer.lower() == question.correct_answer.lower():
                            auto_graded_score += question.points
        
        result.auto_graded_score = auto_graded_score
        result.essay_score = 0  # Initialize essay score
        result.max_score = max_score
        result.score = auto_graded_score  # Initial score from auto-graded questions
        result.is_graded = False  # Reset grading status
        result.is_published = False  # Reset publishing status
        
        db.session.commit()
        
        flash('تم تقديم الامتحان بنجاح', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in submit_exam: {str(e)}", exc_info=True)
        flash('حدث خطأ أثناء تقديم الامتحان', 'error')
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

# Question Bank Routes
@app.route('/question-bank')
@login_required
def question_bank():
    if current_user.role != 'teacher':
        flash('Only teachers can access the question bank.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    question_type = request.args.get('type')
    difficulty = request.args.get('difficulty')
    topic = request.args.get('topic')
    folder_id = request.args.get('folder_id', type=int)
    
    # Base query
    query = Question.query.filter_by(created_by=current_user.id)
    
    # Apply filters
    if question_type:
        query = query.filter_by(question_type=question_type)
    if difficulty:
        query = query.filter_by(difficulty_level=difficulty)
    if topic:
        query = query.filter(Question.subject_tags.like(f'%{topic}%'))
    if folder_id:
        query = query.filter_by(folder_id=folder_id)
    
    questions = query.all()
    folders = QuestionFolder.query.filter_by(created_by=current_user.id).all()
    
    return render_template('question_bank.html', 
                         questions=questions, 
                         folders=folders,
                         current_folder_id=folder_id)

@app.route('/question-bank/folder/create', methods=['POST'])
@login_required
def create_folder():
    if current_user.role != 'teacher':
        return jsonify({'error': 'غير مصرح لك بإنشاء مجلدات'}), 403
    
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        parent_id = request.form.get('parent_id')
        
        if not name:
            return jsonify({'error': 'اسم المجلد مطلوب'}), 400
        
        # Convert parent_id to int or None
        parent_id = int(parent_id) if parent_id and parent_id != 'null' else None
        
        folder = QuestionFolder(
            name=name,
            description=description,
            parent_id=parent_id,
            created_by=current_user.id
        )
        
        db.session.add(folder)
        db.session.commit()
        
        return jsonify({
            'id': folder.id,
            'name': folder.name,
            'description': folder.description,
            'parent_id': folder.parent_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/question-bank/question/create', methods=['POST'])
@login_required
def create_question():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Create new question
        question = Question(
            question_text=data.get('text', ''),  # Get text from the editor
            question_type=data.get('type', 'multiple_choice'),
            correct_answer=data.get('correct_answer', ''),
            points=int(data.get('points', 1)),
            options=data.get('options', []),
            difficulty_level=data.get('difficulty_level', 'medium'),
            subject_tags=data.get('subject_tags', ''),
            folder_id=data.get('folder_id'),
            created_by=current_user.id
        )
        
        db.session.add(question)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'question': question.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating question: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create question'
        }), 500

@app.route('/question-bank/question/<int:question_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_question(question_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    question = Question.query.get_or_404(question_id)
    
    if question.created_by != current_user.id:
        return jsonify({'error': 'You can only modify your own questions'}), 403
    
    if request.method == 'DELETE':
        try:
            db.session.delete(question)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting question: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to delete question'
            }), 500
    
    try:
        data = request.get_json()
        
        # Update question fields
        question.question_text = data.get('text', question.question_text)
        question.question_type = data.get('type', question.question_type)
        question.correct_answer = data.get('correct_answer', question.correct_answer)
        question.points = int(data.get('points', question.points))
        question.options = data.get('options', question.options)
        question.difficulty_level = data.get('difficulty_level', question.difficulty_level)
        question.subject_tags = data.get('subject_tags', question.subject_tags)
        question.folder_id = data.get('folder_id', question.folder_id)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'question': question.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating question: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update question'
        }), 500

@app.route('/question-bank/folder/<int:folder_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_folder(folder_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    folder = QuestionFolder.query.get_or_404(folder_id)
    
    if folder.created_by != current_user.id:
        return jsonify({'error': 'You can only modify your own folders'}), 403
    
    if request.method == 'DELETE':
        # Move questions in this folder to parent folder or root
        Question.query.filter_by(folder_id=folder_id).update({'folder_id': folder.parent_id})
        db.session.delete(folder)
        db.session.commit()
        return '', 204
    
    data = request.get_json()
    
    folder.name = data['name']
    folder.description = data.get('description')
    folder.parent_id = data.get('parent_id')
    
    db.session.commit()
    
    return jsonify(folder.to_dict())

# Question Bank API Routes
@app.route('/api/question_bank/folders')
@login_required
def get_question_folders():
    # Get all root folders (folders with no parent)
    folders = QuestionFolder.query
    
    # For non-admin users, only show folders they created or shared folders
    if current_user.role != 'admin':
        folders = folders.filter(
            (QuestionFolder.created_by == current_user.id)  # Their own folders
        )
    
    folders = folders.all()
    
    def get_folder_hierarchy(folder):
        folder_dict = folder.to_dict()
        folder_dict['children'] = [get_folder_hierarchy(child) for child in folder.children]
        return folder_dict
    
    # Build folder hierarchy
    folder_tree = [get_folder_hierarchy(folder) for folder in folders if folder.parent_id is None]
    
    return jsonify(folder_tree)

@app.route('/api/question_bank/questions')
@login_required
def get_question_bank_questions():
    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    question_type = request.args.get('type', '')
    folder_id = request.args.get('folder_id', '')
    
    # Start with all questions that either have no exam_id (bank questions) or are in a folder
    query = Question.query.filter(
        (Question.exam_id.is_(None)) |  # Questions not in any exam
        (Question.folder_id.isnot(None))  # Questions in folders
    )
    
    # Add filters
    if search:
        query = query.filter(Question.question_text.ilike(f'%{search}%'))
    if difficulty:
        query = query.filter(Question.difficulty_level == difficulty)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if folder_id:
        query = query.filter(Question.folder_id == folder_id)
    
    # Get all questions visible to the current user
    if current_user.role != 'admin':
        # For teachers, show their own questions and shared questions
        query = query.filter(
            (Question.created_by == current_user.id) |  # Their own questions
            (Question.folder_id.isnot(None))  # Questions in any folder (shared)
        )
    
    questions = query.all()
    return jsonify([{
        'id': q.id,
        'question_text': q.question_text,
        'question_type': q.question_type,
        'points': q.points,
        'difficulty_level': q.difficulty_level,
        'subject_tags': q.subject_tags,
        'options': q.options,
        'folder_id': q.folder_id
    } for q in questions])

@app.route('/api/question_bank/get_questions', methods=['POST'])
@login_required
def get_questions_by_ids():
    data = request.get_json()
    question_ids = data.get('question_ids', [])
    
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    return jsonify([{
        'id': q.id,
        'question_text': q.question_text,
        'question_type': q.question_type,
        'points': q.points,
        'difficulty_level': q.difficulty_level,
        'subject_tags': q.subject_tags,
        'options': q.options,
        'correct_answer': q.correct_answer
    } for q in questions])

@app.route('/grade_exam/<int:exam_id>')
@login_required
def grade_exam(exam_id):
    if current_user.role != 'teacher':
        flash('غير مصرح لك بتصحيح الامتحانات', 'error')
        return redirect(url_for('dashboard'))
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != current_user.id:
        flash('غير مصرح لك بتصحيح هذا الامتحان', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all submissions for this exam that have essay questions
    results = ExamResult.query.filter_by(exam_id=exam_id).all()
    submissions = []
    
    for result in results:
        has_essay = False
        essay_answers = {}
        
        # Check if submission has essay questions
        for q_id, answer in result.answers.items():
            question = Question.query.get(int(q_id))
            if question and question.question_type == 'essay':
                has_essay = True
                essay_answers[q_id] = {
                    'question': question,
                    'answer': answer
                }
        
        if has_essay:
            student = User.query.get(result.student_id)
            submissions.append({
                'result': result,
                'student': student,
                'essay_answers': essay_answers
            })
    
    return render_template('grade_exam.html', exam=exam, submissions=submissions)

@app.route('/submit_grades/<int:exam_id>', methods=['POST'])
@login_required
def submit_grades(exam_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        result_id = data.get('result_id')
        essay_scores = data.get('essay_scores', {})
        
        result = ExamResult.query.get_or_404(result_id)
        
        # Calculate total essay score
        total_essay_score = sum(float(score) for score in essay_scores.values())
        
        # Update result
        result.essay_score = total_essay_score
        result.score = result.auto_graded_score + total_essay_score
        result.is_graded = True
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/publish_results/<int:exam_id>', methods=['POST'])
@login_required
def publish_results(exam_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.creator_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Check if all submissions with essay questions are graded
        results = ExamResult.query.filter_by(exam_id=exam_id).all()
        for result in results:
            has_essay = any(
                Question.query.get(int(q_id)).question_type == 'essay'
                for q_id in result.answers.keys()
            )
            if has_essay and not result.is_graded:
                return jsonify({
                    'error': 'يجب تصحيح جميع الأسئلة المقالية قبل نشر النتائج'
                }), 400
        
        # Publish all results
        for result in results:
            result.is_published = True
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/view_result/<int:exam_id>')
@login_required
def view_result(exam_id):
    if current_user.role != 'student':
        flash('غير مصرح لك بعرض نتائج الامتحانات', 'error')
        return redirect(url_for('dashboard'))
    
    result = ExamResult.query.filter_by(
        exam_id=exam_id,
        student_id=current_user.id
    ).first_or_404()
    
    if not result.is_published:
        flash('لم يتم نشر نتائج هذا الامتحان بعد', 'warning')
        return redirect(url_for('dashboard'))
    
    return render_template('view_result.html', result=result)

def create_sample_data():
    # Delete all existing data
    ExamResult.query.delete()
    Question.query.delete()
    Exam.query.delete()
    User.query.delete()
    
    # Create test users
    teacher = User(username='teacher1', email='teacher1@example.com', role='teacher')
    teacher.set_password('password123')
    
    student = User(username='student1', email='student1@example.com', role='student')
    student.set_password('password123')
    
    db.session.add_all([teacher, student])
    db.session.commit()
    
    # Create a test exam
    exam = Exam(
        title='اختبار تجريبي',
        description='هذا اختبار تجريبي يغطي الجبر والهندسة وحساب المثلثات',
        duration=60,
        creator_id=teacher.id,
        is_active=True
    )
    db.session.add(exam)
    db.session.commit()
    
    # Create test questions
    questions = [
        Question(
            exam_id=exam.id,
            question_text='ما هي عاصمة المملكة العربية السعودية؟',
            question_type='multiple_choice',
            options=['الرياض', 'جدة', 'مكة', 'المدينة'],
            correct_answer='الرياض',
            points=2,
            created_by=teacher.id
        ),
        Question(
            exam_id=exam.id,
            question_text='هل اللغة العربية هي أكثر اللغات السامية المتحدث بها؟',
            question_type='true_false',
            correct_answer='true',
            points=1,
            created_by=teacher.id
        ),
        Question(
            exam_id=exam.id,
            question_text='اشرح أهمية اللغة العربية في الحضارة الإسلامية',
            question_type='essay',
            correct_answer='',
            points=5,
            created_by=teacher.id
        )
    ]
    db.session.add_all(questions)
    db.session.commit()
    
    # Create a test result
    result = ExamResult(
        exam_id=exam.id,
        student_id=student.id,
        score=7.0,
        max_score=8.0,
        answers={
            '1': 'الرياض',
            '2': 'true',
            '3': 'اللغة العربية لها أهمية كبيرة في الحضارة الإسلامية لأنها لغة القرآن الكريم...'
        },
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        is_graded=True,
        is_published=True,
        auto_graded_score=3.0,
        essay_score=4.0
    )
    db.session.add(result)
    db.session.commit()
    
    print("Sample data created successfully!")

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
