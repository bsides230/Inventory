// Admin Panel Logic

const API_BASE = '/api';
let adminToken = sessionStorage.getItem('admin_token') || null;

async function adminApiFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (adminToken) {
        options.headers['Authorization'] = `Bearer ${adminToken}`;
    }
    const res = await fetch(url, options);
    if (res.status === 401 || res.status === 403) {
        adminLogout();
        throw new Error('Session expired');
    }
    return res;
}

async function adminLogin() {
    const password = document.getElementById('adminPasswordInput').value;
    const errEl = document.getElementById('adminLoginError');
    errEl.classList.add('hidden');

    try {
        const res = await fetch(`${API_BASE}/admin/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password }),
        });
        const data = await res.json();
        if (res.ok && data.token) {
            adminToken = data.token;
            sessionStorage.setItem('admin_token', data.token);
            showAdminApp();
        } else {
            errEl.textContent = data.detail || 'Incorrect password.';
            errEl.classList.remove('hidden');
        }
    } catch (e) {
        errEl.textContent = 'Network error. Please try again.';
        errEl.classList.remove('hidden');
    }
}

function adminLogout() {
    adminToken = null;
    sessionStorage.removeItem('admin_token');
    document.getElementById('adminLoginScreen').classList.remove('hidden');
    document.getElementById('adminApp').classList.add('hidden');
}

function showAdminApp() {
    document.getElementById('adminLoginScreen').classList.add('hidden');
    document.getElementById('adminApp').classList.remove('hidden');
    switchTab('inventory');
    loadLocations();
    loadEmailSettings();
    loadRecipients();
}

// --- Tab switching ---
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.admin-tab').forEach(el => el.classList.remove('active'));

    const tabEl = document.getElementById(`tab-${tabName}`);
    if (tabEl) tabEl.classList.remove('hidden');
    document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

    if (window.lucide) lucide.createIcons();
}

// --- Inventory ---
async function rebuildInventory() {
    const btn = document.getElementById('btnRebuild');
    const resultEl = document.getElementById('rebuildResult');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Rebuilding...';
    if (window.lucide) lucide.createIcons();
    resultEl.classList.add('hidden');

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/rebuild-inventory`, { method: 'POST' });
        const data = await res.json();
        resultEl.textContent = data.message;
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed. Check server logs.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i> Rebuild Inventory Now';
        if (window.lucide) lucide.createIcons();
    }
}

// --- Locations ---
async function loadLocations() {
    const listEl = document.getElementById('locationsList');
    try {
        const res = await adminApiFetch(`${API_BASE}/admin/locations`);
        const data = await res.json();
        if (data.success) {
            renderLocationsList(data.locations);
        }
    } catch (e) {
        listEl.innerHTML = '<div class="text-falcone-red text-sm">Failed to load locations.</div>';
    }
}

function renderLocationsList(locations) {
    const listEl = document.getElementById('locationsList');
    if (locations.length === 0) {
        listEl.innerHTML = '<div class="text-[var(--color-text-secondary)] text-sm text-center py-4">No locations configured yet.</div>';
        return;
    }
    listEl.innerHTML = locations.map(loc => `
        <div class="flex items-center justify-between bg-[var(--color-bg-body)] rounded-lg border border-[var(--color-border)] px-4 py-3">
            <div class="flex items-center gap-4">
                <div class="bg-falcone-red/10 border border-falcone-red/30 rounded-lg px-3 py-1.5 text-center">
                    <div class="text-xs text-[var(--color-text-secondary)] mb-0.5">PIN</div>
                    <div class="text-lg font-bold text-falcone-red font-mono tracking-widest">${escapeHtml(loc.pin)}</div>
                </div>
                <div class="font-medium">${escapeHtml(loc.name)}</div>
            </div>
            <button onclick="deleteLocation('${escapeHtml(loc.pin)}')" class="p-2 text-[var(--color-text-secondary)] hover:text-falcone-red transition-colors rounded-lg">
                <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
        </div>
    `).join('');
    if (window.lucide) lucide.createIcons();
}

