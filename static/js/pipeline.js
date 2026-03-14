/* ============================================================
   SMarketing — pipeline.js
   Kanban interactions + pipeline actions
   ============================================================ */

'use strict';

/* ── Quick stage update via AJAX ─────────────────────────────── */
window.quickUpdateStage = function(oppId, newStage) {
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = `/pipeline/opportunity/${oppId}/stage`;

  const stageInput = document.createElement('input');
  stageInput.type  = 'hidden';
  stageInput.name  = 'stage';
  stageInput.value = newStage;
  form.appendChild(stageInput);

  // CSRF token if needed
  const csrf = document.querySelector('meta[name="csrf-token"]');
  if (csrf) {
    const csrfInput = document.createElement('input');
    csrfInput.type  = 'hidden';
    csrfInput.name  = 'csrf_token';
    csrfInput.value = csrf.content;
    form.appendChild(csrfInput);
  }

  document.body.appendChild(form);
  form.submit();
};


/* ── Kanban card click navigation ────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.kanban-card[data-url]').forEach(card => {
    card.addEventListener('click', function(e) {
      if (!e.target.closest('button') && !e.target.closest('a')) {
        window.location.href = this.dataset.url;
      }
    });
  });
});


/* ── Pipeline filter ─────────────────────────────────────────── */
window.filterPipeline = function(query) {
  query = query.toLowerCase().trim();
  document.querySelectorAll('.kanban-card').forEach(card => {
    const text = card.textContent.toLowerCase();
    card.style.display = !query || text.includes(query) ? '' : 'none';
  });

  // Update column counts
  document.querySelectorAll('.kanban-col').forEach(col => {
    const visible = col.querySelectorAll('.kanban-card:not([style*="display: none"])').length;
    const countEl = col.querySelector('.col-count');
    if (countEl) countEl.textContent = visible;
  });
};


/* ── Stage statistics mini chart ────────────────────────────── */
window.renderStageSparkline = function(canvasId, value, max, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [value, Math.max(0, max - value)],
        backgroundColor: [color, '#f1f5f9'],
        borderWidth: 0,
        hoverOffset: 0,
      }]
    },
    options: {
      responsive: false,
      cutout: '70%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      animation: { duration: 800 }
    }
  });
};


/* ── Opportunity probability slider visual ───────────────────── */
(function probSlider() {
  const slider = document.getElementById('probabilitySlider');
  const display = document.getElementById('probabilityDisplay');
  if (!slider || !display) return;

  const update = () => {
    const val = parseInt(slider.value);
    display.textContent = val + '%';
    const color = val >= 70 ? '#059669' : val >= 40 ? '#f59e0b' : '#dc2626';
    display.style.color = color;
    slider.style.accentColor = color;
  };

  slider.addEventListener('input', update);
  update();
})();


/* ── Lost reason toggle ──────────────────────────────────────── */
(function lostReasonToggle() {
  const stageSelect   = document.querySelector('[name="stage"]');
  const lostReasonRow = document.getElementById('lostReasonRow');
  if (!stageSelect || !lostReasonRow) return;

  const toggle = () => {
    lostReasonRow.style.display = stageSelect.value === 'lost' ? 'block' : 'none';
  };
  stageSelect.addEventListener('change', toggle);
  toggle();
})();
