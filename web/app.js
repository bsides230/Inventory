// Falcone's Pizza Inventory - Frontend App Logic

const API_BASE = '/api';

// --- i18n Dictionary ---
const translations = {
    en: {
        loginTitle: "Inventory Login",
        labelUsername: "Username",
        labelPin: "4-Digit PIN",
        btnLogin: "Login",
        loginError: "Invalid username or PIN",
        appTitle: "Inventory",
        userGreeting: "User",
        labelSave: "Save Changes",
        langToggle: "Español",
        itemsCount: "items",
        // Categories
        catProduce: "Produce",
        catMeat: "Meat",
        catDairy: "Dairy",
        catBeverages: "Beverages",
        // Units
        cases: "cases",
        bags: "bags",
        lbs: "lbs",
        blocks: "blocks",
        tubs: "tubs",
        par: "Par"
    },
    es: {
        loginTitle: "Inicio de sesión",
        labelUsername: "Usuario",
        labelPin: "PIN de 4 dígitos",
        btnLogin: "Entrar",
        loginError: "Usuario o PIN inválido",
        appTitle: "Inventario",
        userGreeting: "Usuario",
        labelSave: "Guardar",
        langToggle: "English",
        itemsCount: "artículos",
        // Categories
        catProduce: "Verduras",
        catMeat: "Carnes",
        catDairy: "Lácteos",
        catBeverages: "Bebidas",
        // Units
        cases: "cajas",
        bags: "bolsas",
        lbs: "libras",
        blocks: "bloques",
        tubs: "tinas",
        par: "Mín"
    }
};

// --- State Management ---
const state = {
    isAuthenticated: false,
    user: null,
    lang: localStorage.getItem('falcone_lang') || 'en', // 'en' or 'es'
    currentCategory: null,
    inventory: {}
};

// --- DOM Elements ---
const DOM = {
    loginScreen: document.getElementById('loginScreen'),
    loginForm: document.getElementById('loginForm'),
    usernameInput: document.getElementById('username'),
    pinInput: document.getElementById('pin'),
    loginError: document.getElementById('loginError'),

    appHeader: document.querySelector('header'),
    dashboardView: document.getElementById('dashboardView'),
    categoryView: document.getElementById('categoryView'),

    btnBack: document.getElementById('btnBack'),
    btnLogout: document.getElementById('btnLogout'),
    btnToggleLangApp: document.getElementById('btnToggleLangApp'),
    btnToggleLangLogin: document.getElementById('btnToggleLangLogin'),

    appTitle: document.getElementById('appTitle'),
    currentUser: document.getElementById('currentUser'),
    userGreeting: document.getElementById('userGreeting'),

    categoryTitle: document.getElementById('categoryTitle'),
    categoryCount: document.getElementById('categoryCount'),
    itemList: document.getElementById('itemList'),
};

// --- Initialization ---
async function initApp() {
    // Apply initial language
    applyLanguage();

    // Check backend status/auth requirement
    try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();

        if (!data.auth_required) {
            // Auth disabled by backend toggle
            setAuthenticated("anonymous");
            return;
        }
    } catch (e) {
        console.error("Failed to fetch status:", e);
    }

    // Check localStorage for existing session
    const savedUser = localStorage.getItem('falcone_user');
    if (savedUser) {
        // Assume valid for this basic implementation. Real apps would verify token.
        setAuthenticated(savedUser);
    } else {
        showLogin();
    }
}

// --- Authentication ---
function showLogin() {
    DOM.loginScreen.classList.remove('hidden');
    // Hide main app elements behind it just in case
    DOM.appHeader.style.display = 'none';
    DOM.dashboardView.style.display = 'none';
    DOM.categoryView.style.display = 'none';

    // Focus username
    setTimeout(() => DOM.usernameInput.focus(), 100);
}

