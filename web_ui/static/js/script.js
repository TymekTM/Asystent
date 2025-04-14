// Theme Switching Logic
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const lightIcon = document.getElementById('theme-icon-light');
const darkIcon = document.getElementById('theme-icon-dark');
const currentTheme = localStorage.getItem('theme');
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.setAttribute('data-bs-theme', 'dark');
        if (lightIcon) lightIcon.classList.add('d-none');
        if (darkIcon) darkIcon.classList.remove('d-none');
    } else {
        document.body.setAttribute('data-bs-theme', 'light');
        if (lightIcon) lightIcon.classList.remove('d-none');
        if (darkIcon) darkIcon.classList.add('d-none');
    }
}

// Apply initial theme based on preference or system setting
if (currentTheme) {
    applyTheme(currentTheme);
} else if (prefersDarkScheme.matches) {
    applyTheme('dark');
} else {
     applyTheme('light'); // Default to light
}


// Listener for theme toggle button
if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        let newTheme = document.body.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });
}

// Listener for system theme changes
prefersDarkScheme.addEventListener('change', (e) => {
    // Only change if no explicit theme is set in local storage
    if (!localStorage.getItem('theme')) {
        applyTheme(e.matches ? 'dark' : 'light');
    }
});

// --- Other Global JS (if any) ---
console.log("Assistant CP UI script loaded.");

// Example: Close flash messages after a delay
document.addEventListener('DOMContentLoaded', (event) => {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Close after 5 seconds
    });
});
