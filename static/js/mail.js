// Get form and status element
const form = document.getElementById('contact-form');
const status = document.getElementById('form-status');

form.addEventListener('submit', function(event) {
    event.preventDefault(); // prevent default form submission

    status.textContent = 'Sending...';

    // Send email using EmailJS
    emailjs.sendForm('service_o7ekpoq', 'template_krcnku7', this)
        .then(function() {
            status.textContent = 'Message sent successfully! 🚀';
            status.className = 'note success';
            form.reset();
        }, function(error) {
            console.error('FAILED...', error);
            status.textContent = 'Oops! Something went wrong.';
            status.className = 'note error';
        });
});
