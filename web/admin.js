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
    switchTab('analytics');
    loadLocations();
    loadEmailSettings();
    loadRecipients();
    loadAnalytics().then(() => populateFreqLocationDropdown());
    loadCategoryOrder();
    loadUILabels();
    loadBranding();
    loadAppSettings();
}

// --- Analytics ---
let analyticsData = null;
let currentAnalyticsCategory = null;

async function loadAnalytics() {
    try {
        const res = await adminApiFetch(`${API_BASE}/admin/aggregation`);
        const data = await res.json();
        if (data.success) {
            analyticsData = data;

            const select = document.getElementById('analyticsLocationSelect');
            select.innerHTML = '<option value="">All Locations</option>' +
                data.locations.map(loc => `<option value="${escapeHtml(loc.pin)}">${escapeHtml(loc.name)}</option>`).join('');

            renderAnalyticsCategoryTabs();
            if (data.categories.length > 0) {
                currentAnalyticsCategory = data.categories[0].id;
            }
            renderAnalytics();
        }
    } catch (e) {
        console.error('Failed to load analytics:', e);
    }
}

function renderAnalyticsCategoryTabs() {
    if (!analyticsData) return;
    const tabsContainer = document.getElementById('analyticsCategoryTabs');
    tabsContainer.innerHTML = analyticsData.categories.map(cat => `
        <button onclick="setAnalyticsCategory('${escapeHtml(cat.id)}')"
                class="analytics-cat-tab px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                       ${cat.id === currentAnalyticsCategory ? 'border-falcone-red text-falcone-red' : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border)]'}"
                data-cat-id="${escapeHtml(cat.id)}">
            ${escapeHtml(cat.label)}
        </button>
    `).join('');
}

window.setAnalyticsCategory = function(catId) {
    currentAnalyticsCategory = catId;
    document.querySelectorAll('.analytics-cat-tab').forEach(el => {
        if (el.getAttribute('data-cat-id') === catId) {
            el.classList.add('border-falcone-red', 'text-falcone-red');
            el.classList.remove('border-transparent', 'text-[var(--color-text-secondary)]');
        } else {
            el.classList.remove('border-falcone-red', 'text-falcone-red');
            el.classList.add('border-transparent', 'text-[var(--color-text-secondary)]');
        }
    });
    renderAnalytics();
}

window.renderAnalytics = function() {
    if (!analyticsData || !currentAnalyticsCategory) return;

    const locationPin = document.getElementById('analyticsLocationSelect').value;
    const content = document.getElementById('analyticsContent');
    const category = analyticsData.categories.find(c => c.id === currentAnalyticsCategory);

    if (!category) return;

    // Calculate frequencies
    let itemFreqs = {};
    category.items.forEach(item => { itemFreqs[item.id] = { name: item.name, freq: 0 }; });

    if (locationPin) {
        const freqs = analyticsData.frequencies[locationPin] || {};
        for (const [itemId, freq] of Object.entries(freqs)) {
            if (itemFreqs[itemId]) itemFreqs[itemId].freq += freq;
        }
    } else {
        // All locations
        for (const freqs of Object.values(analyticsData.frequencies)) {
            for (const [itemId, freq] of Object.entries(freqs)) {
                if (itemFreqs[itemId]) itemFreqs[itemId].freq += freq;
            }
        }
    }

    // Sort items by frequency descending, then name ascending
    const sortedItems = Object.values(itemFreqs).sort((a, b) => {
        if (b.freq !== a.freq) return b.freq - a.freq;
        return a.name.localeCompare(b.name);
    });

    if (sortedItems.length === 0) {
        content.innerHTML = '<div class="text-[var(--color-text-secondary)] text-sm text-center py-4">No items in this category.</div>';
        return;
    }

    content.innerHTML = `
        <div class="grid grid-cols-[1fr_auto] gap-4 px-4 py-2 bg-[var(--color-bg-nav)] border-b border-[var(--color-border)] text-xs font-bold text-[var(--color-text-secondary)] uppercase tracking-wider rounded-t-lg">
            <div>Item Name</div>
            <div class="text-right">Times Ordered</div>
        </div>
        ${sortedItems.map((item, i) => `
            <div class="grid grid-cols-[1fr_auto] gap-4 px-4 py-3 border-b border-[var(--color-border)] hover:bg-[var(--color-border)]/50 transition-colors ${i === sortedItems.length - 1 ? 'rounded-b-lg border-b-0' : ''}">
                <div class="font-medium truncate" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
                <div class="font-bold font-mono text-falcone-red text-right w-16">${item.freq}</div>
            </div>
        `).join('')}
    `;
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

// --- Inventory / Upload ---
let _selectedMasterFile = null;

function handleMasterFileSelect(input) {
    const file = input.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
        alert('Please select an .xlsx file.');
        input.value = '';
        return;
    }
    _selectedMasterFile = file;
    document.getElementById('uploadFileName').textContent = file.name;
    document.getElementById('uploadSelectedFile').classList.remove('hidden');
    document.getElementById('btnUpload').disabled = false;
    if (window.lucide) lucide.createIcons();
}

