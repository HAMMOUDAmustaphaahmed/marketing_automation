/* ============================================================
   SMarketing — main.js
   Scripts globaux : alertes, sidebar, helpers
   ============================================================ */

'use strict';

/* ── Auto-dismiss Flash Messages ────────────────────────────── */
(function autoDissmissAlerts() {
  const dismiss = () => {
    document.querySelectorAll('.flash-container .alert').forEach(el => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    });
  };
  setTimeout(dismiss, 5000);
})();


/* ── Mobile Sidebar Toggle ───────────────────────────────────── */
(function sidebarToggle() {
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebarOverlay');

  if (!toggleBtn || !sidebar) return;

  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('show');
    if (overlay) overlay.classList.toggle('show');
  });

  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('show');
      overlay.classList.remove('show');
    });
  }
})();


/* ── Confirm Delete ──────────────────────────────────────────── */
document.addEventListener('click', function(e) {
  const btn = e.target.closest('[data-confirm]');
  if (btn) {
    const msg = btn.dataset.confirm || 'Êtes-vous sûr de vouloir effectuer cette action ?';
    if (!confirm(msg)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }
});


/* ── Loading Overlay on Form Submit ─────────────────────────── */
(function formLoadingState() {
  document.querySelectorAll('form[data-loading]').forEach(form => {
    form.addEventListener('submit', function() {
      const btn = this.querySelector('[type="submit"]');
      if (btn) {
        const label = btn.dataset.loadingText || 'Chargement...';
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${label}`;
      }
    });
  });
})();


/* ── Tooltip initialization ──────────────────────────────────── */
(function initTooltips() {
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => new bootstrap.Tooltip(el, { trigger: 'hover' }));
})();


/* ── Score bar animation on page load ───────────────────────── */
(function animateScoreBars() {
  const bars = document.querySelectorAll('.score-fill[data-width]');
  setTimeout(() => {
    bars.forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  }, 200);
})();


/* ── Utility: format number with thousand separator ─────────── */
window.formatNumber = function(n, decimals = 0) {
  return Number(n).toLocaleString('fr-TN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};


/* ── Utility: copy text to clipboard ────────────────────────── */
window.copyToClipboard = function(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    if (btn) {
      const original = btn.innerHTML;
      btn.innerHTML = '<i class="fas fa-check"></i>';
      btn.classList.add('text-success');
      setTimeout(() => {
        btn.innerHTML = original;
        btn.classList.remove('text-success');
      }, 1500);
    }
  });
};


/* ── Utility: show toast notification ───────────────────────── */
window.showToast = function(message, type = 'success') {
  const container = document.querySelector('.flash-container');
  if (!container) return;

  const icons = { success: 'check-circle', error: 'times-circle', warning: 'exclamation-triangle', info: 'info-circle' };
  const bsType = type === 'error' ? 'danger' : type;

  const div = document.createElement('div');
  div.className = `alert alert-${bsType} alert-dismissible fade show shadow-sm`;
  div.style.fontSize = '.875rem';
  div.innerHTML = `
    <i class="fas fa-${icons[type] || 'info-circle'} me-2"></i>${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  container.appendChild(div);

  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(div);
    if (bsAlert) bsAlert.close();
  }, 5000);
};


/* ── Search input debounce ───────────────────────────────────── */
window.debounce = function(fn, delay = 400) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
};


/* ── Active sidebar link highlight ──────────────────────────── */
(function highlightActiveSidebarLink() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('#sidebar .nav-link').forEach(link => {
    if (link.getAttribute('href') && currentPath.startsWith(link.getAttribute('href'))) {
      link.classList.add('active');
    }
  });
})();


/* ── File upload preview ────────────────────────────────────── */
document.querySelectorAll('input[type="file"][data-preview]').forEach(input => {
  input.addEventListener('change', function() {
    const previewId = this.dataset.preview;
    const preview = document.getElementById(previewId);
    if (!preview || !this.files[0]) return;

    const file = this.files[0];
    const sizeKB = (file.size / 1024).toFixed(0);
    preview.textContent = `📎 ${file.name} (${sizeKB} KB)`;
    preview.style.color = '#059669';
  });
});


/* ── Responsive table scroll hint ───────────────────────────── */
(function tableScrollHint() {
  document.querySelectorAll('.table-responsive').forEach(wrapper => {
    if (wrapper.scrollWidth > wrapper.clientWidth) {
      wrapper.style.boxShadow = 'inset -8px 0 10px -8px rgba(0,0,0,.1)';
    }
  });
})();