async function addLocation() {
    const pin = document.getElementById('newPin').value.trim();
    const name = document.getElementById('newLocationName').value.trim();
    const errEl = document.getElementById('addLocationError');
    errEl.classList.add('hidden');

    if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
        errEl.textContent = 'PIN must be exactly 4 digits.';
        errEl.classList.remove('hidden');
        return;
    }
    if (!name) {
        errEl.textContent = 'Location name is required.';
        errEl.classList.remove('hidden');
        return;
    }

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/locations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin, name }),
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('newPin').value = '';
            document.getElementById('newLocationName').value = '';
            loadLocations();
        } else {
            errEl.textContent = data.detail || 'Failed to add location.';
            errEl.classList.remove('hidden');
        }
    } catch (e) {
        errEl.textContent = 'Request failed.';
        errEl.classList.remove('hidden');
    }
}

async function deleteLocation(pin) {
    if (!confirm(`Remove PIN ${pin}? Staff using this PIN will be locked out.`)) return;
    try {
        await adminApiFetch(`${API_BASE}/admin/locations/${pin}`, { method: 'DELETE' });
        loadLocations();
    } catch (e) {
        alert('Failed to delete location.');
    }
}

// --- Email Settings ---
async function loadEmailSettings() {
    try {
        const res = await adminApiFetch(`${API_BASE}/admin/email-settings`);
        const data = await res.json();
        if (data.success) {
            const s = data.settings;
            document.getElementById('smtpHost').value = s.smtp_host || '';
            document.getElementById('smtpPort').value = s.smtp_port || '1025';
            document.getElementById('smtpUsername').value = s.smtp_username || '';
            document.getElementById('smtpPassword').value = '';
            document.getElementById('smtpSenderEmail').value = s.smtp_sender_email || '';
            document.getElementById('smtpUseTls').checked = s.smtp_use_tls === 'true';
        }
    } catch (e) {
        console.error('Failed to load email settings:', e);
    }
}

async function saveEmailSettings() {
    const resultEl = document.getElementById('emailSettingsResult');
    resultEl.classList.add('hidden');

    const body = {
        smtp_host: document.getElementById('smtpHost').value.trim(),
        smtp_port: parseInt(document.getElementById('smtpPort').value) || 1025,
        smtp_username: document.getElementById('smtpUsername').value.trim() || null,
        smtp_password: document.getElementById('smtpPassword').value || '***',
        smtp_use_tls: document.getElementById('smtpUseTls').checked,
        smtp_sender_email: document.getElementById('smtpSenderEmail').value.trim(),
    };

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/email-settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? 'Email settings saved.' : 'Failed to save settings.';
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}

// --- Recipients ---
async function loadRecipients() {
    try {
        const res = await adminApiFetch(`${API_BASE}/admin/recipients`);
        const data = await res.json();
        if (data.success) {
            document.getElementById('recipientsList').value = data.recipients.join('\n');
        }
    } catch (e) {
        console.error('Failed to load recipients:', e);
    }
}

async function saveRecipients() {
    const resultEl = document.getElementById('recipientsResult');
    resultEl.classList.add('hidden');

    const raw = document.getElementById('recipientsList').value;
    const recipients = raw.split('\n').map(r => r.trim()).filter(r => r);

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/recipients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipients }),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? `Saved ${recipients.length} recipient(s).` : 'Failed to save.';
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}

// --- Password ---
async function changePassword() {
    const resultEl = document.getElementById('passwordResult');
    resultEl.classList.add('hidden');

    const body = {
        current_password: document.getElementById('currentPassword').value,
        new_password: document.getElementById('newPassword').value,
    };

    if (!body.new_password || body.new_password.length < 4) {
        resultEl.textContent = 'New password must be at least 4 characters.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
        return;
    }

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? 'Password updated successfully.' : (data.detail || 'Failed to update password.');
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
        if (data.success) {
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
        }
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}

function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    if (adminToken) {
        showAdminApp();
    }
    if (window.lucide) lucide.createIcons();
});