function handleMasterDrop(event) {
    event.preventDefault();
    document.getElementById('uploadDropZone').classList.remove('border-falcone-red', 'bg-falcone-red/5');
    const file = event.dataTransfer.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
        alert('Please drop an .xlsx file.');
        return;
    }
    _selectedMasterFile = file;
    document.getElementById('uploadFileName').textContent = file.name;
    document.getElementById('uploadSelectedFile').classList.remove('hidden');
    document.getElementById('btnUpload').disabled = false;
    if (window.lucide) lucide.createIcons();
}

function clearMasterFile() {
    _selectedMasterFile = null;
    document.getElementById('masterFileInput').value = '';
    document.getElementById('uploadSelectedFile').classList.add('hidden');
    document.getElementById('uploadFileName').textContent = '';
    document.getElementById('btnUpload').disabled = true;
}

async function uploadMasterFile() {
    if (!_selectedMasterFile) return;
    const btn = document.getElementById('btnUpload');
    const resultEl = document.getElementById('rebuildResult');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Uploading...';
    if (window.lucide) lucide.createIcons();
    resultEl.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('file', _selectedMasterFile);
        const res = await adminApiFetch(`${API_BASE}/admin/upload-master`, {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        resultEl.textContent = data.message;
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
        if (data.success) clearMasterFile();
    } catch (e) {
        resultEl.textContent = 'Upload failed. Check server logs.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    } finally {
        btn.disabled = !_selectedMasterFile;
        btn.innerHTML = '<i data-lucide="upload" class="w-4 h-4"></i> Upload &amp; Rebuild';
        if (window.lucide) lucide.createIcons();
    }
}

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
        btn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i> Rebuild from Existing File';
        if (window.lucide) lucide.createIcons();
    }
}

// --- Category Order ---
let draggedCategory = null;

async function loadCategoryOrder() {
    const listEl = document.getElementById('categoryOrderList');
    try {
        const res = await adminApiFetch(`${API_BASE}/admin/category-order`);
        const data = await res.json();
        if (data.success) {
            renderCategoryOrderList(data.categories);
        }
    } catch (e) {
        listEl.innerHTML = '<div class="text-falcone-red text-sm">Failed to load categories.</div>';
    }
}

