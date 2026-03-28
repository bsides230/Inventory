// Falcone's Pizza Inventory - Frontend App Logic

const API_BASE = '/api';

// --- i18n ---
const translations = {
    en: {
        appTitle: "Inventory",
        langToggle: "Español",
        itemsCount: "items",
        labelSubmitOrder: "Submit",
        labelOrderModalTitle: "Submit Order",
        labelOrderDate: "Order Date",
        labelRushOrder: "Rush Order (Urgent)",
        labelNeededBy: "Needed By Date",
        labelCancel: "Cancel",
        labelConfirm: "Confirm Order",
        each: "each",
        case: "case",
        offlineBannerText: "You are offline. Cached data is available; submitting orders requires a connection.",
        installBannerText: "Install this app for faster access from your home screen.",
        iosInstallText: "On iPhone: tap Share, then Add to Home Screen.",
        updateBannerText: "A new app update is ready.",
        installCta: "Install",
        dismissCta: "Dismiss",
        gotItCta: "Got it",
        refreshCta: "Refresh",
        pinPrompt: "Enter your location PIN to continue",
        invalidPin: "Invalid PIN. Please try again.",
    },
    es: {
        appTitle: "Inventario",
        langToggle: "English",
        itemsCount: "artículos",
        labelSubmitOrder: "Enviar",
        labelOrderModalTitle: "Enviar Pedido",
        labelOrderDate: "Fecha del Pedido",
        labelRushOrder: "Pedido Urgente",
        labelNeededBy: "Fecha Requerida",
        labelCancel: "Cancelar",
        labelConfirm: "Confirmar Pedido",
        each: "c/u",
        case: "caja",
        offlineBannerText: "No tienes conexión. Puedes usar datos en caché; enviar pedidos requiere internet.",
        installBannerText: "Instala esta app para abrirla más rápido desde tu pantalla principal.",
        iosInstallText: "En iPhone: toca Compartir y luego Añadir a pantalla de inicio.",
        updateBannerText: "Hay una actualización lista para instalar.",
        installCta: "Instalar",
        dismissCta: "Cerrar",
        gotItCta: "Entendido",
        refreshCta: "Actualizar",
        pinPrompt: "Ingresa el PIN de tu ubicación para continuar",
        invalidPin: "PIN inválido. Inténtalo de nuevo.",
    }
};

// --- State ---
const state = {
    lang: localStorage.getItem('falcone_lang') || 'en',
    theme: localStorage.getItem('falcone_theme') || 'dark',
    currentCategory: null,
    inventory: {},
    categories: [],
    deferredInstallPrompt: null,
    token: localStorage.getItem('falcone_token') || null,
    locationName: localStorage.getItem('falcone_location') || null,
    locationPin: localStorage.getItem('falcone_pin') || null,
    currentDraftId: parseInt(localStorage.getItem('falcone_draft_id') || '0') || null,
    currentDraftName: localStorage.getItem('falcone_draft_name') || 'Draft',
    drafts: [],
    pinBuffer: '',
};

