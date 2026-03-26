// Falcone's Pizza Inventory - Frontend App Logic

const API_BASE = '/api';

// --- i18n Dictionary ---
const translations = {
    en: {
        appTitle: "Inventory",
        langToggle: "Español",
        itemsCount: "items",
        labelSubmitOrder: "Submit Order",
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
        refreshCta: "Refresh"
    },
    es: {
        appTitle: "Inventario",
        langToggle: "English",
        itemsCount: "artículos",
        labelSubmitOrder: "Enviar Pedido",
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
        refreshCta: "Actualizar"
    }
};

// --- State Management ---
const state = {
    lang: localStorage.getItem('falcone_lang') || 'en', // 'en' or 'es'
    theme: localStorage.getItem('falcone_theme') || 'dark', // 'light' or 'dark'
    currentCategory: null,
    inventory: {},
    categories: [],
    deferredInstallPrompt: null
};

// --- DOM Elements ---
const DOM = {
    appHeader: document.querySelector('header'),
    dashboardView: document.getElementById('dashboardView'),
    categoryView: document.getElementById('categoryView'),

    btnBack: document.getElementById('btnBack'),
    btnToggleLangApp: document.getElementById('btnToggleLangApp'),
    btnToggleTheme: document.getElementById('btnToggleTheme'),

    htmlTitle: document.getElementById('htmlTitle'),
    appTitle: document.getElementById('appTitle'),

    categoryTitle: document.getElementById('categoryTitle'),
    categoryCount: document.getElementById('categoryCount'),
    itemList: document.getElementById('itemList'),

    // Order Modal
    btnSubmitOrder: document.getElementById('btnSubmitOrder'),
    orderModal: document.getElementById('orderModal'),
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
};



async function apiFetch(url, options = {}) {
    try {
        return await fetch(url, options);
    } catch (error) {
        if (!navigator.onLine) {
            DOM.offlineBanner?.classList.remove('hidden');
        }
        throw error;
    }
}

function updateConnectivityBanner() {
    if (!DOM.offlineBanner) return;
    if (navigator.onLine) {
        DOM.offlineBanner.classList.add('hidden');
    } else {
        DOM.offlineBanner.classList.remove('hidden');
    }
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

            if (registration.waiting) {
                DOM.updateBanner?.classList.remove('hidden');
            }

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
                if (waitingWorker) {
                    waitingWorker.postMessage({ type: 'SKIP_WAITING' });
                }
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

// --- Initialization ---
async function initApp() {
    try {
        const res = await apiFetch(`${API_BASE}/status`);
        const data = await res.json();
        const loc = data.location || "Falcones Pizza";
        DOM.htmlTitle.textContent = `${loc} Inventory`;

        // Update translation logic for title based on location
        translations.en.appTitle = `${loc} Inventory`;
        translations.es.appTitle = `Inventario ${loc}`;
    } catch (e) {
        console.error("Failed to fetch status:", e);
    }

    applyLanguage();
    applyTheme();

    try {
        const res = await apiFetch(`${API_BASE}/categories`);
        const data = await res.json();
        if (data.success) {
            state.categories = data.categories;
        }
    } catch (e) {
        console.error("Failed to fetch categories:", e);
    }

    renderDashboard();
}

// --- Internationalization ---
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
        DOM.btnToggleTheme.innerHTML = `<i data-lucide="${icon}" class="w-6 h-6"></i>`;
        if (window.lucide) {
            lucide.createIcons();
        }
    }
}

function applyLanguage() {
    const t = translations[state.lang];

    // Update static text
    document.getElementById('appTitle').textContent = t.appTitle;
    document.getElementById('labelSubmitOrder').textContent = t.labelSubmitOrder;
    document.getElementById('labelOrderModalTitle').textContent = t.labelOrderModalTitle;
    document.getElementById('labelOrderDate').textContent = t.labelOrderDate;
    document.getElementById('labelRushOrder').textContent = t.labelRushOrder;
    document.getElementById('labelNeededBy').textContent = t.labelNeededBy;
    document.getElementById('labelCancel').textContent = t.labelCancel;
    document.getElementById('labelConfirm').textContent = t.labelConfirm;
    if (DOM.offlineBannerText) DOM.offlineBannerText.textContent = t.offlineBannerText;
    if (DOM.installBannerText) DOM.installBannerText.textContent = t.installBannerText;
    if (DOM.iosInstallText) DOM.iosInstallText.textContent = t.iosInstallText;
    if (DOM.updateBannerText) DOM.updateBannerText.textContent = t.updateBannerText;
    if (DOM.btnInstallApp) DOM.btnInstallApp.textContent = t.installCta;
    if (DOM.btnDismissInstall) DOM.btnDismissInstall.textContent = t.dismissCta;
    if (DOM.btnDismissIosInstall) DOM.btnDismissIosInstall.textContent = t.gotItCta;
    if (DOM.btnRefreshApp) DOM.btnRefreshApp.textContent = t.refreshCta;

    // Update toggle buttons text
    const langSpans = document.querySelectorAll('#btnToggleLangApp span');
    langSpans.forEach(span => span.textContent = t.langToggle);

    // If we're logged in, re-render to update dynamic text
    if (state.currentCategory) {
        const catConfig = state.categories.find(c => c.id === state.currentCategory);
        if (catConfig) {
            DOM.categoryTitle.textContent = state.lang === 'es' ? catConfig.label_es : catConfig.label_en;
        }
        renderCategory(state.currentCategory);
    } else {
        renderDashboard();
    }
}

