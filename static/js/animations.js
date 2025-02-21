document.addEventListener('DOMContentLoaded', function() {
    const animatedCards = document.querySelectorAll('.animated-card');

    animatedCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('animate__animated', 'animate__pulse');
        });

        card.addEventListener('mouseleave', function() {
            this.classList.remove('animate__animated', 'animate__pulse');
            // Need to force a reflow for the animation to be replayed on next mouseenter
            void this.offsetWidth;
        });
    });
});
