/* ============================================================
   SMarketing — quote.js
   Calcul dynamique des devis (lignes, totaux, TVA)
   ============================================================ */

'use strict';

/* ── Add item row ────────────────────────────────────────────── */
function addItemRow() {
  const container = document.getElementById('itemsContainer');
  const rowIndex  = container.querySelectorAll('.item-row').length;

  const row = document.createElement('div');
  row.className = 'row g-2 mb-2 item-row align-items-end';
  row.innerHTML = `
    <div class="col-md-5">
      <input type="text" name="item_description[]" class="form-control form-control-sm"
             placeholder="Description de la prestation" required>
    </div>
    <div class="col-md-2">
      <input type="number" name="item_quantity[]" class="form-control form-control-sm item-qty"
             placeholder="Qté" value="1" step="0.01" min="0">
    </div>
    <div class="col-md-2">
      <input type="number" name="item_price[]" class="form-control form-control-sm item-price"
             placeholder="Prix HT" step="0.01" min="0">
    </div>
    <div class="col-md-1">
      <input type="number" name="item_discount[]" class="form-control form-control-sm item-discount"
             placeholder="%" value="0" step="1" min="0" max="100">
    </div>
    <div class="col-md-2">
      <div class="d-flex gap-1">
        <input type="text" class="form-control form-control-sm item-total-display"
               placeholder="Total" readonly style="background:#f8fafc; font-weight:600; color:#1a56db;">
        <button type="button" class="btn btn-sm btn-light text-danger flex-shrink-0"
                onclick="removeRow(this)" title="Supprimer">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>`;

  container.appendChild(row);
  attachRowListeners(row);
}


/* ── Remove item row ─────────────────────────────────────────── */
function removeRow(btn) {
  btn.closest('.item-row').remove();
  calcTotals();
}


/* ── Calc single row total ───────────────────────────────────── */
function calcRowTotal(row) {
  const qty      = parseFloat(row.querySelector('.item-qty')?.value)      || 0;
  const price    = parseFloat(row.querySelector('.item-price')?.value)    || 0;
  const discount = parseFloat(row.querySelector('.item-discount')?.value) || 0;
  const total    = qty * price * (1 - discount / 100);

  const display = row.querySelector('.item-total-display');
  if (display) {
    display.value = total > 0 ? total.toFixed(2) + ' TND' : '';
  }
  return total;
}


/* ── Calc all totals ─────────────────────────────────────────── */
function calcTotals() {
  let totalHT = 0;

  document.querySelectorAll('.item-row').forEach(row => {
    totalHT += calcRowTotal(row);
  });

  const tvaInput  = document.querySelector('[name="tva"]');
  const tvaRate   = tvaInput ? parseFloat(tvaInput.value) || 19 : 19;
  const tvaAmount = totalHT * tvaRate / 100;
  const totalTTC  = totalHT + tvaAmount;

  // Update display elements
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val.toFixed(2) + ' TND';
  };
  set('totalHT', totalHT);
  set('totalTVA', tvaAmount);
  set('totalTTC', totalTTC);

  // Update hidden fields if present
  const htField  = document.querySelector('[name="total_ht_hidden"]');
  const ttcField = document.querySelector('[name="total_ttc_hidden"]');
  if (htField)  htField.value  = totalHT.toFixed(2);
  if (ttcField) ttcField.value = totalTTC.toFixed(2);
}


/* ── Attach listeners to row inputs ─────────────────────────── */
function attachRowListeners(row) {
  row.querySelectorAll('.item-qty, .item-price, .item-discount').forEach(input => {
    input.addEventListener('input', () => {
      calcRowTotal(row);
      calcTotals();
    });
  });
}


/* ── Toggle internal vs upload form ─────────────────────────── */
function toggleQuoteSource(val) {
  const internal = document.getElementById('internalSection');
  const upload   = document.getElementById('uploadSection');
  if (internal) internal.style.display = val === 'internal' ? 'block' : 'none';
  if (upload)   upload.style.display   = val === 'uploaded'  ? 'block' : 'none';
}


/* ── Init on DOM ready ───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  // Attach listeners to existing rows
  document.querySelectorAll('.item-row').forEach(attachRowListeners);

  // TVA change
  const tvaInput = document.querySelector('[name="tva"]');
  if (tvaInput) tvaInput.addEventListener('input', calcTotals);

  // Source radio buttons
  document.querySelectorAll('[name="source"]').forEach(radio => {
    radio.addEventListener('change', e => toggleQuoteSource(e.target.value));
  });

  // Initial calculation
  calcTotals();
});
