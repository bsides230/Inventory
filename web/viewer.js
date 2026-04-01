const API_BASE = '/api';
let adminToken = sessionStorage.getItem('admin_token') || null;

// --- Authentication & Theme ---
if (!adminToken) {
    window.location.href = '/admin';
}

function getAdminToken() {
    return adminToken;
}

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Initialize theme
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

// --- Translations ---
let currentLang = localStorage.getItem('app_lang') || 'en';

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('app_lang', lang);
    // Reload or re-render might be needed here if labels change
}


// --- Order Logic ---
let ordersData = [];
let currentSelectedOrderId = null;

async function loadOrders() {
    try {
        const res = await fetch('/api/admin/orders', {
            headers: { 'Authorization': `Bearer ${getAdminToken()}` }
        });
        if (res.status === 401 || res.status === 403) {
            sessionStorage.removeItem('admin_token');
            window.location.href = '/admin';
            return;
        }
        if (res.ok) {
            const data = await res.json();
            ordersData = data.orders || [];
            renderOrderDropdown();
        } else {
            console.error("Failed to load orders");
        }
    } catch (e) {
        console.error("Error loading orders", e);
    }
}

function toggleOrderDropdown() {
    document.getElementById('orderDropdown').classList.toggle('hidden');
}

document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('orderDropdown');
    const button = document.getElementById('btnOrderSelector');
    if (dropdown && button && !dropdown.contains(e.target) && !button.contains(e.target)) {
        dropdown.classList.add('hidden');
    }
});

function renderOrderDropdown() {
    const listEl = document.getElementById('orderList');

    if (ordersData.length === 0) {
        listEl.innerHTML = '<div class="px-4 py-2 text-sm text-[var(--color-text-secondary)]">No orders found.</div>';
        return;
    }

    listEl.innerHTML = ordersData.map((order, index) => {
        const isRush = order.is_rush;
        const dateStr = new Date(order.submitted_at).toLocaleString();
        const locName = escapeHtml(order.location_name || order.location_pin);

        return `
            <button onclick="selectOrder('${order.id}')" class="w-full text-left px-4 py-3 hover:bg-[var(--color-border)] transition-colors border-b border-[var(--color-border)] last:border-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="font-bold text-sm text-[var(--color-text-primary)] truncate">${locName}</span>
                    ${isRush ? `<span class="bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wide shrink-0">Rush</span>` : ''}
                </div>
                <div class="text-xs text-[var(--color-text-secondary)]">${dateStr}</div>
            </button>
        `;
    }).join('');
}

function selectOrder(orderId) {
    currentSelectedOrderId = orderId;
    document.getElementById('orderDropdown').classList.add('hidden');
    renderSelectedOrder();
}

function renderSelectedOrder() {
    const order = ordersData.find(o => o.id === currentSelectedOrderId);
    const noOrderState = document.getElementById('noOrderSelectedState');
    const orderArea = document.getElementById('orderContentArea');
    const orderNameBtn = document.getElementById('currentOrderName');

    if (!order) {
        noOrderState.classList.remove('hidden');
        orderArea.classList.add('hidden');
        orderNameBtn.textContent = "Select Order...";
        return;
    }

    noOrderState.classList.add('hidden');
    orderArea.classList.remove('hidden');

    const locName = escapeHtml(order.location_name || order.location_pin);
    const dateStr = new Date(order.submitted_at).toLocaleString();

    orderNameBtn.textContent = `${locName} - ${new Date(order.submitted_at).toLocaleDateString()}`;

    // Header info
    document.getElementById('viewOrderLocation').textContent = locName;
    const badge = document.getElementById('viewOrderRushBadge');
    if (order.is_rush) badge.classList.remove('hidden');
    else badge.classList.add('hidden');

    document.getElementById('viewOrderDate').textContent = dateStr;

    const neededByContainer = document.getElementById('viewOrderNeededByContainer');
    if (order.needed_by) {
        neededByContainer.classList.remove('hidden');
        document.getElementById('viewOrderNeededBy').textContent = order.needed_by;
    } else {
        neededByContainer.classList.add('hidden');
    }

    const totalAmount = order.total_amount || 0;
    document.getElementById('viewOrderTotal').textContent = `$${totalAmount.toFixed(2)}`;

    // Items
    const itemsContainer = document.getElementById('viewOrderItems');
    let itemsHtml = '';

    (order.items || []).forEach((item, itemIdx) => {
        const isChecked = item.checked || false;
        const amount = item.amount || '';
        itemsHtml += `
            <div class="flex items-center justify-between gap-3 p-3 bg-[var(--color-bg-body)] rounded border border-[var(--color-border)] hover:border-brand-primary transition-colors">
                <div class="flex items-center gap-3 flex-1 min-w-0">
                    <input type="checkbox" id="check-${order.id}-${itemIdx}" class="w-5 h-5 rounded border-[var(--color-border)] text-brand-primary focus:ring-brand-primary bg-transparent accent-brand-primary cursor-pointer shrink-0" ${isChecked ? 'checked' : ''} onchange="updateOrderItem('${order.id}', ${itemIdx}, 'check', this.checked)">
                    <label for="check-${order.id}-${itemIdx}" class="flex-1 min-w-0 cursor-pointer ${isChecked ? 'line-through text-[var(--color-text-secondary)]' : 'text-[var(--color-text-primary)]'}">
                        <div class="font-medium text-sm truncate">${escapeHtml(item.item_name)}</div>
                        <div class="text-xs text-[var(--color-text-secondary)]">${item.quantity} ${item.unit} &bull; ${escapeHtml(item.category_id)}</div>
                    </label>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <span class="text-sm font-medium text-[var(--color-text-secondary)]">$</span>
                    <input type="number" step="0.01" min="0" placeholder="0.00" class="bg-[var(--color-bg-body)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:border-brand-primary outline-none w-24 text-right py-1 px-2 font-mono text-sm" value="${amount}" oninput="debounceUpdateOrderItem('${order.id}', ${itemIdx}, 'amount', this.value)">
                </div>
            </div>
        `;
    });

    itemsContainer.innerHTML = itemsHtml;

    // Set up delete button
    const deleteBtn = document.getElementById('btnDeleteOrder');
    deleteBtn.onclick = () => deleteOrder(order.user_id, order.id);

    if (window.lucide) lucide.createIcons();
}