// --- DOM ---
const DOM = {
    pinScreen: document.getElementById('pinScreen'),
    pinScreenTitle: document.getElementById('pinScreenTitle'),
    pinScreenSubtitle: document.getElementById('pinScreenSubtitle'),
    pinError: document.getElementById('pinError'),
    appHeader: document.getElementById('appHeader'),
    dashboardView: document.getElementById('dashboardView'),
    categoryView: document.getElementById('categoryView'),
    btnBack: document.getElementById('btnBack'),
    btnToggleLangApp: document.getElementById('btnToggleLangApp'),
    btnToggleTheme: document.getElementById('btnToggleTheme'),
    appTitle: document.getElementById('appTitle'),
    locationBadge: document.getElementById('locationBadge'),
    categoryTitle: document.getElementById('categoryTitle'),
    categoryCount: document.getElementById('categoryCount'),
    itemList: document.getElementById('itemList'),
    btnSubmitOrder: document.getElementById('btnSubmitOrder'),
    orderModal: document.getElementById('orderModal'),
    orderModalLocation: document.getElementById('orderModalLocation'),
    orderDateInput: document.getElementById('orderDateInput'),
    rushOrderCheckbox: document.getElementById('rushOrderCheckbox'),
    neededByContainer: document.getElementById('neededByContainer'),
    neededByInput: document.getElementById('neededByInput'),
    btnCancelOrder: document.getElementById('btnCancelOrder'),
    btnConfirmOrder: document.getElementById('btnConfirmOrder'),
    orderModalError: document.getElementById('orderModalError'),
    offlineBanner: document.getElementById('offlineBanner'),
    offlineBannerText: document.getElementById('offlineBannerText'),
    installBanner: document.getElementById('installBanner'),
    installBannerText: document.getElementById('installBannerText'),
    iosInstallBanner: document.getElementById('iosInstallBanner'),
    iosInstallText: document.getElementById('iosInstallText'),
    updateBanner: document.getElementById('updateBanner'),
    updateBannerText: document.getElementById('updateBannerText'),
    btnInstallApp: document.getElementById('btnInstallApp'),
    btnDismissInstall: document.getElementById('btnDismissInstall'),
    btnDismissIosInstall: document.getElementById('btnDismissIosInstall'),
    btnRefreshApp: document.getElementById('btnRefreshApp'),
    draftSelectorWrapper: document.getElementById('draftSelectorWrapper'),
    btnDraftSelector: document.getElementById('btnDraftSelector'),
    draftDropdown: document.getElementById('draftDropdown'),
    draftList: document.getElementById('draftList'),
    currentDraftName: document.getElementById('currentDraftName'),
};

// --- PIN Auth ---
let pinBuffer = '';

window.pinKey = function(digit) {
    if (pinBuffer.length >= 4) return;
    pinBuffer += digit;
    updatePinDots();
    if (pinBuffer.length === 4) {
        setTimeout(() => submitPin(pinBuffer), 150);
    }
};

window.pinBackspace = function() {
    if (pinBuffer.length === 0) return;
    pinBuffer = pinBuffer.slice(0, -1);
    updatePinDots();
    DOM.pinError.classList.add('hidden');
};

function updatePinDots() {
    for (let i = 0; i < 4; i++) {
        const dot = document.getElementById(`pinDot${i}`);
        if (i < pinBuffer.length) {
            dot.classList.remove('border-[var(--color-border)]');
            dot.classList.add('bg-falcone-red', 'border-falcone-red');
        } else {
            dot.classList.remove('bg-falcone-red', 'border-falcone-red');
            dot.classList.add('border-[var(--color-border)]');
        }
    }
}

