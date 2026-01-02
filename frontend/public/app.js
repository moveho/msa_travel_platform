const payload = JSON.parse(atob(token.split('.')[1]));
document.getElementById('user-greeting').textContent = `Hello, ${payload.sub}`;
    } catch (e) {
    document.getElementById('user-greeting').textContent = 'Welcome';
}
}

// --- Auth Functions ---
async function signup() {
    const username = document.getElementById('signup-username').value;
    const password = document.getElementById('signup-password').value;

    if (!username || !password) {
        alert("Please enter both username and password.");
        return;
    }

    try {
        const res = await fetch(`${API_AUTH}/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (res.ok) {
            alert('Account created! Please log in.');
            window.location.hash = '#login';
            document.getElementById('signup-username').value = '';
            document.getElementById('signup-password').value = '';
        } else {
            const text = await res.text();
            try {
                const data = JSON.parse(text);
                alert(data.detail || 'Signup failed');
            } catch {
                alert(`Error: ${text.substring(0, 100)}`);
            }
        }
    } catch (e) {
        console.error(e);
        alert('Network Error');
    }
}

async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        alert("Please enter both username and password.");
        return;
    }

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const res = await fetch(`${API_AUTH}/token`, {
            method: 'POST',
            body: formData
        });
        if (res.ok) {
            const data = await res.json();
            token = data.access_token;
            localStorage.setItem('token', token);
            window.location.hash = '#dashboard';
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
        } else {
            alert('Invalid username or password');
        }
    } catch (e) {
        console.error(e);
        alert('Network Error');
    }
}

function logout() {
    token = null;
    localStorage.removeItem('token');
    window.location.hash = '#login';
}

// --- Travel Functions ---
async function loadTravels() {
    const res = await fetch(`${API_TRAVEL}/travels`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        const travels = await res.json();
        const list = document.getElementById('travel-list');
        const emptyState = document.getElementById('empty-state');

        if (travels.length === 0) {
            list.innerHTML = '';
            emptyState.classList.remove('hidden');
        } else {
            emptyState.classList.add('hidden');
            list.innerHTML = travels.map(t => `
                <div class="bg-white rounded-xl shadow-sm hover:shadow-lg transition duration-300 overflow-hidden border border-gray-100 flex flex-col">
                    <div class="h-32 bg-gradient-to-r from-indigo-400 to-purple-500 flex items-center justify-center">
                        <span class="text-white text-4xl opacity-50">✈️</span>
                    </div>
                    <div class="p-6 flex-grow">
                        <div class="flex justify-between items-start mb-2">
                            <h3 class="text-xl font-bold text-gray-900 truncate">${t.title}</h3>
                        </div>
                        <p class="text-gray-500 text-sm mb-4 line-clamp-2">${t.description || 'No description'}</p>
                    </div>
                    <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
                        <button onclick="openSchedule(${t.id})" class="text-indigo-600 font-medium hover:text-indigo-800 text-sm">View Itinerary →</button>
                        <button onclick="deleteTravel(${t.id})" class="text-gray-400 hover:text-red-500 transition">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </div>
                </div>
            `).join('');
        }
    } else if (res.status === 401) {
        logout();
    }
}

async function createTravel() {
    const title = document.getElementById('travel-title').value;
    const description = document.getElementById('travel-desc').value;

    if (!title) return alert("Title is required");

    const res = await fetch(`${API_TRAVEL}/travels`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ title, description })
    });

    if (res.ok) {
        document.getElementById('travel-title').value = '';
        document.getElementById('travel-desc').value = '';
        document.getElementById('create-travel-modal').classList.add('hidden');
        loadTravels();
    }
}

async function deleteTravel(id) {
    if (!confirm('Are you sure you want to delete this trip?')) return;
    await fetch(`${API_TRAVEL}/travels/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    loadTravels();
}

// --- Schedule Functions ---
async function openSchedule(travelId) {
    document.getElementById('current-travel-id').value = travelId;
    document.getElementById('schedule-modal').classList.remove('hidden');
    loadSchedules(travelId);
}

function closeModal() {
    document.getElementById('schedule-modal').classList.add('hidden');
}

async function loadSchedules(travelId) {
    const res = await fetch(`${API_SCHEDULE}/schedules?travel_id=${travelId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        const schedules = await res.json();
        schedules.sort((a, b) => new Date(a.date) - new Date(b.date));

        const list = document.getElementById('schedule-list');
        list.innerHTML = schedules.map((s, index) => `
            <li class="relative pb-8">
                ${index !== schedules.length - 1 ? '<span class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>' : ''}
                <div class="relative flex space-x-3">
                    <div>
                        <span class="h-8 w-8 rounded-full bg-indigo-500 flex items-center justify-center ring-8 ring-white">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </span>
                    </div>
                    <div class="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                            <p class="text-sm text-gray-500">${s.date} </p>
                            <p class="text-md font-bold text-gray-900">${s.place}</p>
                            <p class="text-sm text-gray-600 mt-1">${s.memo || ''}</p>
                        </div>
                        <div class="text-right text-sm whitespace-nowrap text-gray-500">
                            <button onclick="deleteSchedule(${s.id})" class="text-red-400 hover:text-red-600">Delete</button>
                        </div>
                    </div>
                </div>
            </li>
        `).join('');
    }
}

async function createSchedule() {
    const travelId = document.getElementById('current-travel-id').value;
    const date = document.getElementById('sched-date').value;
    const place = document.getElementById('sched-place').value;
    const memo = document.getElementById('sched-memo').value;

    if (!date || !place) return alert("Date and Place are required");

    const res = await fetch(`${API_SCHEDULE}/schedules`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            travel_id: parseInt(travelId),
            date,
            place,
            memo
        })
    });

    if (res.ok) {
        document.getElementById('sched-place').value = '';
        document.getElementById('sched-memo').value = '';
        loadSchedules(travelId);
    } else {
        alert('Failed to add schedule');
    }
}

async function deleteSchedule(id) {
    const travelId = document.getElementById('current-travel-id').value;
    await fetch(`${API_SCHEDULE}/schedules/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    loadSchedules(travelId);
}
