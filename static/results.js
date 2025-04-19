/* filepath: c:\Users\avina\FRVS\static\js\results.js */
document.addEventListener('DOMContentLoaded', function() {
    const progressBars = document.querySelectorAll('.progress-bar[data-width]');
    progressBars.forEach(bar => {
        const width = bar.getAttribute('data-width');
        bar.style.width = `${width}%`;
    });
});