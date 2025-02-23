from app import app, db, Exam, Question, ExamResult, User

def check_database():
    try:
        with app.app_context():
            # Check exam with id 4
            exam = Exam.query.get(4)
            if exam:
                print(f"Found exam: {exam.title}")
                print(f"Exam active status: {exam.is_active}")
                
                # Check questions for this exam
                question_count = Question.query.filter_by(exam_id=4).count()
                print(f"Number of questions: {question_count}")
                
                # Check if there are any previous attempts
                results = ExamResult.query.filter_by(exam_id=4).all()
                print(f"Previous attempts: {len(results)}")
                if results:
                    for result in results:
                        print(f"Result: Student {result.student_id}, Score: {result.score}/{result.max_score}")
            else:
                print("Exam #4 not found")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_database()
