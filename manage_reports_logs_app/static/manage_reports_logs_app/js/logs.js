(() => {
  let logs = [];
  try {
    logs = JSON.parse(document.getElementById("logs-data").textContent) || [];
  } catch (e) {
    logs = [];
  }

  const state = { role: "All", createdDate: null, page: 1, perPage: 25 };

  // ===== Helper: Fix Supabase timestamp + format to PH time =====
  function formatToPhilippineTime(dateString) {
    if (!dateString) return "-";

    // Ensure a valid ISO 8601 format (Supabase may omit Z/timezone)
    // Example input: "2025-11-08T09:16:59.850165" → "2025-11-08T09:16:59.850165Z"
    let cleanDate = dateString.trim();
    if (!cleanDate.endsWith("Z") && !cleanDate.includes("+")) cleanDate += "Z";

    const parsedDate = new Date(cleanDate);
    if (isNaN(parsedDate.getTime())) return "-";

    // Convert to PH time
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
      timeZone: "Asia/Manila"
    }); // "YYYY-MM-DD" format
    if (logDatePH !== state.createdDate) return false;
  }

  return true;
}

  // ===== Render table =====
  function render() {
    const tbody = document.getElementById("logsTbody");
    tbody.innerHTML = "";

    const filtered = logs.filter(matchesFilter);
    const start = (state.page - 1) * state.perPage;
    const pageSlice = filtered.slice(start, start + state.perPage);

    if (pageSlice.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="6" style="text-align:center">No logs found</td>`;
      tbody.appendChild(tr);
    } else {
      pageSlice.forEach(l => {
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
    }
  }

  // ===== Event listeners =====
  document.getElementById("actorRoleFilter").addEventListener("change", e => {
    state.role = e.target.value;
    render();
  });

  document.getElementById("createdDateFilter").addEventListener("change", e => {
    state.createdDate = e.target.value || null;
    render();
  });

  document.getElementById("exportCSV").addEventListener("click", () => {
    let csv = "ID,Actor,Action Type,Description,Actor Role,Timestamp\n";
    logs.forEach(l => {
      csv += `"${l.log_id}","${l.actor}","${l.action_type}","${l.description}","${l.actor_role}","${formatToPhilippineTime(l.created_at)}"\n`;
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "system_logs.csv";
    link.click();
  });

  // ===== Initial render =====
  render();
})();
