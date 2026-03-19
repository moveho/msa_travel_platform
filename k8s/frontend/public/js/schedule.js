import { API_SCHEDULE } from './config.js';
import { token } from './auth.js';

export async function loadSchedules(travelId) {
    const res = await fetch(`${API_SCHEDULE}/schedules?travel_id=${travelId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        const schedules = await res.json();
        schedules.sort((a, b) => new Date(a.date) - new Date(b.date));
        return schedules;
    }
    return [];
}

export async function createSchedule(travelId, date, time, place, memo, imageUrl) {
    const res = await fetch(`${API_SCHEDULE}/schedules`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            travel_id: travelId,
            date,
            time,
            place,
            memo,
            image_url: imageUrl
        })
    });
    return res.ok;
}

export async function deleteSchedule(id) {
    await fetch(`${API_SCHEDULE}/schedules/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
}