function renderCategoryOrderList(categories) {
    const listEl = document.getElementById('categoryOrderList');
    if (categories.length === 0) {
        listEl.innerHTML = '<div class="text-[var(--color-text-secondary)] text-sm text-center py-4 col-span-full">No categories found.</div>';
        return;
    }
    listEl.innerHTML = categories.map((cat, idx) => {
        const isLucideIcon = /^[a-z][a-z0-9-]*$/.test(cat.icon || 'box');
        const iconHtml = isLucideIcon
            ? `<i data-lucide="${cat.icon || 'box'}" class="category-icon text-${cat.color || 'gray'}-400"></i>`
            : `<span class="category-icon" style="line-height:1; display:flex; align-items:center; justify-content:center;">${cat.icon || '📦'}</span>`;
        return `
        <div class="category-drag-item category-btn cursor-move relative"
             draggable="true"
             data-id="${escapeHtml(cat.id)}">
            <div class="pointer-events-none w-full h-full flex flex-col">
                ${iconHtml}
                <div class="category-title-wrapper flex-1">
                    <span class="category-title">${escapeHtml(cat.label || cat.id)}</span>
                </div>
            </div>
            <div class="absolute top-2 right-2 bg-[var(--color-bg-nav)] rounded-full w-5 h-5 flex items-center justify-center text-[var(--color-text-secondary)] text-[10px] font-mono font-bold border border-[var(--color-border)] shadow-sm pointer-events-none index-badge">${idx + 1}</div>
        </div>
        `;
    }).join('');

    // Add drag and drop event listeners
    const items = listEl.querySelectorAll('.category-drag-item');
    items.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragend', handleDragEnd);
    });

    if (window.lucide) lucide.createIcons();
}

function handleDragStart(e) {
    draggedCategory = this;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
    this.classList.add('opacity-50');
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault(); // Necessary. Allows us to drop.
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation(); // Stops the browser from redirecting.
    }
    if (draggedCategory !== this) {
        const list = document.getElementById('categoryOrderList');
        const items = Array.from(list.querySelectorAll('.category-drag-item'));
        const draggedIdx = items.indexOf(draggedCategory);
        const droppedIdx = items.indexOf(this);

        if (draggedIdx < droppedIdx) {
            this.parentNode.insertBefore(draggedCategory, this.nextSibling);
        } else {
            this.parentNode.insertBefore(draggedCategory, this);
        }

        // Update numbers
        const newItems = Array.from(list.querySelectorAll('.category-drag-item'));
        newItems.forEach((item, idx) => {
            const badge = item.querySelector('.index-badge');
            if (badge) badge.textContent = idx + 1;
        });
    }
    return false;
}

function handleDragEnd(e) {
    this.classList.remove('opacity-50');
}

async function saveCategoryOrder() {
    const listEl = document.getElementById('categoryOrderList');
    const items = listEl.querySelectorAll('.category-drag-item');
    const order = Array.from(items).map(item => item.getAttribute('data-id'));

    const resultEl = document.getElementById('categoryOrderResult');
    resultEl.classList.add('hidden');

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/category-order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order }),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? 'Category order saved.' : 'Failed to save.';
        resultEl.className = `p-3 rounded-lg text-sm mt-4 ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm mt-4 bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}


// --- UI Labels ---
async function loadUILabels() {
    try {
        const res = await adminApiFetch(`${API_BASE}/ui-labels`);
        const data = await res.json();
        if (data.success && data.labels) {
            document.querySelectorAll('.ui-label-input').forEach(input => {
                const key = input.getAttribute('data-key');
                if (data.labels[key]) {
                    input.value = data.labels[key];
                } else {
                    input.value = '';
                }
            });
        }
    } catch (e) {
        console.error('Failed to load UI labels:', e);
    }
}

async function saveUILabels() {
    const labels = {};
    document.querySelectorAll('.ui-label-input').forEach(input => {
        const key = input.getAttribute('data-key');
        const val = input.value.trim();
        if (val) {
            labels[key] = val;
        }
    });

    const resultEl = document.getElementById('uiLabelsResult');
    resultEl.classList.add('hidden');

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/ui-labels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ labels }),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? 'UI labels saved.' : 'Failed to save.';
        resultEl.className = `p-3 rounded-lg text-sm mt-4 ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm mt-4 bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}