async function submitPin(pin) {
    try {
        const res = await fetch(`${API_BASE}/auth/pin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin }),
        });
        const data = await res.json();
        if (res.ok && data.token) {
            state.token = data.token;
            state.locationName = data.location_name;
            state.locationPin = data.pin;
            localStorage.setItem('falcone_token', data.token);
            localStorage.setItem('falcone_location', data.location_name);
            localStorage.setItem('falcone_pin', data.pin);
            pinBuffer = '';
            updatePinDots();
            DOM.pinError.classList.add('hidden');
            await initAppAfterAuth();
        } else {
            DOM.pinError.textContent = translations[state.lang].invalidPin;
            DOM.pinError.classList.remove('hidden');
            pinBuffer = '';
            updatePinDots();
        }
    } catch (e) {
        DOM.pinError.textContent = 'Network error. Please try again.';
        DOM.pinError.classList.remove('hidden');
        pinBuffer = '';
        updatePinDots();
    }
}

window.logout = function() {
    state.token = null;
    state.locationName = null;
    state.locationPin = null;
    state.currentDraftId = null;
    localStorage.removeItem('falcone_token');
    localStorage.removeItem('falcone_location');
    localStorage.removeItem('falcone_pin');
    localStorage.removeItem('falcone_draft_id');
    localStorage.removeItem('falcone_draft_name');
    showPinScreen();
};

function showPinScreen() {
    DOM.pinScreen.classList.remove('hidden');
    DOM.appHeader.classList.add('hidden');
}

function hidePinScreen() {
    DOM.pinScreen.classList.add('hidden');
    DOM.appHeader.classList.remove('hidden');
}

// --- API helpers ---
async function apiFetch(url, options = {}) {
    if (state.token) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${state.token}`;
    }
    try {
        const res = await fetch(url, options);
        if (res.status === 401) {
            logout();
            throw new Error('Session expired. Please log in again.');
        }
        return res;
    } catch (error) {
        if (!navigator.onLine) {
            DOM.offlineBanner?.classList.remove('hidden');
        }
        throw error;
    }
}

// --- Draft Management ---
async function loadDrafts() {
    try {
        const res = await apiFetch(`${API_BASE}/drafts`);
        const data = await res.json();
        if (data.success) {
            state.drafts = data.drafts;
            renderDraftDropdown();

            // If no draft selected or selected draft not in list, pick first
            if (state.drafts.length > 0) {
                const found = state.drafts.find(d => d.id === state.currentDraftId);
                if (!found) {
                    selectDraft(state.drafts[0].id, state.drafts[0].name);
                } else {
                    DOM.currentDraftName.textContent = found.name;
                }
            }

            DOM.draftSelectorWrapper.classList.remove('hidden');
        }
    } catch (e) {
        console.error('Failed to load drafts:', e);
    }
}

function renderDraftDropdown() {
    DOM.draftList.innerHTML = '';
    if (state.drafts.length === 0) {
        DOM.draftList.innerHTML = '<div class="px-3 py-2 text-sm text-[var(--color-text-secondary)]">No drafts yet</div>';
        return;
    }
    state.drafts.forEach(draft => {
        const el = document.createElement('div');
        el.className = `flex items-center justify-between px-3 py-2 hover:bg-[var(--color-border)] cursor-pointer transition-colors ${draft.id === state.currentDraftId ? 'bg-[var(--color-border)]' : ''}`;
        el.innerHTML = `
            <div onclick="selectDraft(${draft.id}, '${draft.name.replace(/'/g, "\\'")}')">
                <div class="text-sm font-medium flex items-center gap-2">
                    ${draft.id === state.currentDraftId ? '<i data-lucide="check" class="w-3 h-3 text-falcone-red"></i>' : ''}
                    ${escapeHtml(draft.name)}
                </div>
                <div class="text-xs text-[var(--color-text-secondary)]">${draft.item_count} item${draft.item_count !== 1 ? 's' : ''}</div>
            </div>
            <button onclick="event.stopPropagation(); deleteDraft(${draft.id})" class="p-1 text-[var(--color-text-secondary)] hover:text-falcone-red transition-colors rounded ml-2" title="Delete draft">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
        `;
        DOM.draftList.appendChild(el);
    });
    if (window.lucide) lucide.createIcons();
}

window.selectDraft = async function(draftId, draftName) {
    state.currentDraftId = draftId;
    state.currentDraftName = draftName;
    localStorage.setItem('falcone_draft_id', String(draftId));
    localStorage.setItem('falcone_draft_name', draftName);
    DOM.currentDraftName.textContent = draftName;
    closeDraftDropdown();
    renderDraftDropdown();

    // Reload current category with new draft
    if (state.currentCategory) {
        state.inventory = {};
        await loadCategory(state.currentCategory);
    }
};

window.createNewDraft = async function() {
    closeDraftDropdown();
    try {
        const res = await apiFetch(`${API_BASE}/drafts/new`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: `Draft ${state.drafts.length + 1}` }),
        });
        const data = await res.json();
        if (data.success) {
            await loadDrafts();
            await selectDraft(data.draft.id, data.draft.name);
            if (state.currentCategory) {
                state.inventory = {};
                await loadCategory(state.currentCategory);
            }
        }
    } catch (e) {
        console.error('Failed to create draft:', e);
    }
};

