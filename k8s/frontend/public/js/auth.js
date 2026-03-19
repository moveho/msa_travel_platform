import { API_AUTH } from './config.js';

export let token = localStorage.getItem('token');

export function setToken(newToken) {
    token = newToken;
    if (token) {
        localStorage.setItem('token', token);
    } else {
        localStorage.removeItem('token');
    }
}

export function getUser() {
    if (!token) return null;
    try {
        return JSON.parse(atob(token.split('.')[1]));
    } catch (e) {
        return null;
    }
}

export async function signup(username, password) {
    const res = await fetch(`${API_AUTH}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
        const text = await res.text();
        try {
            const data = JSON.parse(text);
            throw new Error(data.detail || 'Signup failed');
        } catch (e) {
            throw new Error(e.message || `Error: ${text.substring(0, 100)}`);
        }
    }
    return true;
}

export async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${API_AUTH}/token`, {
        method: 'POST',
        body: formData
    });

    if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        return true;
    } else {
        throw new Error('Invalid username or password');
    }
}

export function logout() {
    setToken(null);
    window.location.hash = '#login';
}
