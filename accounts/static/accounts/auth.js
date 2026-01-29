document.addEventListener('DOMContentLoaded', function () {
    // Select all toggle buttons
    const toggleButtons = document.querySelectorAll('.password-toggle');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function () {
            // Find the associated input
            const inputId = this.getAttribute('data-target');
            const input = document.getElementById(inputId);
            const icon = this.querySelector('i');

            if (input) {
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.remove('ph-eye-slash');
                    icon.classList.add('ph-eye');
                } else {
                    input.type = 'password';
                    icon.classList.remove('ph-eye');
                    icon.classList.add('ph-eye-slash');
                }
            }
        });
    });
});
