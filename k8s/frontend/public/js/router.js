import { token } from './auth.js';

export function initRouter(callbacks) {
    window.addEventListener('hashchange', () => handleRoute(callbacks));
    window.addEventListener('load', () => {
        if (!token) {
            window.location.hash = '#login';
        } else {
            if (window.location.hash === '#login' || window.location.hash === '#signup' || !window.location.hash) {
                window.location.hash = '#dashboard';
            }
        }
        handleRoute(callbacks);
    });
}

function handleRoute(callbacks) {
    const hash = window.location.hash || '#login';

    // Hide all pages
    document.getElementById('login-page').classList.add('hidden');
    document.getElementById('signup-page').classList.add('hidden');
    document.getElementById('dashboard-page').classList.add('hidden');
    document.getElementById('navbar').classList.add('hidden');

    // Show active page
    if (hash === '#login') {
        document.getElementById('login-page').classList.remove('hidden');
    } else if (hash === '#signup') {
        document.getElementById('signup-page').classList.remove('hidden');
    } else if (hash === '#dashboard') {
        if (!token) {
            window.location.hash = '#login';
            return;
        }
        document.getElementById('dashboard-page').classList.remove('hidden');
        document.getElementById('navbar').classList.remove('hidden');

        if (callbacks.onDashboard) callbacks.onDashboard();
    }
}
