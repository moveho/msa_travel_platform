import { signup, login, logout, getUser, token } from './auth.js';
import { loadTravels, createTravel, deleteTravel } from './travel.js';
import { loadSchedules, createSchedule, deleteSchedule } from './schedule.js';
import { loadRecommendations } from './recommendation.js';
import { initRouter } from './router.js';

// --- UI Helpers ---
function updateUserGreeting() {
    const user = getUser();
    const greeting = document.getElementById('user-greeting');
    if (user) {
        greeting.textContent = `Hello, ${user.sub || user.username}`;
    } else {
        greeting.textContent = 'Welcome';
    }
}

async function renderTravels() {
    const travels = await loadTravels();
    const list = document.getElementById('travel-list');
    const emptyState = document.getElementById('empty-state');

    if (travels.length === 0) {
        list.innerHTML = '';
        emptyState.classList.remove('hidden');
    } else {
        emptyState.classList.add('hidden');
        list.innerHTML = travels.map(t => `
            <div class="bg-white rounded-xl shadow-sm hover:shadow-lg transition duration-300 overflow-hidden border border-gray-100 flex flex-col">
                <div class="h-32 bg-gray-200 relative overflow-hidden">
                    ${t.image_url ?
                `<img src="${t.image_url}" class="w-full h-full object-cover" alt="${t.title}">` :
                `<div class="w-full h-full bg-gradient-to-r from-indigo-400 to-purple-500 flex items-center justify-center">
                            <span class="text-white text-4xl opacity-50">✈️</span>
                        </div>`
            }
                </div>
                <div class="p-6 flex-grow">
                    <div class="flex justify-between items-start mb-2">
                        <h3 class="text-xl font-bold text-gray-900 truncate">${t.title}</h3>
                    </div>
                    <p class="text-gray-500 text-sm mb-4 line-clamp-2">${t.description || 'No description'}</p>
                </div>
                <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
                    <button data-action="view-itinerary" data-id="${t.id}" class="text-indigo-600 font-medium hover:text-indigo-800 text-sm">View Itinerary →</button>
                    <button data-action="delete-travel" data-id="${t.id}" class="text-gray-400 hover:text-red-500 transition">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                </div>
            </div>
        `).join('');
    }
}

async function renderRecommendations() {
    const recs = await loadRecommendations();
    const list = document.getElementById('recommendation-list');

    if (recs.length === 0) {
        list.innerHTML = '<p class="text-gray-500 text-sm">No recommendations yet.</p>';
        return;
    }

    list.innerHTML = recs.map(r => `
        <div onclick="openRecommendationModal('${r.id}')" class="flex-shrink-0 w-72 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg transition cursor-pointer transform hover:-translate-y-1">
            <div class="h-40 bg-gray-200 relative">
                <img src="${r.imageUrl || 'https://via.placeholder.com/300x200'}" alt="${r.title}" class="w-full h-full object-cover">
                <div class="absolute top-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-lg text-xs font-bold text-indigo-600 shadow-sm">
                    ${Math.round(r.totalScore)} pts
                </div>
            </div>
            <div class="p-4">
                <h4 class="font-bold text-gray-900 truncate text-lg">${r.title}</h4>
                <p class="text-xs text-gray-500 mt-1">${r.country}</p>
                <p class="text-sm text-gray-600 mt-2 line-clamp-2">${r.reason}</p>
            </div>
        </div>
    `).join('');

    // Store recs globally for modal access
    window.currentRecommendations = recs;
}

window.openRecommendationModal = (id) => {
    const rec = window.currentRecommendations.find(r => r.id === id);
    if (!rec) return;

    document.getElementById('rec-modal-image').src = rec.imageUrl || 'https://via.placeholder.com/600x400';
    document.getElementById('rec-modal-title').textContent = rec.title;
    document.getElementById('rec-modal-country').textContent = rec.country;
    document.getElementById('rec-modal-score').textContent = Math.round(rec.totalScore);
    document.getElementById('rec-modal-author').textContent = rec.author;
    document.getElementById('rec-modal-reason').textContent = rec.reason;
    document.getElementById('rec-modal-desc').textContent = rec.description;

    document.getElementById('recommendation-modal').classList.remove('hidden');
};

