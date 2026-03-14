/* ============================================================
   SMarketing — mailing.js
   Éditeur email + génération IA template + campagne
   ============================================================ */

'use strict';

/* ── Generate Email Template with Grok AI ───────────────────── */
window.generateEmailAI = async function() {
  const sector    = document.getElementById('aiSector')?.value || '';
  const contact   = document.getElementById('aiContact')?.value || '';
  const loadCard  = document.getElementById('aiLoadingCard');
  const subjectEl = document.getElementById('emailSubject');
  const bodyEl    = document.getElementById('emailBody');

  if (!subjectEl || !bodyEl) return;

  // Show loading
  if (loadCard) loadCard.style.display = 'block';

  const genBtn = document.getElementById('generateBtn');
  if (genBtn) {
    genBtn.disabled = true;
    genBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Génération...';
  }

  try {
    const resp = await fetch('/mailing/generate-template', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sector, contact })
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data = await resp.json();

    if (data.error) {
      showToast('Erreur IA : ' + data.error, 'error');
    } else {
      subjectEl.value = data.subject || '';
      bodyEl.value    = data.body    || '';
      showToast('Template généré par IA avec succès !', 'success');

      // Trigger preview update
      updateEmailPreview();
    }
  } catch (err) {
    showToast('Erreur de connexion : ' + err.message, 'error');
  } finally {
    if (loadCard) loadCard.style.display = 'none';
    if (genBtn) {
      genBtn.disabled = false;
      genBtn.innerHTML = '<i class="fas fa-magic me-1"></i>Générer avec IA';
    }
  }
};


/* ── Live Email Preview ──────────────────────────────────────── */
window.updateEmailPreview = function() {
  const bodyEl   = document.getElementById('emailBody');
  const preview  = document.getElementById('emailPreview');
  if (!bodyEl || !preview) return;

  // Replace template variables with sample data
  let html = bodyEl.value
    .replace(/\{\{name\}\}/g, '<strong>Mohamed Ben Ali</strong>')
    .replace(/\{\{company\}\}/g, '<strong>Entreprise Demo</strong>');

  preview.innerHTML = html || '<p style="color:#94a3b8; font-style:italic;">Aperçu de votre email...</p>';
};


/* ── Character count for subject ────────────────────────────── */
(function subjectCharCount() {
  const input   = document.getElementById('emailSubject');
  const counter = document.getElementById('subjectCounter');
  if (!input || !counter) return;

  const update = () => {
    const len = input.value.length;
    counter.textContent = `${len}/150`;
    counter.style.color = len > 100 ? '#d97706' : len > 130 ? '#dc2626' : '#94a3b8';
  };
  input.addEventListener('input', update);
  update();
})();


/* ── Body live preview on input ─────────────────────────────── */
(function bodyLivePreview() {
  const bodyEl = document.getElementById('emailBody');
  if (!bodyEl) return;
  bodyEl.addEventListener('input', debounce(updateEmailPreview, 400));
  updateEmailPreview(); // Initial render
})();


/* ── Toggle recipient target select ─────────────────────────── */
window.toggleRecipientGroup = function(select) {
  const sectorGroup   = document.getElementById('sectorGroup');
  const specificGroup = document.getElementById('specificGroup');

  if (sectorGroup)   sectorGroup.style.display   = select.value === 'sector'   ? 'block' : 'none';
  if (specificGroup) specificGroup.style.display  = select.value === 'specific' ? 'block' : 'none';
};


/* ── Select / deselect all prospects checkboxes ─────────────── */
window.toggleAllProspects = function(masterCb) {
  document.querySelectorAll('.prospect-checkbox').forEach(cb => {
    cb.checked = masterCb.checked;
  });
  updateSelectedCount();
};

window.updateSelectedCount = function() {
  const count = document.querySelectorAll('.prospect-checkbox:checked').length;
  const display = document.getElementById('selectedCount');
  if (display) display.textContent = count + ' sélectionné(s)';
};


/* ── Mark log as replied inline ─────────────────────────────── */
window.markReplied = async function(logId, btn) {
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

  try {
    const resp = await fetch(`/mailing/log/${logId}/replied`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    if (resp.redirected || resp.ok) {
      const row = btn.closest('tr');
      if (row) {
        const statusCell = row.querySelector('.log-status');
        if (statusCell) {
          statusCell.innerHTML = '<span class="badge bg-success" style="font-size:.65rem;">replied</span>';
        }
        btn.outerHTML = '<a href="#" class="btn btn-xs btn-success" style="font-size:.7rem; padding:2px 8px;" onclick="createOpp(' + logId + ')">+ Opportunité</a>';
      }
      showToast('Réponse enregistrée !', 'success');
    }
  } catch (err) {
    showToast('Erreur : ' + err.message, 'error');
    btn.disabled = false;
    btn.innerHTML = 'A répondu ✓';
  }
};


/* ── Init ────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  // Recipient target select
  const targetSelect = document.querySelector('[name="target"]');
  if (targetSelect) {
    targetSelect.addEventListener('change', e => toggleRecipientGroup(e.target));
  }

  // Prospect checkboxes
  document.querySelectorAll('.prospect-checkbox').forEach(cb => {
    cb.addEventListener('change', updateSelectedCount);
  });
});
