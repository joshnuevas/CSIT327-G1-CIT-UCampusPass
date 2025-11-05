(() => {
  // === READ JSON DATA ===
  let visits = [];
  try {
    const el = document.getElementById('visits-data');
    visits = JSON.parse(el.textContent || '[]');
  } catch (e) {
    console.error('Failed to parse visits data', e);
  }

  // === INITIAL SORT ===
  visits.sort((a, b) => (a.visit_id || 0) - (b.visit_id || 0));

  const state = {
    status: 'All',
  };

  // === HELPERS ===
  function formatDate(dStr) {
    if (!dStr) return '';
    const d = new Date(dStr);
    return isNaN(d) ? dStr : d.toISOString().slice(0, 10);
  }

  function formatTime(tStr) {
    if (!tStr) return '';
    return tStr.slice(0, 5);
  }

  // === FILTER FUNCTION ===
  function matchesFilters(v) {
    if (state.status !== 'All') {
      return (v.status || '').toLowerCase() === state.status.toLowerCase();
    }
    return true;
  }

  // === RENDER FUNCTION ===
  function render() {
    const tbody = document.getElementById('visitsTbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const filtered = visits.filter(matchesFilters);

    for (const v of filtered) {
      const tr = document.createElement('tr');
      tr.dataset.status = v.status || '';
      tr.innerHTML = `
        <td>${v.visit_id || ''}</td>
        <td>${formatDate(v.visit_date)}</td>
        <td>${v.code || ''}</td>
        <td>${v.user_email || ''}</td>
        <td>${v.purpose || ''}</td>
        <td>${v.department || ''}</td>
        <td>${formatTime(v.start_time)} - ${formatTime(v.end_time)}</td>
        <td><span class="status ${v.status?.toLowerCase() || ''}">${v.status || ''}</span></td>
      `;
      tbody.appendChild(tr);
    }

    if (filtered.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="8" style="text-align:center;">No visit records found.</td>`;
      tbody.appendChild(tr);
    }
  }

  // === EVENT BINDINGS ===
  document.addEventListener('DOMContentLoaded', () => {
    const statusFilter = document.getElementById('statusFilter');
    const exportBtn = document.getElementById('exportCSV');

    if (statusFilter) {
      statusFilter.addEventListener('change', (e) => {
        state.status = e.target.value;
        render();
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        let csv = "ID,Register Date,Code,Visitor,Purpose,Department,Start-End,Status\n";
        visits.filter(matchesFilters).forEach(v => {
          const row = [
            v.visit_id || '',
            formatDate(v.visit_date),
            v.code || '',
            v.user_email || '',
            v.purpose || '',
            v.department || '',
            `${formatTime(v.start_time)} - ${formatTime(v.end_time)}`,
            v.status || ''
          ].map(x => `"${x}"`).join(',');
          csv += row + '\n';
        });
        const blob = new Blob([csv], { type: "text/csv" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "visit_records.csv";
        link.click();
      });
    }

    render();
  });
})();