window.deleteDraft = async function(draftId) {
    if (state.drafts.length <= 1) {
        alert('You must have at least one draft.');
        return;
    }
    if (!confirm('Delete this draft and all its items?')) return;
    try {
        await apiFetch(`${API_BASE}/drafts/${draftId}`, { method: 'DELETE' });
        await loadDrafts();
    } catch (e) {
        console.error('Failed to delete draft:', e);
    }
};

function closeDraftDropdown() {
    DOM.draftDropdown.classList.add('hidden');
}

DOM.btnDraftSelector?.addEventListener('click', (e) => {
    e.stopPropagation();
    DOM.draftDropdown.classList.toggle('hidden');
    if (window.lucide) lucide.createIcons();
});

document.addEventListener('click', () => closeDraftDropdown());

// --- App Init ---
async function initApp() {
    applyTheme();
    applyLanguage();

    if (state.token) {
        await initAppAfterAuth();
    } else {
        showPinScreen();
    }
}

async function initAppAfterAuth() {
    hidePinScreen();

    try {
        const res = await apiFetch(`${API_BASE}/status`);
        const data = await res.json();
        const loc = data.location || "Falcones Pizza";
        document.getElementById('htmlTitle').textContent = `${loc} Inventory`;
        translations.en.appTitle = `${loc} Inventory`;
        translations.es.appTitle = `Inventario ${loc}`;
    } catch (e) {
        console.error("Failed to fetch status:", e);
    }

    if (DOM.locationBadge && state.locationName) {
        DOM.locationBadge.textContent = state.locationName;
    }

    applyLanguage();

    try {
        const res = await apiFetch(`${API_BASE}/categories`);
        const data = await res.json();
        if (data.success) {
            state.categories = data.categories;
        }
    } catch (e) {
        console.error("Failed to fetch categories:", e);
    }

    // Load or create drafts
    await loadDrafts();
    if (state.drafts.length === 0) {
        // Create initial draft
        await window.createNewDraft();
    }

    renderDashboard();
}

// --- Language & Theme ---
function toggleLanguage() {
    state.lang = state.lang === 'en' ? 'es' : 'en';
    localStorage.setItem('falcone_lang', state.lang);
    applyLanguage();
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('falcone_theme', state.theme);
    applyTheme();
}

function applyTheme() {
    document.documentElement.setAttribute('data-theme', state.theme);
    if (DOM.btnToggleTheme) {
        const icon = state.theme === 'dark' ? 'sun' : 'moon';
        DOM.btnToggleTheme.innerHTML = `<i data-lucide="${icon}" class="w-5 h-5"></i>`;
        if (window.lucide) lucide.createIcons();
    }
}

function applyLanguage() {
    const t = translations[state.lang];
    const setEl = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };

    setEl('appTitle', t.appTitle);
    setEl('labelSubmitOrder', t.labelSubmitOrder);
    setEl('labelOrderModalTitle', t.labelOrderModalTitle);
    setEl('labelOrderDate', t.labelOrderDate);
    setEl('labelRushOrder', t.labelRushOrder);
    setEl('labelNeededBy', t.labelNeededBy);
    setEl('labelCancel', t.labelCancel);
    setEl('labelConfirm', t.labelConfirm);
    if (DOM.pinScreenSubtitle) DOM.pinScreenSubtitle.textContent = t.pinPrompt;
    if (DOM.offlineBannerText) DOM.offlineBannerText.textContent = t.offlineBannerText;
    if (DOM.installBannerText) DOM.installBannerText.textContent = t.installBannerText;
    if (DOM.iosInstallText) DOM.iosInstallText.textContent = t.iosInstallText;
    if (DOM.updateBannerText) DOM.updateBannerText.textContent = t.updateBannerText;
    if (DOM.btnInstallApp) DOM.btnInstallApp.textContent = t.installCta;
    if (DOM.btnDismissInstall) DOM.btnDismissInstall.textContent = t.dismissCta;
    if (DOM.btnDismissIosInstall) DOM.btnDismissIosInstall.textContent = t.gotItCta;
    if (DOM.btnRefreshApp) DOM.btnRefreshApp.textContent = t.refreshCta;

    document.querySelectorAll('#btnToggleLangApp span').forEach(span => span.textContent = t.langToggle);

    if (state.currentCategory) {
        const catConfig = state.categories.find(c => c.id === state.currentCategory);
        if (catConfig) DOM.categoryTitle.textContent = state.lang === 'es' ? catConfig.label_es : catConfig.label_en;
        renderCategory(state.currentCategory);
    } else {
        renderDashboard();
    }
}