window.closeRecommendationModal = () => {
    document.getElementById('recommendation-modal').classList.add('hidden');
};

const renderSchedules = async (travelId) => {
    const schedules = await loadSchedules(travelId);
    const list = document.getElementById('schedule-list');

    // Group by Date for better visual
    // But for now, simple timeline
    list.innerHTML = schedules.map(s => `
        <li>
            <div class="relative pb-8">
                <span class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>
                <div class="relative flex space-x-3">
                    <div>
                        <span class="h-8 w-8 rounded-full bg-indigo-500 flex items-center justify-center ring-8 ring-white">
                           <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </span>
                    </div>
                    <div class="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div class="space-y-2">
                             <div class="flex items-center space-x-2">
                                <p class="text-sm text-gray-500">${s.date} ${s.time ? `<span class="text-indigo-600 font-bold">${s.time}</span>` : ''}</p>
                             </div>
                            
                            <div>
                                <p class="text-md font-bold text-gray-900">${s.place}</p>
                                ${s.memo ? `<p class="text-sm text-gray-600">${s.memo}</p>` : ''}
                            </div>
                            
                            ${s.image_url ? `
                                <div class="mt-2">
                                    <img src="${s.image_url}" class="h-32 w-auto rounded-lg shadow-sm border border-gray-100 object-cover" alt="Schedule Image">
                                </div>
                            ` : ''}
                        </div>
                        <div class="text-right text-sm whitespace-nowrap text-gray-500">
                             <button onclick="removeSchedule('${s.id}', '${travelId}')" class="text-red-400 hover:text-red-600">Delete</button>
                        </div>
                    </div>
                </div>
            </div>
        </li>
    `).join('');
};

// --- Event Listeners ---

// Global Click Handler (Delegation)
document.addEventListener('click', async (e) => {
    const target = e.target.closest('button');
    if (!target) return;

    const action = target.dataset.action;
    const id = target.dataset.id;

    if (action === 'view-itinerary') {
        document.getElementById('current-travel-id').value = id;
        document.getElementById('schedule-modal').classList.remove('hidden');
        renderSchedules(id);
    } else if (action === 'delete-travel') {
        if (confirm('Delete this trip?')) {
            await deleteTravel(id);
            renderTravels();
        }
    } else if (action === 'delete-schedule') {
        await deleteSchedule(id);
        const travelId = document.getElementById('current-travel-id').value;
        renderSchedules(travelId);
    }
});

// Form Handlers
window.signup = async () => {
    const username = document.getElementById('signup-username').value;
    const password = document.getElementById('signup-password').value;
    try {
        await signup(username, password);
        alert('Account created! Please log in.');
        window.location.hash = '#login';
    } catch (e) {
        alert(e.message);
    }
};

window.login = async () => {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    try {
        await login(username, password);
        window.location.hash = '#dashboard';
    } catch (e) {
        alert(e.message);
    }
};

window.logout = logout;

// Helper to read and resize image
const processImage = (file) => {
    return new Promise((resolve, reject) => {
        if (!file) return resolve(null);

        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                try {
                    const canvas = document.createElement('canvas');
                    const MAX_WIDTH = 800;
                    const MAX_HEIGHT = 600;
                    let width = img.width;
                    let height = img.height;

                    if (width > height) {
                        if (width > MAX_WIDTH) {
                            height *= MAX_WIDTH / width;
                            width = MAX_WIDTH;
                        }
                    } else {
                        if (height > MAX_HEIGHT) {
                            width *= MAX_HEIGHT / height;
                            height = MAX_HEIGHT;
                        }
                    }

                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    resolve(canvas.toDataURL('image/jpeg', 0.7)); // Compress to 70% quality
                } catch (e) {
                    reject(e);
                }
            };
            img.onerror = (err) => reject(new Error("Image load failed"));
        };
        reader.onerror = (err) => reject(new Error("File read failed"));
    });
};

