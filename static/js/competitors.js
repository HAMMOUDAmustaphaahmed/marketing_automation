/* ============================================================
   SMarketing — competitors.js
   Actions concurrents : recherche live, filtres, delete
   ============================================================ */

'use strict';

/* ── Live search filter ──────────────────────────────────────── */
(function liveSearch() {
  const input = document.getElementById('competitorSearch');
  if (!input) return;

  input.addEventListener('input', debounce(function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll('tbody tr').forEach(row => {
      const name = row.querySelector('td:first-child')?.textContent.toLowerCase() || '';
      row.style.display = !q || name.includes(q) ? '' : 'none';
    });
  }, 300));
})();


/* ── Sort table by column ────────────────────────────────────── */
window.sortTable = function(colIndex) {
  const tbody = document.querySelector('table tbody');
  if (!tbody) return;

  const rows = Array.from(tbody.querySelectorAll('tr'));
  const dir  = tbody.dataset.sortDir === 'asc' ? -1 : 1;
  tbody.dataset.sortDir = dir === 1 ? 'asc' : 'desc';

  rows.sort((a, b) => {
    const aText = a.cells[colIndex]?.textContent.trim() || '';
    const bText = b.cells[colIndex]?.textContent.trim() || '';
    return aText.localeCompare(bText, 'fr', { numeric: true }) * dir;
  });

  rows.forEach(row => tbody.appendChild(row));
};


/* ── SWOT expand/collapse ────────────────────────────────────── */
window.toggleSwot = function(btn) {
  const swotBox = btn.nextElementSibling;
  if (!swotBox) return;
  const isHidden = swotBox.style.display === 'none' || !swotBox.style.display;
  swotBox.style.display = isHidden ? 'block' : 'none';
  btn.innerHTML = isHidden
    ? '<i class="fas fa-chevron-up me-1"></i>Masquer SWOT'
    : '<i class="fas fa-chess-king me-1"></i>Voir SWOT';
};