// Debounce state modifications
let updateOrderTimeout = {};

function debounceUpdateOrderItem(orderId, itemIdx, field, value) {
    clearTimeout(updateOrderTimeout[orderId]);

    const order = ordersData.find(o => o.id === orderId);
    if (!order) return;

    if (field === 'amount') {
        order.items[itemIdx].amount = value === '' ? null : parseFloat(value);
        // Optimistically update total amount in UI
        const newTotal = order.items.reduce((sum, it) => sum + (parseFloat(it.amount) || 0), 0);
        document.getElementById('viewOrderTotal').textContent = `$${newTotal.toFixed(2)}`;
    }

    updateOrderTimeout[orderId] = setTimeout(() => {
        saveOrderState(orderId);
    }, 1000);
}

function updateOrderItem(orderId, itemIdx, field, value) {
    const order = ordersData.find(o => o.id === orderId);
    if (!order) return;

    if (field === 'check') {
        order.items[itemIdx].checked = value;
        // visually update label
        const label = document.querySelector(`label[for="check-${orderId}-${itemIdx}"]`);
        if (label) {
            if (value) {
                label.classList.add('line-through', 'text-[var(--color-text-secondary)]');
                label.classList.remove('text-[var(--color-text-primary)]');
            } else {
                label.classList.remove('line-through', 'text-[var(--color-text-secondary)]');
                label.classList.add('text-[var(--color-text-primary)]');
            }
        }
    }

    saveOrderState(orderId);
}

async function saveOrderState(orderId) {
    const order = ordersData.find(o => o.id === orderId);
    if (!order) return;

    try {
        const res = await fetch(`/api/admin/orders/${order.user_id}/${order.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAdminToken()}`
            },
            body: JSON.stringify({ items: order.items })
        });

        if (res.ok) {
            const data = await res.json();
            order.total_amount = data.order.total_amount;
            if (currentSelectedOrderId === orderId) {
                document.getElementById('viewOrderTotal').textContent = `$${order.total_amount.toFixed(2)}`;
            }
        }
    } catch (e) {
        console.error("Failed to save order state", e);
    }
}

async function deleteOrder(userId, orderId) {
    if (!confirm("Are you sure you want to delete this order? This will delete all instances of that order in the history.")) {
        return;
    }

    try {
        const res = await fetch(`/api/admin/orders/${userId}/${orderId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getAdminToken()}` }
        });

        if (res.ok) {
            ordersData = ordersData.filter(o => o.id !== orderId);
            currentSelectedOrderId = null;
            renderOrderDropdown();
            renderSelectedOrder();
        } else {
            alert("Failed to delete order.");
        }
    } catch (e) {
        console.error("Error deleting order", e);
        alert("Error deleting order.");
    }
}

function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
    if (adminToken) {
        loadOrders();
    }
});