// --- Navigation & Rendering ---

function renderDashboard() {
    state.currentCategory = null;
    DOM.btnBack.classList.add('hidden');
    DOM.categoryView.classList.add('hidden');

    DOM.dashboardView.innerHTML = '';

    state.categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';

        const displayLabel = state.lang === 'es' ? cat.label_es : cat.label_en;

        // Custom styling for category colors
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

    DOM.dashboardView.style.display = 'grid'; // Ensure it's a grid

    // Re-initialize icons since we injected new HTML with data-lucide tags
    if (window.lucide) {
        lucide.createIcons();
    }
}

async function loadCategory(categoryId) {
    state.currentCategory = categoryId;

    // UI Transitions
    DOM.dashboardView.style.display = 'none';
    DOM.categoryView.classList.remove('hidden');
    DOM.btnBack.classList.remove('hidden');

    const t = translations[state.lang];
    const catConfig = state.categories.find(c => c.id === categoryId);
    DOM.categoryTitle.textContent = catConfig ? (state.lang === 'es' ? catConfig.label_es : catConfig.label_en) : categoryId;

    // Show loading state
    DOM.itemList.innerHTML = '<div class="text-center py-8 text-gray-400"><i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2"></i>Loading...</div>';
    if (window.lucide) lucide.createIcons();

    try {
        const res = await apiFetch(`${API_BASE}/inventory/${categoryId}`);
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

    // Update count
    DOM.categoryCount.textContent = `${items.length} ${t.itemsCount}`;

    // Clear list
    DOM.itemList.innerHTML = '';

    if (items.length === 0) {
        DOM.itemList.innerHTML = '<div class="text-center py-8 text-gray-400">No items found.</div>';
        return;
    }

    items.forEach((item, index) => {
        const itemEl = document.createElement('div');
        itemEl.className = 'item-card p-4 mb-3';

        // Use textContent for user data to prevent XSS
        const nameEscaped = document.createElement('div');
        nameEscaped.textContent = state.lang === 'es' ? item.name_es : item.name_en;

        const isEachSelected = item.unit === 'each' ? 'selected' : '';
        const isCaseSelected = item.unit === 'case' ? 'selected' : '';

        itemEl.innerHTML = `
            <div class="flex-1 pr-4">
                <h3 class="text-lg font-bold text-[var(--color-text-primary)] leading-tight">${nameEscaped.innerHTML}</h3>
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

    if (window.lucide) {
        lucide.createIcons();
    }
}

// Backend Sync Function
async function syncItemUpdate(item) {
    try {
        await apiFetch(`${API_BASE}/inventory/${state.currentCategory}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: item.id,
                qty: item.qty,
                unit: item.unit
            })
        });
    } catch (e) {
        console.error("Failed to sync item update:", e);
    }
}

// Global Actions for items (attached directly to window for easy inline access)
window.updateQty = function(categoryId, itemIndex, delta) {
    const item = state.inventory[categoryId][itemIndex];
    let newQty = parseInt(item.qty) + delta;
    if (newQty < 0) newQty = 0;

    item.qty = newQty;

    // Update input visually without re-rendering entire list immediately to prevent focus loss issues
    const inputs = document.querySelectorAll('.qty-input');
    if (inputs[itemIndex]) {
        inputs[itemIndex].value = newQty;
    }

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

// Order Submission Handlers
DOM.btnSubmitOrder.addEventListener('click', () => {
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    DOM.orderDateInput.value = today;

    // Reset modal state
    DOM.rushOrderCheckbox.checked = false;
    DOM.neededByContainer.classList.add('hidden');
    DOM.neededByInput.value = '';
    DOM.orderModalError.classList.add('hidden');

    DOM.orderModal.classList.remove('hidden');
});

DOM.rushOrderCheckbox.addEventListener('change', (e) => {
    if (e.target.checked) {
        DOM.neededByContainer.classList.remove('hidden');
    } else {
        DOM.neededByContainer.classList.add('hidden');
    }
});

DOM.btnCancelOrder.addEventListener('click', () => {
    DOM.orderModal.classList.add('hidden');
});

DOM.btnConfirmOrder.addEventListener('click', async () => {
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
    lucide.createIcons();

    try {
        const res = await apiFetch(`${API_BASE}/submit_order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: date,
                is_rush: isRush,
                needed_by: neededBy || null
            })
        });

        const data = await res.json();

        if (data.success) {
            DOM.orderModal.classList.add('hidden');
            alert(`Order submitted successfully!\nFile: ${data.filename}`);

            // Reload category to get cleared state
            if (state.currentCategory) {
                loadCategory(state.currentCategory);
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
        applyLanguage(); // reset label text
    }
});

// Global Nav Handlers
DOM.btnBack.addEventListener('click', renderDashboard);

// --- Event Listeners ---
DOM.btnToggleLangApp.addEventListener('click', toggleLanguage);
if (DOM.btnToggleTheme) {
    DOM.btnToggleTheme.addEventListener('click', toggleTheme);
}

// Start
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    registerServiceWorker();
    setupInstallPrompts();
    updateConnectivityBanner();
    window.addEventListener('online', updateConnectivityBanner);
    window.addEventListener('offline', updateConnectivityBanner);
});
