/* ============================================================
   SMarketing — prospects.js
   Filtres, status update, score bar animation
   ============================================================ */

'use strict';

/* ── Animate score bars on load ─────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.score-fill').forEach(bar => {
    const target = parseInt(bar.dataset.score || bar.style.width) || 0;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target + '%'; }, 100);
  });
});


/* ── Quick status update via dropdown ───────────────────────── */
window.quickStatus = function(selectEl, prospectId) {
  const newStatus = selectEl.value;
  if (!newStatus) return;

  const form = document.createElement('form');
  form.method = 'POST';
  form.action = `/prospects/${prospectId}/status`;

  const input = document.createElement('input');
  input.type  = 'hidden';
  input.name  = 'status';
  input.value = newStatus;
  form.appendChild(input);

  document.body.appendChild(form);
  form.submit();
};


/* ── Bulk export selected prospects ─────────────────────────── */
window.exportSelected = function() {
  const checked = Array.from(document.querySelectorAll('.prospect-checkbox:checked'))
    .map(cb => cb.value);

  if (checked.length === 0) {
    showToast('Sélectionnez au moins un prospect.', 'warning');
    return;
  }

  const url = '/prospects/export?ids=' + checked.join(',');
  window.open(url, '_blank');
};


/* ── Relevance score color helper ───────────────────────────── */
window.scoreColor = function(score) {
  if (score >= 70) return '#059669';
  if (score >= 40) return '#1a56db';
  return '#94a3b8';
};


/* ── Send individual email modal pre-fill ───────────────────── */
window.openEmailModal = function(prospectId, email, name, company) {
  const modal     = document.getElementById('individualEmailModal');
  const idInput   = document.getElementById('emailProspectId');
  const toDisplay = document.getElementById('emailTo');

  if (!modal) return;

  if (idInput)   idInput.value   = prospectId;
  if (toDisplay) toDisplay.value = `${name} <${email}> — ${company}`;

  bootstrap.Modal.getOrCreateInstance(modal).show();
};
