// Main JavaScript file for the examination system

// Handle exam verification button clicks
document.querySelectorAll('.verification-btn').forEach(button => {
    button.addEventListener('click', function(e) {
        e.preventDefault();
        // Add verification logic here
        console.log('Verification requested');
    });
});

// Handle exam resume/start button clicks
document.querySelectorAll('.resume-btn').forEach(button => {
    button.addEventListener('click', function(e) {
        e.preventDefault();
        // Add exam start/resume logic here
        console.log('Exam start/resume requested');
    });
});

// Add hover effects for exam cards
document.querySelectorAll('.exam-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});