function setAuthenticated(username) {
    state.isAuthenticated = true;
    state.user = username;

    // Save state
    if (username !== "anonymous") {
        localStorage.setItem('falcone_user', username);
    }

    // Update UI
    DOM.currentUser.textContent = username.charAt(0).toUpperCase() + username.slice(1);

    // Hide login, show app
    DOM.loginScreen.classList.add('hidden');
    DOM.appHeader.style.display = 'block';
    DOM.dashboardView.style.display = 'grid'; // Grid display for dashboard

    // Clear inputs
    DOM.usernameInput.value = '';
    DOM.pinInput.value = '';

    // Render initial view
    renderDashboard();
}

async function handleLogin(e) {
    e.preventDefault();

    const username = DOM.usernameInput.value.trim();
    const pin = DOM.pinInput.value.trim();

    if (!username || !pin) {
        showLoginError();
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, pin })
        });

        const data = await res.json();

        if (data.success) {
            DOM.loginError.classList.add('hidden');
            setAuthenticated(data.user);
        } else {
            showLoginError();
        }
    } catch (error) {
        console.error("Login failed:", error);
        // Fallback for demo if backend is down - let kitchen/1234 through
        if (username.toLowerCase() === 'kitchen' && pin === '1234') {
            setAuthenticated('kitchen');
        } else {
            showLoginError();
        }
    }
}

function showLoginError() {
    DOM.loginError.classList.remove('hidden');
    DOM.pinInput.value = '';
    DOM.pinInput.classList.add('shake');
    setTimeout(() => DOM.pinInput.classList.remove('shake'), 400);
}

function handleLogout() {
    localStorage.removeItem('falcone_user');
    state.isAuthenticated = false;
    state.user = null;
    showLogin();
}

// --- Internationalization ---
function toggleLanguage() {
    state.lang = state.lang === 'en' ? 'es' : 'en';
    localStorage.setItem('falcone_lang', state.lang);
    applyLanguage();
}

function applyLanguage() {
    const t = translations[state.lang];

    // Update static text
    document.getElementById('loginTitle').textContent = t.loginTitle;
    document.getElementById('labelUsername').textContent = t.labelUsername;
    document.getElementById('labelPin').textContent = t.labelPin;
    document.getElementById('btnLogin').textContent = t.btnLogin;
    document.getElementById('loginError').textContent = t.loginError;
    document.getElementById('appTitle').textContent = t.appTitle;
    document.getElementById('userGreeting').textContent = t.userGreeting;
    document.getElementById('labelSave').textContent = t.labelSave;

    // Update toggle buttons text
    const langSpans = document.querySelectorAll('#btnToggleLangLogin span, #btnToggleLangApp span');
    langSpans.forEach(span => span.textContent = t.langToggle);

    // Update inputs placeholders
    DOM.usernameInput.placeholder = state.lang === 'en' ? 'e.g. kitchen' : 'ej. cocina';

    // If we're logged in, re-render to update dynamic text
    if (state.isAuthenticated) {
        if (state.currentCategory) {
            renderCategory(state.currentCategory);
        } else {
            renderDashboard();
        }
    }
}

// --- Navigation & Rendering ---
const CATEGORIES = [
    { id: 'produce', icon: 'carrot', labelKey: 'catProduce' },
    { id: 'meat', icon: 'beef', labelKey: 'catMeat' },
    { id: 'dairy', icon: 'milk', labelKey: 'catDairy' },
    { id: 'beverages', icon: 'cup-soda', labelKey: 'catBeverages' }
];

