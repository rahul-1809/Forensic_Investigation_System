document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('toast-container');
  if (!container) return;

  function setupToast(t, i) {
    // animate in
    setTimeout(() => t.classList.add('visible'), 50 + i * 200);
    const close = t.querySelector('.toast-close');
    const remove = () => { t.classList.remove('visible'); setTimeout(() => t.remove(), 400); };
    if (close) close.addEventListener('click', remove);
    // auto-dismiss
    setTimeout(remove, 4200 + i * 800);
  }

  const toasts = Array.from(container.querySelectorAll('.toast'));
  toasts.forEach(setupToast);

  // expose a helper to create toasts dynamically (for AJAX flows)
  window.showToast = function(message, type = 'success', opts = {}) {
    const t = document.createElement('div');
    t.className = `toast ${type === 'error' ? 'error' : 'success'}`;
    t.innerHTML = `<span class="toast-message"></span><button class="toast-close" aria-label="Close">×</button>`;
    t.querySelector('.toast-message').textContent = message;
    container.appendChild(t);
    const index = container.querySelectorAll('.toast').length - 1;
    setupToast(t, index);
    return t;
  };
});
