(() => {
  // === READ JSON DATA ===
  let visits = [];
  try {
    const el = document.getElementById('visits-data');
    visits = JSON.parse(el.textContent || '[]');
  } catch (e) {
    console.error('Failed to parse visits data', e);
  }

  // === SORT BY ID DESCENDING ===
  visits.sort((a, b) => (b.visit_id || 0) - (a.visit_id || 0));

  const state = {
    status: 'All',
    registerDate: null,
    page: 1,
    perPage: 25
  };

  const tbody = document.getElementById('visitsTbody');
  const paginationContainer = document.getElementById('pagination');

  // ===== HELPERS =====
  function formatDate(dStr) {
    if (!dStr) return '-';
    const d = new Date(dStr);
    if (isNaN(d)) return dStr;
    return d.toLocaleDateString('en-CA'); // YYYY-MM-DD
  }

  function formatTime(tStr) {
    if (!tStr) return '';
    return tStr.slice(0, 5);
  }

  function matchesFilters(v) {
    if (state.status !== 'All' && (v.status || '').toLowerCase() !== state.status.toLowerCase()) {
      return false;
    }

    if (state.registerDate) {
      const visitDate = new Date(v.visit_date).toLocaleDateString('en-CA');
      if (visitDate !== state.registerDate) return false;
    }

    return true;
  }

  // ===== PAGINATION =====
  function getFilteredPaginatedVisits() {
    const filtered = visits.filter(matchesFilters);
    const start = (state.page - 1) * state.perPage;
    const end = start + state.perPage;
    const paginated = filtered.slice(start, end);
    return { filtered, paginated };
  }

  function renderPagination(totalItems) {
    paginationContainer.innerHTML = '';

    const totalPages = Math.ceil(totalItems / state.perPage);
    if (totalPages <= 1) return;

    const prevBtn = document.createElement('button');
    prevBtn.textContent = 'Prev';
    prevBtn.classList.add('prev');
    prevBtn.disabled = state.page === 1;

    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Next';
    nextBtn.classList.add('next');
    nextBtn.disabled = state.page === totalPages;

    const pageInfo = document.createElement('span');
    pageInfo.textContent = `Page ${state.page} of ${totalPages}`;

    prevBtn.addEventListener('click', () => {
      if (state.page > 1) { state.page--; render(); }
    });
    nextBtn.addEventListener('click', () => {
      if (state.page < totalPages) { state.page++; render(); }
    });

    paginationContainer.appendChild(prevBtn);
    paginationContainer.appendChild(pageInfo);
    paginationContainer.appendChild(nextBtn);
  }

  // ===== RENDER TABLE =====
  function render() {
    tbody.innerHTML = '';

    const { filtered, paginated } = getFilteredPaginatedVisits();

    if (paginated.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="8" style="text-align:center;">No visit records found.</td>`;
      tbody.appendChild(tr);
      paginationContainer.innerHTML = '';
      return;
    }

    paginated.forEach(v => {
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
    });

    renderPagination(filtered.length);
  }

  // ===== EXPORT HELPERS =====
  function getFilterDescription() {
    const desc = [];
    if (state.status && state.status !== 'All') desc.push(`Status: ${state.status}`);
    if (state.registerDate) desc.push(`Register Date: ${state.registerDate}`);
    return desc.length ? "Filters applied: " + desc.join(', ') : "No filters applied; exporting all visits.";
  }

  function exportCSV() {
    const filtered = visits.filter(matchesFilters);
    if (!filtered.length) return alert("No data to export!");

    let csv = `"${getFilterDescription()}"\n\nID,Register Date,Code,Visitor,Purpose,Department,Start-End,Status\n`;
    filtered.forEach(v => {
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
  }

  function exportPDF() {
    const filtered = visits.filter(matchesFilters);
    if (!filtered.length) return alert("No data to export!");

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    doc.setFontSize(12);
    doc.text(getFilterDescription(), 14, 10);

    const columns = ["ID", "Register Date", "Code", "Visitor", "Purpose", "Department", "Start-End", "Status"];
    const rows = filtered.map(v => [
      v.visit_id || '',
      formatDate(v.visit_date),
      v.code || '',
      v.user_email || '',
      v.purpose || '',
      v.department || '',
      `${formatTime(v.start_time)} - ${formatTime(v.end_time)}`,
      v.status || ''
    ]);

    doc.autoTable({
      head: [columns],
      body: rows,
      startY: 20,
      styles: { fontSize: 10 }
    });

    doc.save("visit_records.pdf");
  }

  // ===== EVENT BINDINGS =====
  document.addEventListener('DOMContentLoaded', () => {
    const statusFilter = document.getElementById('statusFilter');
    const registerDateFilter = document.getElementById('registerDateFilter');
    const exportBtn = document.querySelector('.export-btn');
    const exportMenu = document.querySelector('.export-menu');

    if (statusFilter) {
      statusFilter.addEventListener('change', e => {
        state.status = e.target.value;
        state.page = 1;
        render();
      });
    }

    if (registerDateFilter) {
      registerDateFilter.addEventListener('change', e => {
        state.registerDate = e.target.value || null;
        state.page = 1;
        render();
      });
    }

    if (exportBtn && exportMenu) {
      exportBtn.addEventListener('click', e => {
        e.stopPropagation();
        exportMenu.classList.toggle('show');
        exportBtn.setAttribute('aria-expanded', exportMenu.classList.contains('show'));
      });

      exportMenu.addEventListener('click', e => e.stopPropagation());
      document.addEventListener('click', () => {
        exportMenu.classList.remove('show');
        exportBtn.setAttribute('aria-expanded', false);
      });

      document.getElementById('exportCSV').addEventListener('click', () => {
        exportMenu.classList.remove('show');
        exportBtn.setAttribute('aria-expanded', false);
        exportCSV();
      });

      document.getElementById('exportPDF').addEventListener('click', () => {
        exportMenu.classList.remove('show');
        exportBtn.setAttribute('aria-expanded', false);
        exportPDF();
      });
    }

    render();
  });
})();