// --- Navigation ---
function renderDashboard() {
    state.currentCategory = null;
    DOM.btnBack.classList.add('hidden');
    DOM.categoryView.classList.add('hidden');
    DOM.dashboardView.innerHTML = '';

    state.categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';
        const displayLabel = state.lang === 'es' ? cat.label_es : cat.label_en;
        btn.innerHTML = `
            <div class="category-icon-container bg-${cat.color}-900 border-${cat.color}-700">
                <i data-lucide="${cat.icon}" class="category-icon text-${cat.color}-400"></i>
            </div>
            <div class="category-title-wrapper">
                <span class="category-title">${displayLabel}</span>
            </div>
        `;
        btn.onclick = () => loadCategory(cat.id);
        DOM.dashboardView.appendChild(btn);
    });

    DOM.dashboardView.style.display = 'grid';
    if (window.lucide) lucide.createIcons();
}

async function loadCategory(categoryId) {
    state.currentCategory = categoryId;
    DOM.dashboardView.style.display = 'none';
    DOM.categoryView.classList.remove('hidden');
    DOM.btnBack.classList.remove('hidden');

    const catConfig = state.categories.find(c => c.id === categoryId);
    DOM.categoryTitle.textContent = catConfig ? (state.lang === 'es' ? catConfig.label_es : catConfig.label_en) : categoryId;

    DOM.itemList.innerHTML = '<div class="text-center py-8 text-gray-400"><i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2"></i>Loading...</div>';
    if (window.lucide) lucide.createIcons();

    try {
        const draftParam = state.currentDraftId ? `?draft_id=${state.currentDraftId}` : '';
        const res = await apiFetch(`${API_BASE}/inventory/${categoryId}${draftParam}`);
        const data = await res.json();
        if (data.success) {
            state.inventory[categoryId] = data.items;
            renderCategory(categoryId);
        }
    } catch (error) {
        console.error("Failed to load category:", error);
        DOM.itemList.innerHTML = '<div class="text-center py-8 text-red-400">Error loading data.</div>';
    }
}