// Generic Image Preview Logic
window.handleFileSelect = (input) => {
    const file = input.files[0];
    const wrapper = input.parentElement;
    const preview = wrapper.querySelector('img');
    const content = wrapper.querySelector('div[id$="-content"]'); // contains 'content' in ID
    const removeBtn = wrapper.querySelector('button');

    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.classList.remove('hidden');
            if (content) content.classList.add('hidden');
            if (removeBtn) removeBtn.classList.remove('hidden');
            wrapper.classList.add('border-indigo-500'); // Keep active border
        };
        reader.readAsDataURL(file);
    }
};

// Generic Reset Logic
window.resetUpload = (inputId) => {
    const input = document.getElementById(inputId);
    if (!input) return;

    const wrapper = input.parentElement;
    const preview = wrapper.querySelector('img');
    const content = wrapper.querySelector('div[id$="-content"]');
    const removeBtn = wrapper.querySelector('button');

    input.value = '';
    if (preview) {
        preview.classList.add('hidden');
        preview.src = '';
    }
    if (content) content.classList.remove('hidden');
    if (removeBtn) removeBtn.classList.add('hidden');
    wrapper.classList.remove('border-indigo-500');

    // Prevent event bubbling if needed
    if (typeof event !== 'undefined' && event) {
        event.stopPropagation();
    }
};

window.createTravel = async () => {
    const title = document.getElementById('travel-title').value;
    const description = document.getElementById('travel-desc').value;
    const fileInput = document.getElementById('travel-image');
    const file = fileInput.files[0];

    if (!title) return alert("Title is required");

    let imageUrl = null;
    try {
        console.log("Processing file:", file); // Debug log
        imageUrl = await processImage(file);
    } catch (e) {
        console.error("Image Processing Error:", e);
        alert("Failed to process image: " + (e.message || e));
        return;
    }

    try {
        if (await createTravel(title, description, imageUrl)) {
            document.getElementById('travel-title').value = '';
            document.getElementById('travel-desc').value = '';
            resetUpload('travel-image'); // New generic reset
            document.getElementById('create-travel-modal').classList.add('hidden');
            renderTravels();
        } else {
            alert("Failed to create trip (Server Error)");
        }
    } catch (e) {
        console.error("API Error:", e);
        alert("Failed to create trip (Network Error): " + e.message);
    }
};

window.createSchedule = async () => {
    const travelId = document.getElementById('current-travel-id').value;
    const date = document.getElementById('sched-date').value;
    const time = document.getElementById('sched-time').value;
    const place = document.getElementById('sched-place').value;
    const memo = document.getElementById('sched-memo').value;
    const fileInput = document.getElementById('sched-image');
    const file = fileInput.files[0];

    if (!date || !place) return alert("Date and Place are required");

    let imageUrl = null;
    if (file) {
        try {
            imageUrl = await processImage(file);
        } catch (e) {
            console.error(e);
            return alert("Failed to process image");
        }
    }

    if (await createSchedule(travelId, date, time, place, memo, imageUrl)) {
        document.getElementById('sched-place').value = '';
        document.getElementById('sched-memo').value = '';
        resetUpload('sched-image');
        renderSchedules(travelId);
    } else {
        alert('Failed to add schedule');
    }
};

window.closeModal = () => {
    document.getElementById('schedule-modal').classList.add('hidden');
};

// Init
initRouter({
    onDashboard: () => {
        updateUserGreeting();
        renderTravels();
        renderRecommendations();

        // Auto-refresh recommendations every 10 seconds
        if (window.recInterval) clearInterval(window.recInterval);
        window.recInterval = setInterval(renderRecommendations, 10000);
    }
});
