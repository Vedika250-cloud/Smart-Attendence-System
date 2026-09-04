// Shared UI utilities

// 1. Toast Notification System
function showToast(message, type = 'info', title = null) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ';
    if (type === 'success') icon = '✓';
    if (type === 'warning') icon = '⚠';
    if (type === 'error') icon = '✕';

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">
            ${title ? `<div class="toast-title">${title}</div>` : ''}
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    const closeToast = () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.toast-close').onclick = closeToast;

    setTimeout(closeToast, 5000);
}

// 2. Global Confirmation Modal
function showConfirmModal(title, text, confirmText, onConfirm, type = 'primary') {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    
    const modal = document.createElement('div');
    modal.className = 'modal-content';
    
    modal.innerHTML = `
        <h3 class="modal-title">${title}</h3>
        <p class="modal-text">${text}</p>
        <div class="modal-actions">
            <button class="secondary-btn btn-cancel">Cancel</button>
            <button class="${type === 'danger' ? 'danger-btn' : 'primary-btn'} btn-confirm">${confirmText}</button>
        </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    const cancelBtn = modal.querySelector('.btn-cancel');
    const confirmBtn = modal.querySelector('.btn-confirm');
    
    setTimeout(() => overlay.classList.add('show'), 10);
    cancelBtn.focus();

    const closeModal = () => {
        overlay.classList.remove('show');
        setTimeout(() => overlay.remove(), 300);
    };

    cancelBtn.onclick = closeModal;
    confirmBtn.onclick = () => {
        onConfirm();
        closeModal();
    };
}

// 3. Button Loading State
function setButtonLoading(btn, loadingText) {
    if (!btn.dataset.originalText) {
        btn.dataset.originalText = btn.innerHTML;
    }
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${loadingText}`;
}

function resetButton(btn) {
    if (btn.dataset.originalText) {
        btn.innerHTML = btn.dataset.originalText;
        btn.disabled = false;
        delete btn.dataset.originalText;
    }
}

// 4. API Fetch Wrapper for global error handling & 401
async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (response.status === 401) {
            showToast("Your session has expired. Please log in again.", "warning");
            setTimeout(() => window.location.href = '/login', 2000);
            return null;
        }
        if (!response.ok) {
            let msg = "Something went wrong.";
            try {
                const errData = await response.json();
                msg = errData.message || msg;
            } catch (e) {}
            showToast(msg, "error");
            return null;
        }
        return await response.json();
    } catch (error) {
        showToast("Unable to connect to the server. Please check that the Smart Attendance server is running.", "error");
        return null;
    }
}

// Intercept form submissions for Delete / Logout
document.addEventListener('DOMContentLoaded', () => {
    // Logout
    const logoutForms = document.querySelectorAll('form[action="/logout"]');
    logoutForms.forEach(form => {
        form.onsubmit = (e) => {
            e.preventDefault();
            showConfirmModal("Logout?", "Are you sure you want to logout from Smart Attendance?", "Logout", () => {
                form.submit();
            }, 'primary');
        };
    });

    // Handle flashed messages from backend
    document.querySelectorAll('.alert').forEach(a => {
        const type = a.classList.contains('alert-danger') ? 'error' : 'success';
        showToast(a.textContent, type);
        a.remove();
    });

    // Unsaved changes warning
    const forms = document.querySelectorAll('.form-grid, .warn-unsaved');
    let isDirty = false;
    forms.forEach(form => {
        form.addEventListener('input', () => { isDirty = true; });
        form.addEventListener('submit', () => { isDirty = false; });
    });
    window.addEventListener('beforeunload', (e) => {
        if (isDirty) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});