function renderCategory(categoryId) {
    const items = state.inventory[categoryId] || [];
    const t = translations[state.lang];
    DOM.categoryCount.textContent = `${items.length} ${t.itemsCount}`;
    DOM.itemList.innerHTML = '';

    if (items.length === 0) {
        DOM.itemList.innerHTML = '<div class="text-center py-8 text-gray-400">No items found.</div>';
        return;
    }

    items.forEach((item, index) => {
        const itemEl = document.createElement('div');
        itemEl.className = 'item-card p-4 mb-3';

        const nameEl = document.createElement('span');
        nameEl.textContent = state.lang === 'es' ? item.name_es : item.name_en;
        const nameSafe = nameEl.textContent;

        const isEachSelected = item.unit === 'each' ? 'selected' : '';
        const isCaseSelected = item.unit === 'case' ? 'selected' : '';

        itemEl.innerHTML = `
            <div class="flex-1 pr-4">
                <h3 class="text-lg font-bold text-[var(--color-text-primary)] leading-tight">${escapeHtml(nameSafe)}</h3>
                <div class="mt-2">
                    <select onchange="updateUnit('${categoryId}', ${index}, this.value)" class="bg-[var(--color-bg-body)] border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-primary)] py-1 px-2 focus:ring-1 focus:ring-falcone-red outline-none">
                        <option value="each" ${isEachSelected}>${t.each}</option>
                        <option value="case" ${isCaseSelected}>${t.case}</option>
                    </select>
                </div>
            </div>
            <div class="item-controls flex items-center gap-3 shrink-0">
                <button class="qty-btn w-10 h-10 flex items-center justify-center hover:bg-[var(--color-border)] rounded-lg transition-colors" onclick="updateQty('${categoryId}', ${index}, -1)">
                    <i data-lucide="minus" class="w-5 h-5"></i>
                </button>
                <input type="number" class="qty-input w-16 text-center bg-[var(--color-bg-body)] border border-[var(--color-border)] rounded-lg py-2 font-bold" value="${item.qty}" min="0"
                    onchange="setQty('${categoryId}', ${index}, this.value)"
                    onfocus="this.select()">
                <button class="qty-btn w-10 h-10 flex items-center justify-center hover:bg-[var(--color-border)] rounded-lg transition-colors" onclick="updateQty('${categoryId}', ${index}, 1)">
                    <i data-lucide="plus" class="w-5 h-5"></i>
                </button>
            </div>
        `;
        DOM.itemList.appendChild(itemEl);
    });

    if (window.lucide) lucide.createIcons();
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// --- Item Sync (auto-save) ---
async function syncItemUpdate(item) {
    try {
        const draftParam = state.currentDraftId ? `?draft_id=${state.currentDraftId}` : '';
        await apiFetch(`${API_BASE}/inventory/${state.currentCategory}/update${draftParam}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: item.id, qty: item.qty, unit: item.unit }),
        });
        // Refresh draft item count in background
        loadDrafts();
    } catch (e) {
        console.error("Failed to sync item update:", e);
    }
}

window.updateQty = function(categoryId, itemIndex, delta) {
    const item = state.inventory[categoryId][itemIndex];
    let newQty = parseInt(item.qty) + delta;
    if (newQty < 0) newQty = 0;
    item.qty = newQty;
    const inputs = document.querySelectorAll('.qty-input');
    if (inputs[itemIndex]) inputs[itemIndex].value = newQty;
    syncItemUpdate(item);
};

window.setQty = function(categoryId, itemIndex, value) {
    const item = state.inventory[categoryId][itemIndex];
    let newQty = parseInt(value);
    if (isNaN(newQty) || newQty < 0) newQty = 0;
    item.qty = newQty;
    syncItemUpdate(item);
};

window.updateUnit = function(categoryId, itemIndex, value) {
    const item = state.inventory[categoryId][itemIndex];
    item.unit = value;
    syncItemUpdate(item);
};

// --- Order Submission ---
DOM.btnSubmitOrder?.addEventListener('click', () => {
    const today = new Date().toISOString().split('T')[0];
    DOM.orderDateInput.value = today;
    DOM.rushOrderCheckbox.checked = false;
    DOM.neededByContainer.classList.add('hidden');
    DOM.neededByInput.value = '';
    DOM.orderModalError.classList.add('hidden');
    if (DOM.orderModalLocation && state.locationName) {
        DOM.orderModalLocation.textContent = `Location: ${state.locationName}`;
    }
    DOM.orderModal.classList.remove('hidden');
});

DOM.rushOrderCheckbox?.addEventListener('change', (e) => {
    DOM.neededByContainer.classList.toggle('hidden', !e.target.checked);
});

DOM.btnCancelOrder?.addEventListener('click', () => DOM.orderModal.classList.add('hidden'));

DOM.btnConfirmOrder?.addEventListener('click', async () => {
    const date = DOM.orderDateInput.value;
    const isRush = DOM.rushOrderCheckbox.checked;
    const neededBy = DOM.neededByInput.value;

    if (!date) {
        DOM.orderModalError.textContent = "Please select an order date.";
        DOM.orderModalError.classList.remove('hidden');
        return;
    }
    if (isRush && !neededBy) {
        DOM.orderModalError.textContent = "Please select a needed by date for rush orders.";
        DOM.orderModalError.classList.remove('hidden');
        return;
    }

    DOM.btnConfirmOrder.disabled = true;
    DOM.btnConfirmOrder.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i> Submitting...';
    if (window.lucide) lucide.createIcons();

    try {
        const res = await apiFetch(`${API_BASE}/submit_order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date,
                is_rush: isRush,
                needed_by: neededBy || null,
                draft_id: state.currentDraftId || null,
            }),
        });
        const data = await res.json();

        if (data.success) {
            DOM.orderModal.classList.add('hidden');
            alert(`Order submitted!\nLocation: ${state.locationName}\nFile: ${data.filename}${data.delivery_error ? `\n\nNote: Email delivery failed: ${data.delivery_error}` : ''}`);

            // Submitted draft is now closed — reload drafts and pick a new one
            state.currentDraftId = null;
            localStorage.removeItem('falcone_draft_id');
            await loadDrafts();
            if (state.drafts.length === 0) {
                await window.createNewDraft();
            }
            if (state.currentCategory) {
                state.inventory = {};
                await loadCategory(state.currentCategory);
            }
        } else {
            DOM.orderModalError.textContent = data.message || "Error submitting order.";
            DOM.orderModalError.classList.remove('hidden');
        }
    } catch (e) {
        console.error("Failed to submit order:", e);
        DOM.orderModalError.textContent = "Failed to submit order due to a network error.";
        DOM.orderModalError.classList.remove('hidden');
    } finally {
        DOM.btnConfirmOrder.disabled = false;
        DOM.btnConfirmOrder.innerHTML = '<span id="labelConfirm">Confirm Order</span>';
        applyLanguage();
    }
});