function renderDashboard() {
    state.currentCategory = null;
    DOM.btnBack.classList.add('hidden');
    DOM.categoryView.classList.add('hidden');

    DOM.dashboardView.innerHTML = '';
    const t = translations[state.lang];

    CATEGORIES.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';
        btn.innerHTML = `
            <div class="category-icon-container">
                <i data-lucide="${cat.icon}" class="category-icon"></i>
            </div>
            <span class="category-title">${t[cat.labelKey]}</span>
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
    const catConfig = CATEGORIES.find(c => c.id === categoryId);
    DOM.categoryTitle.textContent = t[catConfig.labelKey];

    // Show loading state
    DOM.itemList.innerHTML = '<div class="text-center py-8 text-gray-400"><i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2"></i>Loading...</div>';
    if (window.lucide) lucide.createIcons();

    try {
        const res = await fetch(`${API_BASE}/inventory/${categoryId}`);
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
        itemEl.className = 'item-card';

        // Translate unit if available, otherwise keep original
        const displayUnit = t[item.unit] || item.unit;

        // Alert if below par
        const isLow = item.qty < item.par;
        const nameColor = isLow ? 'text-falcone-red' : 'text-white';
        const parAlert = isLow ? `<i data-lucide="alert-triangle" class="w-4 h-4 text-falcone-red inline ml-2"></i>` : '';

        // Use textContent for user data to prevent XSS
        const nameEscaped = document.createElement('div');
        nameEscaped.textContent = item.name;

        itemEl.innerHTML = `
            <div class="flex-1">
                <h3 class="text-lg font-bold ${nameColor}">${nameEscaped.innerHTML}${parAlert}</h3>
                <div class="text-sm text-gray-400 mt-1 flex items-center gap-2">
                    <span>${t.par}: ${item.par}</span>
                    <span class="w-1 h-1 rounded-full bg-gray-600"></span>
                    <span>${displayUnit}</span>
                </div>
            </div>
            <div class="item-controls flex items-center gap-3">
                <button class="qty-btn" onclick="updateQty('${categoryId}', ${index}, -1)">
                    <i data-lucide="minus" class="w-5 h-5"></i>
                </button>
                <input type="number" class="qty-input" value="${item.qty}" min="0"
                    onchange="setQty('${categoryId}', ${index}, this.value)"
                    onfocus="this.select()">
                <button class="qty-btn" onclick="updateQty('${categoryId}', ${index}, 1)">
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

// Global Actions for items (attached directly to window for easy inline access)
window.updateQty = function(categoryId, itemIndex, delta) {
    const item = state.inventory[categoryId][itemIndex];
    let newQty = parseInt(item.qty) + delta;
    if (newQty < 0) newQty = 0;

    item.qty = newQty;
    renderCategory(categoryId);
};

window.setQty = function(categoryId, itemIndex, value) {
    const item = state.inventory[categoryId][itemIndex];
    let newQty = parseInt(value);

    if (isNaN(newQty) || newQty < 0) newQty = 0;

    item.qty = newQty;
    renderCategory(categoryId);
};

document.getElementById('btnSaveInventory').addEventListener('click', () => {
    // Basic animation to show saving
    const btn = document.getElementById('btnSaveInventory');
    const originalContent = btn.innerHTML;

    btn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i> Saving...';
    if (window.lucide) lucide.createIcons();
    btn.disabled = true;

    // Simulate network delay for now
    setTimeout(() => {
        btn.innerHTML = '<i data-lucide="check" class="w-5 h-5"></i> Saved!';
        if (window.lucide) lucide.createIcons();
        btn.classList.replace('bg-falcone-red', 'bg-green-600');
        btn.classList.replace('hover:bg-red-600', 'hover:bg-green-700');

        setTimeout(() => {
            btn.innerHTML = originalContent;
            btn.classList.replace('bg-green-600', 'bg-falcone-red');
            btn.classList.replace('hover:bg-green-700', 'hover:bg-red-600');
            btn.disabled = false;
        }, 2000);

        // Later we will post state.inventory to the backend here
    }, 800);
});

// Global Nav Handlers
DOM.btnBack.addEventListener('click', renderDashboard);

// --- Event Listeners ---
DOM.loginForm.addEventListener('submit', handleLogin);
DOM.btnLogout.addEventListener('click', handleLogout);
DOM.btnToggleLangLogin.addEventListener('click', toggleLanguage);
DOM.btnToggleLangApp.addEventListener('click', toggleLanguage);

// Start
document.addEventListener('DOMContentLoaded', initApp);
