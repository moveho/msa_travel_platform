import { API_TRAVEL } from './config.js';
import { token, logout, getUser } from './auth.js';

export async function loadTravels() {
    const user = getUser();
    const endpoint = (user && user.role === 'admin') ? `${API_TRAVEL}/admin/travels` : `${API_TRAVEL}/travels`;

    const res = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        return await res.json();
    } else if (res.status === 401) {
        logout();
        return [];
    }
    return [];
}

export async function createTravel(title, description) {
    const res = await fetch(`${API_TRAVEL}/travels`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ title, description })
    });
    return res.ok;
}

export async function deleteTravel(id) {
    await fetch(`${API_TRAVEL}/travels/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
}
