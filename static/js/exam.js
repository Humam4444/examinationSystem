// Exam creation and management functionality

// Add a new question to the exam
function addQuestion() {
    const template = document.getElementById('question-template');
    const container = document.getElementById('questions-container');
    const clone = template.content.cloneNode(true);
    
    // Update name attributes for radio buttons to make them unique
    const questionCount = container.children.length;
    const radios = clone.querySelectorAll('input[type="radio"]');
    radios.forEach(radio => {
        radio.name = `correct_answer_${questionCount}`;
    });

    container.appendChild(clone);
    updateQuestionNumbers();
}

// Remove a question from the exam
function removeQuestion(button) {
    const questionItem = button.closest('.question-item');
    questionItem.remove();
    updateQuestionNumbers();
}

// Toggle options based on question type
function toggleOptions(select) {
    const questionItem = select.closest('.question-item');
    const optionsContainer = questionItem.querySelector('.options-container');
    const optionsList = questionItem.querySelector('.options-list');
    const correctAnswerInput = questionItem.querySelector('input[name="correct_answer[]"]');

    switch(select.value) {
        case 'multiple_choice':
            optionsContainer.style.display = 'block';
            optionsList.innerHTML = `
                <div class="row mb-2">
                    <div class="col">
                        <input type="text" class="form-control" name="options[]" placeholder="الخيار 1" required>
                    </div>
                    <div class="col-auto">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="correct_answer_temp" value="0" required>
                        </div>
                    </div>
                </div>
            `.repeat(4);
            break;
            
        case 'true_false':
            optionsContainer.style.display = 'block';
            optionsList.innerHTML = `
                <div class="row mb-2">
                    <div class="col">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="correct_answer_temp" value="true" required>
                            <label class="form-check-label">صح</label>
                        </div>
                    </div>
                </div>
                <div class="row mb-2">
                    <div class="col">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="correct_answer_temp" value="false" required>
                            <label class="form-check-label">خطأ</label>
                        </div>
                    </div>
                </div>
            `;
            break;
            
        case 'essay':
            optionsContainer.style.display = 'none';
            break;
    }

    // Update radio button names to be unique per question
    const questionIndex = Array.from(questionItem.parentNode.children).indexOf(questionItem);
    const radios = questionItem.querySelectorAll('input[type="radio"]');
    radios.forEach(radio => {
        radio.name = `correct_answer_${questionIndex}`;
    });
}

// Update correct answer when radio selection changes
function updateCorrectAnswer(event) {
    const radio = event.target;
    const questionItem = radio.closest('.question-item');
    const correctAnswerInput = questionItem.querySelector('input[name="correct_answer[]"]');
    correctAnswerInput.value = radio.value;
}

// Update question numbers after adding/removing questions
function updateQuestionNumbers() {
    const questions = document.querySelectorAll('.question-item');
    questions.forEach((question, index) => {
        const header = question.querySelector('.card-header h5');
        header.textContent = `السؤال ${index + 1}`;
    });
}

// Form validation before submission
document.addEventListener('DOMContentLoaded', function() {
    const examForm = document.getElementById('examForm');
    if (examForm) {
        examForm.addEventListener('submit', function(e) {
            const questions = document.querySelectorAll('.question-item');
            if (questions.length === 0) {
                e.preventDefault();
                alert('يجب إضافة سؤال واحد على الأقل');
                return;
            }

            // Validate multiple choice questions have a selected correct answer
            let valid = true;
            questions.forEach((question, index) => {
                const questionType = question.querySelector('select[name="question_type[]"]').value;
                if (questionType === 'multiple_choice' || questionType === 'true_false') {
                    const radios = question.querySelectorAll(`input[name="correct_answer_${index}"]`);
                    const selected = Array.from(radios).some(radio => radio.checked);
                    if (!selected) {
                        valid = false;
                        alert(`الرجاء تحديد الإجابة الصحيحة للسؤال ${index + 1}`);
                    }
                }
            });

            if (!valid) {
                e.preventDefault();
            }
        });
    }
});
