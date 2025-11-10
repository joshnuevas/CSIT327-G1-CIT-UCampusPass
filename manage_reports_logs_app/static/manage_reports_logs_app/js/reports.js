(() => {
  let visits = JSON.parse(document.getElementById("visits-data").textContent || "[]");
  let users = JSON.parse(document.getElementById("users-data").textContent || "[]");
  let staff = JSON.parse(document.getElementById("staff-data").textContent || "[]");

  const state = { status: "All", startDate: null, endDate: null };

  // ===== FILTERING =====
  function filterVisits(data) {
    return data.filter(v => {
      if (state.status !== "All" && v.status !== state.status) return false;
      if (state.startDate && new Date(v.visit_date) < new Date(state.startDate)) return false;
      if (state.endDate && new Date(v.visit_date) > new Date(state.endDate)) return false;
      return true;
    });
  }

  // ===== SUMMARY =====
  function updateSummary() {
    const filtered = filterVisits(visits);
    const totalVisitors = new Set(filtered.map(v => v.user_id)).size;
    const totalVisits = filtered.length;
    const upcoming = filtered.filter(v => v.status === "Upcoming").length;
    const ongoing = filtered.filter(v => v.status === "Ongoing").length;
    const completed = filtered.filter(v => v.status === "Completed").length;

    document.getElementById("totalVisitors").textContent = totalVisitors;
    document.getElementById("totalVisits").textContent = totalVisits;
    document.getElementById("upcomingVisits").textContent = upcoming;
    document.getElementById("ongoingVisits").textContent = ongoing;
    document.getElementById("completedVisits").textContent = completed;
  }

  // ===== CHARTS =====
  let visitTrendsChart, purposeChart, staffChart;

  function renderCharts() {
    const filtered = filterVisits(visits);
    updateSummary();

    if (!filtered.length) {
      document.getElementById("visitTrendsChart").style.display = "none";
      document.getElementById("purposeChart").style.display = "none";
      document.getElementById("staffChart").style.display = "none";
      return;
    }

    // --- Visit Trends Chart (with Cancelled & Expired) ---
    const statuses = ["Upcoming", "Ongoing", "Completed", "Cancelled", "Expired"];
    const statusColors = ["#8b1538", "#d44d5c", "#e88f9c", "#f5c3c8", "#fce2e3"];

    const trendLabels = [...new Set(filtered.map(v => v.visit_date))].sort();
    const trendDatasets = statuses.map((status, idx) => ({
      label: status,
      data: trendLabels.map(date => filtered.filter(v => v.visit_date === date && v.status === status).length),
      backgroundColor: statusColors[idx]
    }));

    if (visitTrendsChart) visitTrendsChart.destroy();
    visitTrendsChart = new Chart(document.getElementById("visitTrendsChart"), {
      type: "bar",
      data: { labels: trendLabels, datasets: trendDatasets },
      options: {
        responsive: true,
        maintainAspectRatio: true,   
        aspectRatio: 2,
        plugins: { legend: { display: true, position: "bottom" } },
        scales: {
          x: { title: { display: true, text: "Date", color: "#333" } },
          y: { title: { display: true, text: "Visits", color: "#333" }, beginAtZero: true }
        }
      }
    });

    // --- Visits by Purpose ---
    const purposeCounts = {};
    filtered.forEach(v => {
      const p = v.purpose || "Unspecified";
      purposeCounts[p] = (purposeCounts[p] || 0) + 1;
    });
    const purposeColors = ["#8b1538", "#d44d5c", "#e88f9c", "#f5c3c8", "#fce2e3"];
    if (purposeChart) purposeChart.destroy();
    purposeChart = new Chart(document.getElementById("purposeChart"), {
      type: "pie",
      data: {
        labels: Object.keys(purposeCounts),
        datasets: [{ data: Object.values(purposeCounts), backgroundColor: purposeColors }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,   
        aspectRatio: 2,
        plugins: { legend: { position: "bottom" } }
      }
    });

    // --- Staff Performance ---
    const staffCounts = {};
    filtered.forEach(v => {
      const assigned = v.assigned_staff || "Unassigned";
      staffCounts[assigned] = (staffCounts[assigned] || 0) + 1;
    });

    const staffLabels = staff.map(s => `${s.first_name} ${s.last_name}`);
    const staffData = staffLabels.map(name => staffCounts[name] || 0);
    const staffColors = staffLabels.map((_, idx) => purposeColors[idx % purposeColors.length]);

    if (staffChart) staffChart.destroy();
    staffChart = new Chart(document.getElementById("staffChart"), {
      type: "bar",
      data: { labels: staffLabels, datasets: [{ label: "Visits Handled", data: staffData, backgroundColor: staffColors }] },
      options: {
        responsive: true,
        maintainAspectRatio: true,   
        aspectRatio: 2,
        plugins: { legend: { display: true, position: "bottom" } },
        scales: {
          x: { title: { display: true, text: "Staff", color: "#333" } },
          y: { title: { display: true, text: "Visits", color: "#333" }, beginAtZero: true }
        }
      }
    });
  }

  // ===== FILTERS =====
  document.getElementById("statusFilter").addEventListener("change", e => {
    state.status = e.target.value;
    renderCharts();
  });

  document.getElementById("startDate").addEventListener("change", e => {
    state.startDate = e.target.value || null;
    renderCharts();
  });

  document.getElementById("endDate").addEventListener("change", e => {
    state.endDate = e.target.value || null;
    renderCharts();
  });

  // ===== EXPORT MENU TOGGLE =====
  const exportBtn = document.querySelector(".export-btn");
  const exportMenu = document.querySelector(".export-menu");

  exportBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    exportMenu.classList.toggle("show");
    exportBtn.setAttribute("aria-expanded", exportMenu.classList.contains("show"));
  });

  exportMenu.addEventListener("click", e => e.stopPropagation());

  document.addEventListener("click", (e) => {
    if (!exportBtn.contains(e.target) && !exportMenu.contains(e.target)) {
      exportMenu.classList.remove("show");
      exportBtn.setAttribute("aria-expanded", false);
    }
  });

  // ===== EXPORTS =====
  function getFilterSummary() {
    let desc = [];
    if (state.status && state.status !== "All") desc.push(`Status: ${state.status}`);
    if (state.startDate) desc.push(`From: ${state.startDate}`);
    if (state.endDate) desc.push(`To: ${state.endDate}`);
    return desc.length ? desc.join(", ") : "No filters applied.";
  }

  document.getElementById("exportCSV").addEventListener("click", () => {
    exportMenu.classList.remove("show");
    exportBtn.setAttribute("aria-expanded", false);

    const filtered = filterVisits(visits);
    if (!filtered.length) return alert("No data to export!");

    // ===== Compute Summary =====
    const totalVisitors = new Set(filtered.map(v => v.user_id)).size;
    const totalVisits = filtered.length;
    const ongoing = filtered.filter(v => v.status === "Ongoing").length;
    const completed = filtered.filter(v => v.status === "Completed").length;
    const cancelled = filtered.filter(v => v.status === "Cancelled").length;

    // ===== CSV Header =====
    let csv = "";
    csv += "CampusPass Reports\n";
    csv += getFilterSummary() + "\n\n";

    // ===== Summary Section =====
    csv += "Summary\n";
    csv += "Total Visitors,Total Visits,Ongoing,Completed,Cancelled\n";
    csv += `${totalVisitors},${totalVisits},${ongoing},${completed},${cancelled}\n\n`;

    // ===== Detailed Visit Records =====
    csv += "Visit Records\n";
    csv += "Visit ID,Purpose,Department,Status,Visit Date\n";
    filtered.forEach(v => {
      csv += `"${v.visit_id}","${v.purpose || "-"}","${v.department || "-"}","${v.status || "-"}","${v.visit_date || "-"}"\n`;
    });

    // ===== Download File =====
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "reports.csv";
    link.click();
  });


  document.getElementById("exportPDF").addEventListener("click", async () => {
    exportMenu.classList.remove("show");
    exportBtn.setAttribute("aria-expanded", false);

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "mm", "a4");
    const filtered = filterVisits(visits);

    if (!filtered.length) return alert("No data to export!");

    // ===== Title and Filter Summary =====
    doc.setFontSize(14);
    doc.text("CampusPass Reports", 14, 12);
    doc.setFontSize(11);
    doc.text(getFilterSummary(), 14, 20);

    // ===== Add Summary Table =====
    const totalVisitors = new Set(filtered.map(v => v.user_id)).size;
    const totalVisits = filtered.length;
    const ongoing = filtered.filter(v => v.status === "Ongoing").length;
    const completed = filtered.filter(v => v.status === "Completed").length;
    const cancelled = filtered.filter(v => v.status === "Cancelled").length;

    doc.autoTable({
      startY: 28,
      head: [["Total Visitors", "Total Visits", "Ongoing", "Completed", "Cancelled"]],
      body: [[totalVisitors, totalVisits, ongoing, completed, cancelled]],
      styles: { halign: "center" },
    });

    let yPos = doc.lastAutoTable.finalY + 10;

    // ===== Capture and Embed Charts =====
    async function addChartToPDF(chart, title) {
      if (!chart) return;
      const canvas = chart.canvas;
      const imgData = canvas.toDataURL("image/png", 1.0);
      const imgWidth = 180;
      const imgHeight = (canvas.height / canvas.width) * imgWidth;

      if (yPos + imgHeight > 280) {
        doc.addPage();
        yPos = 20;
      }

      doc.setFontSize(12);
      doc.text(title, 14, yPos);
      yPos += 6;
      doc.addImage(imgData, "PNG", 14, yPos, imgWidth, imgHeight);
      yPos += imgHeight + 10;
    }

    await addChartToPDF(visitTrendsChart, "Visit Trends");
    await addChartToPDF(purposeChart, "Visits by Purpose");
    await addChartToPDF(staffChart, "Staff Performance");

    // ===== Add Visit Records Table =====
    const rows = filtered.map(v => [
      v.visit_id,
      v.purpose || "-",
      v.department || "-",
      v.status || "-",
      v.visit_date || "-"
    ]);

    if (yPos + 60 > 280) {
      doc.addPage();
      yPos = 20;
    }

    doc.autoTable({
      head: [["ID", "Purpose", "Department", "Status", "Date"]],
      body: rows,
      startY: yPos,
      styles: { fontSize: 9 },
    });

    doc.save("reports.pdf");
  });

  renderCharts();

  window.addEventListener("resize", () => {
    clearTimeout(window._resizeTimeout);
    window._resizeTimeout = setTimeout(() => {
      renderCharts(); // rebuild charts with new container dimensions
    }, 300);
  });

})();