DOM.btnBack?.addEventListener('click', renderDashboard);
DOM.btnToggleLangApp?.addEventListener('click', toggleLanguage);
DOM.btnToggleTheme?.addEventListener('click', toggleTheme);

// --- Connectivity & PWA ---
function updateConnectivityBanner() {
    if (!DOM.offlineBanner) return;
    DOM.offlineBanner.classList.toggle('hidden', navigator.onLine);
}

function isIosSafari() {
    const ua = window.navigator.userAgent;
    return /iPhone|iPad|iPod/.test(ua) && /Safari/.test(ua) && !/CriOS|FxiOS/.test(ua);
}

function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            if (registration.waiting) DOM.updateBanner?.classList.remove('hidden');
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                if (!newWorker) return;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        DOM.updateBanner?.classList.remove('hidden');
                    }
                });
            });
            DOM.btnRefreshApp?.addEventListener('click', () => {
                const waitingWorker = registration.waiting;
                if (waitingWorker) waitingWorker.postMessage({ type: 'SKIP_WAITING' });
            });
            navigator.serviceWorker.addEventListener('controllerchange', () => window.location.reload());
        } catch (error) {
            console.error('SW registration failed:', error);
        }
    });
}

function setupInstallPrompts() {
    window.addEventListener('beforeinstallprompt', (event) => {
        event.preventDefault();
        state.deferredInstallPrompt = event;
        DOM.installBanner?.classList.remove('hidden');
    });
    window.addEventListener('appinstalled', () => {
        state.deferredInstallPrompt = null;
        DOM.installBanner?.classList.add('hidden');
        DOM.iosInstallBanner?.classList.add('hidden');
    });
    if (isIosSafari() && !window.matchMedia('(display-mode: standalone)').matches) {
        DOM.iosInstallBanner?.classList.remove('hidden');
    }
    DOM.btnInstallApp?.addEventListener('click', async () => {
        if (!state.deferredInstallPrompt) return;
        state.deferredInstallPrompt.prompt();
        await state.deferredInstallPrompt.userChoice;
        state.deferredInstallPrompt = null;
        DOM.installBanner?.classList.add('hidden');
    });
    DOM.btnDismissInstall?.addEventListener('click', () => DOM.installBanner?.classList.add('hidden'));
    DOM.btnDismissIosInstall?.addEventListener('click', () => DOM.iosInstallBanner?.classList.add('hidden'));
}

// --- Kick off ---
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    registerServiceWorker();
    setupInstallPrompts();
    updateConnectivityBanner();
    window.addEventListener('online', updateConnectivityBanner);
    window.addEventListener('offline', updateConnectivityBanner);
});
