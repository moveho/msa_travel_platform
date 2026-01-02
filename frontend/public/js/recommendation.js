import { API_RECOMMENDATION } from './config.js';

export async function loadRecommendations() {
    try {
        const res = await fetch(`${API_RECOMMENDATION}/recommendations`);
        if (res.ok) {
            return await res.json();
        }
    } catch (e) {
        console.error("Failed to load recommendations", e);
    }
    return [];
}