// --- Branding ---
async function loadBranding() {
    try {
        const res = await adminApiFetch(`${API_BASE}/branding`);
        const data = await res.json();
        if (data.success && data.branding) {
            document.querySelectorAll('.branding-input').forEach(input => {
                const key = input.getAttribute('data-key');
                if (data.branding[key]) {
                    input.value = data.branding[key];
                } else {
                    input.value = '';
                }
            });
        }
    } catch (e) {
        console.error('Failed to load branding:', e);
    }
}

async function saveBranding() {
    const branding = {};
    document.querySelectorAll('.branding-input').forEach(input => {
        const key = input.getAttribute('data-key');
        const val = input.value.trim();
        if (val) {
            branding[key] = val;
        }
    });

    const resultEl = document.getElementById('brandingResult');
    resultEl.classList.add('hidden');

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/branding`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ branding }),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? 'Branding settings saved.' : 'Failed to save.';
        resultEl.className = `p-3 rounded-lg text-sm mt-4 ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm mt-4 bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}

let _selectedFaviconFile = null;

function handleFaviconSelect(input) {
    const file = input.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.png')) {
        alert('Please select a .png image file.');
        input.value = '';
        return;
    }

    // Check image dimensions client side if needed
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            if (img.width > 500 || img.height > 500) {
                alert('Image must be 500x500 pixels or smaller.');
                input.value = '';
                return;
            }
            if (img.width !== img.height) {
                alert('Warning: Image is not square, it may appear distorted.');
            }

            _selectedFaviconFile = file;
            document.getElementById('currentFaviconPreview').src = e.target.result;
            const fnameEl = document.getElementById('faviconFileName');
            fnameEl.textContent = file.name;
            fnameEl.classList.remove('hidden');
            document.getElementById('btnUploadFavicon').disabled = false;
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function uploadFavicon() {
    if (!_selectedFaviconFile) return;

    const btn = document.getElementById('btnUploadFavicon');
    const resultEl = document.getElementById('faviconResult');

    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Uploading...';
    if (window.lucide) lucide.createIcons();
    resultEl.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('file', _selectedFaviconFile);

        const res = await adminApiFetch(`${API_BASE}/admin/upload-favicon`, {
            method: 'POST',
            body: formData,
        });

        const data = await res.json();
        resultEl.textContent = data.success ? 'Favicon updated successfully. Reload page to see changes.' : 'Failed to update favicon.';
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');

        if (data.success) {
            _selectedFaviconFile = null;
            document.getElementById('faviconInput').value = '';
            document.getElementById('faviconFileName').classList.add('hidden');

            // Force refresh image cache by adding timestamp
            const preview = document.getElementById('currentFaviconPreview');
            preview.src = `/assets/icon-192.png?t=${new Date().getTime()}`;
        }
    } catch (e) {
        resultEl.textContent = 'Upload failed. Check server logs.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    } finally {
        btn.innerHTML = '<i data-lucide="upload" class="w-4 h-4"></i> Upload';
        btn.disabled = !_selectedFaviconFile;
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


// --- Color Presets ---
const COLOR_PRESETS = [
    { name: "Crimson Red", hex: "#8e1f1f" },
    { name: "Tomato", hex: "#db594b" },
    { name: "Burnt Orange", hex: "#c2410c" },
    { name: "Amber", hex: "#d97706" },
    { name: "Gold", hex: "#ca8a04" },
    { name: "Lime Green", hex: "#65a30d" },
    { name: "Emerald", hex: "#059669" },
    { name: "Teal", hex: "#0d9488" },
    { name: "Cyan", hex: "#0891b2" },
    { name: "Sky Blue", hex: "#0284c7" },
    { name: "Royal Blue", hex: "#2563eb" },
    { name: "Indigo", hex: "#4f46e5" },
    { name: "Violet", hex: "#7c3aed" },
    { name: "Purple", hex: "#9333ea" },
    { name: "Fuchsia", hex: "#c026d3" },
    { name: "Rose", hex: "#e11d48" },
    { name: "Pure White", hex: "#ffffff" },
    { name: "Warm White", hex: "#f7f3ee" },
    { name: "Light Gray", hex: "#d4d4d4" },
    { name: "Medium Gray", hex: "#737373" },
    { name: "Dark Gray", hex: "#404040" },
    { name: "Charcoal", hex: "#262626" },
    { name: "Near Black", hex: "#151515" },
    { name: "Deep Black", hex: "#0c0c0c" },
];

function populateColorDropdowns() {
    document.querySelectorAll('.color-select').forEach(select => {
        select.innerHTML = '<option value="">Default</option>' +
            COLOR_PRESETS.map(c =>
                `<option value="${c.hex}" style="background:${c.hex};color:${isLight(c.hex)?'#000':'#fff'}">${c.name} (${c.hex})</option>`
            ).join('');
    });
}

function isLight(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 128;
}


// --- App Settings ---
async function loadAppSettings() {
    try {
        const resLangs = await adminApiFetch(`${API_BASE}/languages`);
        const dataLangs = await resLangs.json();
        if (dataLangs.success && dataLangs.languages) {
            const langSel = document.getElementById('settingsOutputLang');
            if (langSel) {
                langSel.innerHTML = dataLangs.languages.map(l =>
                    `<option value="${l.code}">${escapeHtml(l.name)}</option>`
                ).join('');
            }
        }

        const res = await adminApiFetch(`${API_BASE}/admin/settings`);
        const data = await res.json();
        if (data.success && data.settings) {
            const langSel = document.getElementById('settingsOutputLang');
            if (langSel) langSel.value = data.settings.output_language || 'english';
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function saveAppSettings() {
    const resultEl = document.getElementById('settingsResult');
    resultEl.classList.add('hidden');
    const outputLang = document.getElementById('settingsOutputLang').value;

    try {
        const res = await adminApiFetch(`${API_BASE}/admin/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ output_language: outputLang }),
        });
        const data = await res.json();
        resultEl.textContent = data.success ? 'Settings saved.' : 'Failed to save.';
        resultEl.className = `p-3 rounded-lg text-sm ${data.success ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-falcone-red border border-red-700'}`;
        resultEl.classList.remove('hidden');
    } catch (e) {
        resultEl.textContent = 'Request failed.';
        resultEl.className = 'p-3 rounded-lg text-sm bg-red-900/30 text-falcone-red border border-red-700';
        resultEl.classList.remove('hidden');
    }
}


// --- Downloads ---
async function downloadMasterFile() {
    try {
        const res = await adminApiFetch(`${API_BASE}/admin/download-master`);
        if (!res.ok) {
            alert('No Master.xlsx file found on server.');
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Master.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('Download failed.');
    }
}

async function downloadFrequencyReport() {
    const pin = document.getElementById('freqReportLocation').value;
    try {
        const url = `${API_BASE}/admin/download-frequency-report${pin ? '?location_pin=' + encodeURIComponent(pin) : ''}`;
        const res = await adminApiFetch(url);
        if (!res.ok) {
            alert('Failed to generate report.');
            return;
        }
        const blob = await res.blob();
        const disposition = res.headers.get('content-disposition') || '';
        let filename = 'Frequency Report.xlsx';
        const match = disposition.match(/filename="(.+?)"/);
        if (match) filename = match[1];
        const dlUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = dlUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(dlUrl);
    } catch (e) {
        alert('Download failed.');
    }
}

function populateFreqLocationDropdown() {
    if (!analyticsData) return;
    const select = document.getElementById('freqReportLocation');
    if (!select) return;
    select.innerHTML = '<option value="">All Locations</option>' +
        (analyticsData.locations || []).map(loc =>
            `<option value="${escapeHtml(loc.pin)}">${escapeHtml(loc.name)}</option>`
        ).join('');
}


// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    populateColorDropdowns();
    if (adminToken) {
        showAdminApp();
    }
    if (window.lucide) lucide.createIcons();
});
