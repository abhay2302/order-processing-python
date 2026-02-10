// API Base URL
const API_BASE = 'http://localhost:8000';

// Tab Management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
    
    // Load orders when switching to list tab
    if (tabName === 'list') {
        loadOrders();
    }
}

// Message System
function showMessage(text, type = 'info') {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
    messageEl.classList.add('show');
    
    setTimeout(() => {
        messageEl.classList.remove('show');
    }, 4000);
}

// Item Management
function addItem() {
    const container = document.getElementById('items-container');
    const itemRow = document.createElement('div');
    itemRow.className = 'item-row';
    itemRow.innerHTML = `
        <input type="text" placeholder="Product ID" class="product-id" required>
        <input type="number" placeholder="Quantity" class="quantity" min="1" required>
        <input type="number" placeholder="Unit Price" class="unit-price" step="0.01" min="0.01" required>
        <button type="button" class="remove-item" onclick="removeItem(this)">❌</button>
    `;
    container.appendChild(itemRow);
}

function removeItem(button) {
    const container = document.getElementById('items-container');
    if (container.children.length > 1) {
        button.parentElement.remove();
    } else {
        showMessage('At least one item is required', 'error');
    }
}

// Create Order
document.getElementById('create-order-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const customerId = document.getElementById('customer-id').value;
    const itemRows = document.querySelectorAll('.item-row');
    
    const items = [];
    for (const row of itemRows) {
        const productId = row.querySelector('.product-id').value;
        const quantity = parseInt(row.querySelector('.quantity').value);
        const unitPrice = parseFloat(row.querySelector('.unit-price').value);
        
        if (productId && quantity && unitPrice) {
            items.push({
                product_id: productId,
                quantity: quantity,
                unit_price: unitPrice
            });
        }
    }
    
    if (items.length === 0) {
        showMessage('Please add at least one item', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/orders/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                customer_id: customerId,
                items: items
            })
        });
        
        if (response.ok) {
            const order = await response.json();
            showMessage(`Order created successfully! ID: ${order.id}`, 'success');
            document.getElementById('create-order-form').reset();
            
            // Reset to one item row
            const container = document.getElementById('items-container');
            container.innerHTML = `
                <div class="item-row">
                    <input type="text" placeholder="Product ID" class="product-id" required>
                    <input type="number" placeholder="Quantity" class="quantity" min="1" required>
                    <input type="number" placeholder="Unit Price" class="unit-price" step="0.01" min="0.01" required>
                    <button type="button" class="remove-item" onclick="removeItem(this)">❌</button>
                </div>
            `;
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`Network error: ${error.message}`, 'error');
    }
});

// Load Orders
async function loadOrders() {
    const statusFilter = document.getElementById('status-filter').value;
    const ordersContainer = document.getElementById('orders-list');
    
    ordersContainer.innerHTML = '<div class="loading">🔄 Loading orders...</div>';
    
    try {
        let url = `${API_BASE}/orders/`;
        if (statusFilter) {
            url += `?status=${statusFilter}`;
        }
        
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            displayOrders(data.orders);
        } else {
            ordersContainer.innerHTML = '<div class="empty-state"><h3>❌ Error loading orders</h3></div>';
        }
    } catch (error) {
        ordersContainer.innerHTML = '<div class="empty-state"><h3>❌ Network error</h3></div>';
        showMessage(`Error loading orders: ${error.message}`, 'error');
    }
}

// Display Orders
function displayOrders(orders) {
    const container = document.getElementById('orders-list');
    
    if (orders.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>📭 No orders found</h3>
                <p>Create your first order to get started!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = orders.map(order => `
        <div class="order-card">
            <div class="order-header">
                <div class="order-id">ID: ${order.id}</div>
                <div class="status ${order.status}">${order.status}</div>
            </div>
            
            <div class="order-details">
                <div>
                    <strong>Customer:</strong> ${order.customer_id}<br>
                    <strong>Total:</strong> $${parseFloat(order.total_amount).toFixed(2)}<br>
                    <strong>Created:</strong> ${new Date(order.created_at).toLocaleString()}
                </div>
                <div>
                    <strong>Items:</strong> ${order.items.length}<br>
                    <strong>Status:</strong> ${order.status}<br>
                    <strong>Updated:</strong> ${new Date(order.updated_at).toLocaleString()}
                </div>
            </div>
            
            <div class="order-items">
                <h4>📦 Items:</h4>
                ${order.items.map(item => `
                    <div class="item">
                        <span><strong>${item.product_id}</strong> × ${item.quantity}</span>
                        <span>$${parseFloat(item.unit_price).toFixed(2)} each</span>
                    </div>
                `).join('')}
            </div>
            
            <div class="order-actions">
                <button 
                    class="btn-cancel" 
                    onclick="cancelOrder('${order.id}')"
                    ${order.status !== 'PENDING' ? 'disabled' : ''}
                >
                    ${order.status === 'PENDING' ? '❌ Cancel Order' : '🚫 Cannot Cancel'}
                </button>
            </div>
        </div>
    `).join('');
}

// Cancel Order
async function cancelOrder(orderId) {
    if (!confirm('Are you sure you want to cancel this order?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage('Order cancelled successfully!', 'success');
            loadOrders(); // Refresh the list
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        showMessage(`Network error: ${error.message}`, 'error');
    }
}

// Search Order
async function searchOrder() {
    const orderId = document.getElementById('search-id').value.trim();
    const resultContainer = document.getElementById('search-result');
    
    if (!orderId) {
        showMessage('Please enter an order ID', 'error');
        return;
    }
    
    resultContainer.innerHTML = '<div class="loading">🔍 Searching...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}`);
        
        if (response.ok) {
            const order = await response.json();
            displayOrders([order]);
            resultContainer.innerHTML = '';
            displayOrders([order]);
            resultContainer.innerHTML = document.getElementById('orders-list').innerHTML;
        } else if (response.status === 404) {
            resultContainer.innerHTML = `
                <div class="empty-state">
                    <h3>❌ Order not found</h3>
                    <p>No order found with ID: ${orderId}</p>
                </div>
            `;
        } else {
            resultContainer.innerHTML = `
                <div class="empty-state">
                    <h3>❌ Error</h3>
                    <p>Failed to search for order</p>
                </div>
            `;
        }
    } catch (error) {
        resultContainer.innerHTML = `
            <div class="empty-state">
                <h3>❌ Network Error</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Search on Enter key
document.getElementById('search-id').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchOrder();
    }
});

// Auto-refresh orders every 30 seconds when on list tab
setInterval(() => {
    const listTab = document.getElementById('list-tab');
    if (listTab.classList.contains('active')) {
        loadOrders();
    }
}, 30000);

// Load orders on page load
document.addEventListener('DOMContentLoaded', () => {
    loadOrders();
});