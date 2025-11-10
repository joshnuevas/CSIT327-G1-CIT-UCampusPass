(() => {
  let logs = [];
  try {
    logs = JSON.parse(document.getElementById("logs-data").textContent) || [];
  } catch (e) {
    logs = [];
  }

  const state = { 
    role: "All", 
    createdDate: null, 
    page: 1, 
    perPage: 25 
  };

  const tbody = document.getElementById("logsTbody");
  const paginationContainer = document.getElementById("pagination");

  // ===== Helper: Fix Supabase timestamp + format to PH time =====
  function formatToPhilippineTime(dateString) {
    if (!dateString) return "-";

    let cleanDate = dateString.trim();
    if (!cleanDate.endsWith("Z") && !cleanDate.includes("+")) cleanDate += "Z";

    const parsedDate = new Date(cleanDate);
    if (isNaN(parsedDate.getTime())) return "-";

    return parsedDate.toLocaleString("en-PH", {
      timeZone: "Asia/Manila",
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  }

  // ===== Filtering logic =====
  function matchesFilter(l) {
    if (state.role !== "All" && l.actor_role !== state.role) return false;

    if (state.createdDate) {
      const logDatePH = new Date(l.created_at).toLocaleDateString("en-CA", {
        timeZone: "Asia/Manila",
      });
      if (logDatePH !== state.createdDate) return false;
    }

    return true;
  }

  // ===== Pagination logic =====
  function getFilteredPaginatedLogs() {
    const filtered = logs.filter(matchesFilter);
    const start = (state.page - 1) * state.perPage;
    const end = start + state.perPage;
    const paginated = filtered.slice(start, end);
    return { filtered, paginated };
  }

  function renderPagination(totalItems) {
    paginationContainer.innerHTML = "";

    const totalPages = Math.ceil(totalItems / state.perPage);
    if (totalPages <= 1) return;

    const prevBtn = document.createElement("button");
    prevBtn.textContent = "Prev";
    prevBtn.classList.add("prev");

    const nextBtn = document.createElement("button");
    nextBtn.textContent = "Next";
    nextBtn.classList.add("next");

    const pageInfo = document.createElement("span");
    pageInfo.textContent = `Page ${state.page} of ${totalPages}`;

    prevBtn.disabled = state.page === 1;
    nextBtn.disabled = state.page === totalPages;

    prevBtn.addEventListener("click", () => {
        if(state.page > 1) { state.page--; render(); }
    });
    nextBtn.addEventListener("click", () => {
        if(state.page < totalPages) { state.page++; render(); }
    });

    paginationContainer.appendChild(prevBtn);
    paginationContainer.appendChild(pageInfo);
    paginationContainer.appendChild(nextBtn);
  }

  // ===== Render table =====
  function render() {
    tbody.innerHTML = "";

    const { filtered, paginated } = getFilteredPaginatedLogs();

    if (paginated.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="6" style="text-align:center">No logs found</td>`;
      tbody.appendChild(tr);
      paginationContainer.innerHTML = "";
      return;
    }

    paginated.forEach(l => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${l.log_id}</td>
        <td>${l.actor || "-"}</td>
        <td>${l.action_type || "-"}</td>
        <td>${l.description || "-"}</td>
        <td>${l.actor_role || "-"}</td>
        <td>${formatToPhilippineTime(l.created_at)}</td>
      `;
      tbody.appendChild(tr);
    });

    renderPagination(filtered.length);
  }

  // ===== Event listeners =====
  document.getElementById("actorRoleFilter").addEventListener("change", e => {
    state.role = e.target.value;
    state.page = 1;
    render();
  });

  document.getElementById("createdDateFilter").addEventListener("change", e => {
    state.createdDate = e.target.value || null;
    state.page = 1;
    render();
  });

  const exportBtn = document.querySelector(".export-btn");
  const exportMenu = document.querySelector(".export-menu");

  exportBtn.addEventListener("click", (e) => {
    e.stopPropagation(); 
    exportMenu.classList.toggle("show");
    exportBtn.setAttribute("aria-expanded", exportMenu.classList.contains("show"));
  });

  // Prevent menu clicks from closing dropdown
  exportMenu.addEventListener("click", e => e.stopPropagation());

  // Close if clicked outside
  document.addEventListener("click", (e) => {
    if (!exportBtn.contains(e.target) && !exportMenu.contains(e.target)) {
      exportMenu.classList.remove("show");
      exportBtn.setAttribute("aria-expanded", false);
    }
  });

  // ===== Helper: get filter description =====
  function getFilterDescription() {
    let desc = [];
    if (state.role && state.role !== "All") desc.push(`Actor Role: ${state.role}`);
    if (state.createdDate) desc.push(`Created Date: ${state.createdDate}`);
    if (desc.length === 0) return "No filters applied; exporting all logs.";
    return "Filters applied: " + desc.join(", ");
  }

  // ===== CSV export (updated) =====
  document.getElementById("exportCSV").addEventListener("click", () => {
    exportMenu.classList.remove("show");
    exportBtn.setAttribute("aria-expanded", false);
    const filtered = logs.filter(matchesFilter);
    if (filtered.length === 0) return alert("No data to export!");

    let csv = `"${getFilterDescription()}"\n\nID,Actor,Action Type,Description,Actor Role,Timestamp\n`;
    filtered.forEach(l => {
      csv += `"${l.log_id}","${l.actor}","${l.action_type}","${l.description}","${l.actor_role}","${formatToPhilippineTime(l.created_at)}"\n`;
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "system_logs.csv";
    link.click();
  });

  // ===== PDF export (updated) =====
  document.getElementById("exportPDF").addEventListener("click", () => {
    exportMenu.classList.remove("show");
    exportBtn.setAttribute("aria-expanded", false);
    const filtered = logs.filter(matchesFilter);
    if (filtered.length === 0) return alert("No data to export!");

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Add filter info at the top
    doc.setFontSize(12);
    doc.text(getFilterDescription(), 14, 10);

    const columns = ["ID", "Actor", "Action Type", "Description", "Actor Role", "Timestamp"];
    const rows = filtered.map(l => [
      l.log_id,
      l.actor || "-",
      l.action_type || "-",
      l.description || "-",
      l.actor_role || "-",
      formatToPhilippineTime(l.created_at)
    ]);

    doc.autoTable({
      head: [columns],
      body: rows,
      startY: 20,
      styles: { fontSize: 10 }
    });
    doc.save("system_logs.pdf");
  });


  // ===== Initial render =====
  render();
})();
