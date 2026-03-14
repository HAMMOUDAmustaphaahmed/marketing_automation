/* ============================================================
   SMarketing — dashboard.js
   Graphiques Chart.js + widgets tableau de bord
   ============================================================ */

'use strict';

/* ── Funnel Chart (Bar horizontal) ──────────────────────────── */
window.initFunnelChart = function(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const colors = [
    'rgba(219,234,254,.9)',  // new — blue-100
    'rgba(147,197,253,.9)',  // contacted — blue-300
    'rgba(253,230,138,.9)',  // replied — yellow-200
    'rgba(167,243,208,.9)',  // interested — green-200
    'rgba(221,214,254,.9)',  // quoted — purple-200
    'rgba(167,243,208,.9)',  // won — green-200
  ];
  const borders = ['#1a56db','#3b82f6','#f59e0b','#059669','#7c3aed','#059669'];

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Prospects',
        data,
        backgroundColor: colors,
        borderColor: borders,
        borderWidth: 2,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.parsed.y} prospect${ctx.parsed.y > 1 ? 's' : ''}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: { stepSize: 1, font: { size: 11 } }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 11 } }
        }
      }
    }
  });
};


/* ── Pipeline Donut Chart ────────────────────────────────────── */
window.initPipelineDonut = function(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: ['#1a56db','#f59e0b','#7c3aed','#059669','#dc2626','#0891b2','#d97706'],
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 10,
            padding: 10,
            font: { size: 11 }
          }
        }
      }
    }
  });
};


/* ── Revenue Line Chart ──────────────────────────────────────── */
window.initRevenueChart = function(canvasId, labels, wonData, pipelineData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'CA Réalisé (TND)',
          data: wonData,
          borderColor: '#059669',
          backgroundColor: 'rgba(5,150,105,.08)',
          fill: true,
          tension: .4,
          pointRadius: 4,
          pointBackgroundColor: '#059669',
        },
        {
          label: 'Pipeline (TND)',
          data: pipelineData,
          borderColor: '#1a56db',
          backgroundColor: 'rgba(26,86,219,.06)',
          fill: true,
          tension: .4,
          pointRadius: 4,
          pointBackgroundColor: '#1a56db',
          borderDash: [5, 3],
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { boxWidth: 10, padding: 10, font: { size: 11 } }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: {
            font: { size: 11 },
            callback: v => formatNumber(v) + ' TND'
          }
        },
        x: { grid: { display: false }, ticks: { font: { size: 11 } } }
      }
    }
  });
};


/* ── Conversion Rate Gauge ───────────────────────────────────── */
window.updateConversionGauge = function(elementId, rate) {
  const el = document.getElementById(elementId);
  if (!el) return;

  const color = rate >= 50 ? '#059669' : rate >= 25 ? '#f59e0b' : '#dc2626';
  el.style.background = `conic-gradient(${color} ${rate * 3.6}deg, #e2e8f0 0deg)`;

  const label = el.querySelector('.gauge-label');
  if (label) {
    label.textContent = rate + '%';
    label.style.color = color;
  }
};


/* ── KPI Counter Animation ───────────────────────────────────── */
window.animateCounters = function() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count);
    const duration = 800;
    const step = target / (duration / 16);
    let current = 0;

    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = Math.floor(current).toLocaleString('fr-TN');
      if (current >= target) clearInterval(timer);
    }, 16);
  });
};


/* ── Init on DOM ready ───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  animateCounters();

  // Funnel chart (data injected by Jinja)
  if (window._funnelData) {
    initFunnelChart('funnelChart', window._funnelData.labels, window._funnelData.counts);
  }

  // Pipeline donut
  if (window._pipelineData) {
    initPipelineDonut('pipelineDonut', window._pipelineData.labels, window._pipelineData.values);
  }
});
