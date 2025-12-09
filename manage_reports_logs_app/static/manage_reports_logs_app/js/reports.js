/* manage_reports_logs_app/js/reports.js */

document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // 1. DATA & STATE INITIALIZATION
    // ============================================
    
    // Safely parse the JSON data. If empty, default to empty array.
    let rawVisits = [];
    try {
        const jsonContent = document.getElementById("visits-data").textContent;
        rawVisits = JSON.parse(jsonContent || "[]");
        console.log("Visits Loaded:", rawVisits.length, "records"); // Debug log
    } catch (e) {
        console.error("Error parsing visit data:", e);
    }
    
    // Global State
    const state = {
        status: "All",
        startDate: null,
        endDate: null,
        trendScale: 'day' // 'day', 'week', 'month'
    };

    // Chart Instances Container
    let charts = {
        trend: null,
        hourly: null,
        dept: null,
        purpose: null
    };

    // Brand Colors
    const COLORS = {
        maroon: '#8b1538',
        maroonFade: 'rgba(139, 21, 56, 0.1)',
        gold: '#d4af37',
        blue: '#2c3e50',
        grey: '#cbd5e1'
    };

    // ============================================
    // 2. HELPER FUNCTIONS
    // ============================================

    // Helper: Get Local Date String (YYYY-MM-DD)
    // Fixes timezone issues where "Today" becomes "Yesterday" in UTC
    function getLocalDateStr(dateObj) {
        const offset = dateObj.getTimezoneOffset() * 60000;
        return new Date(dateObj.getTime() - offset).toISOString().split('T')[0];
    }

    // Helper: Get ISO Week Number (W01 - W53)
    function getWeekLabel(dateObj) {
        const d = new Date(Date.UTC(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate()));
        d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay()||7));
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
        const weekNo = Math.ceil(( ( (d - yearStart) / 86400000) + 1)/7);
        return `W${weekNo} ${d.getUTCFullYear()}`;
    }

    // Helper: Group Data Logic
    function aggregateData(data, scale) {
        const grouped = {};
        data.forEach(v => {
            if (!v.visit_date) return;
            const date = new Date(v.visit_date);
            let key;

            if (scale === 'day') {
                key = v.visit_date; // YYYY-MM-DD
            } else if (scale === 'week') {
                key = getWeekLabel(date); // W42 2023
            } else if (scale === 'month') {
                key = date.toLocaleString('default', { month: 'short', year: 'numeric' }); // Oct 2023
            }
            grouped[key] = (grouped[key] || 0) + 1;
        });

        // Ensure chronological sort for Days, basic sort for others
        const sortedKeys = Object.keys(grouped).sort();
        return {
            labels: sortedKeys,
            values: sortedKeys.map(k => grouped[k])
        };
    }

    // ============================================
    // 3. MAIN UPDATE LOGIC
    // ============================================

    function getFilteredData() {
        return rawVisits.filter(v => {
            const vDate = new Date(v.visit_date);

            // Parse Filter Dates (Ensure we compare Day vs Day)
            const sDate = state.startDate ? new Date(state.startDate) : null;
            const eDate = state.endDate ? new Date(state.endDate) : null;

            // Include upcoming visits regardless of date filter
            if (v.status === 'Upcoming') {
                return state.status === "All" || v.status === state.status;
            }

            if (sDate && vDate < sDate) return false;
            if (eDate && vDate > eDate) return false;
            if (state.status !== "All" && v.status !== state.status) return false;

            return true;
        });
    }

    function updateDashboard() {
        const data = getFilteredData();

        // --- A. KPI Updates ---
        const totalElem = document.getElementById('totalVisits');
        if (totalElem) totalElem.textContent = data.length.toLocaleString();

        const ongoingElem = document.getElementById('ongoingVisits');
        if (ongoingElem) ongoingElem.textContent = data.filter(v => v.status === 'Active').length;
        
        // Busiest Day Logic
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const dayCounts = {};
        data.forEach(v => {
            if(v.visit_date) {
                // Ensure correct day parsing
                const d = new Date(v.visit_date);
                // Fix for potential timezone offset reading wrong day
                const dayName = days[d.getUTCDay()]; 
                dayCounts[dayName] = (dayCounts[dayName] || 0) + 1;
            }
        });
        const peakDay = Object.keys(dayCounts).reduce((a, b) => dayCounts[a] > dayCounts[b] ? a : b, "-");
        const peakElem = document.getElementById('peakDay');
        if (peakElem) peakElem.textContent = peakDay;

        // --- B. Chart Rendering ---
        renderTrendChart(data);
        renderHourlyChart(data);
        renderDeptChart(data);
        renderPurposeList(data);
    }

    // ============================================
    // 4. CHART CONFIGURATIONS
    // ============================================

    function renderTrendChart(data) {
        const aggr = aggregateData(data, state.trendScale);
        const ctxElem = document.getElementById('visitTrendsChart');
        if (!ctxElem) return;

        const ctx = ctxElem.getContext('2d');
        
        // Gradient Fill
        const grad = ctx.createLinearGradient(0, 0, 0, 400);
        grad.addColorStop(0, COLORS.maroonFade);
        grad.addColorStop(1, 'rgba(255,255,255,0)');

        if (charts.trend) charts.trend.destroy();
        charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: aggr.labels,
                datasets: [{
                    label: 'Visits',
                    data: aggr.values,
                    borderColor: COLORS.maroon,
                    backgroundColor: grad,
                    fill: true,
                    tension: 0.3,
                    pointRadius: state.trendScale === 'day' ? 3 : 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, border: { dash: [5, 5] } }
                }
            }
        });
    }

    function renderHourlyChart(data) {
        // Labels for 7am to 6pm
        const labels = ["7am","8am","9am","10am","11am","12pm","1pm","2pm","3pm","4pm","5pm","6pm"];
        const hours = Array(12).fill(0); 

        data.forEach(v => {
            let h = null;
            
            // Priority 1: Check-in Time (Format "HH:MM:SS")
            if (v.check_in_time) {
                h = parseInt(v.check_in_time.split(':')[0]); 
            } 
            // Priority 2: Created At (Format ISO)
            else if (v.created_at) {
                h = new Date(v.created_at).getHours();
            }

            // If we found a valid hour, map it
            if (h !== null) {
                if (h >= 7 && h <= 18) {
                    hours[h - 7]++;
                }
            }
        });

        const ctxElem = document.getElementById('hourlyChart');
        if (!ctxElem) return;

        if (charts.hourly) charts.hourly.destroy();
        charts.hourly = new Chart(ctxElem, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Avg Visits',
                    data: hours,
                    backgroundColor: COLORS.blue,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { display: false }, x: { grid: { display: false } } }
            }
        });
    }

    function renderDeptChart(data) {
        const counts = {};
        data.forEach(v => { counts[v.department || 'General'] = (counts[v.department || 'General'] || 0) + 1; });
        const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0, 5);

        const ctxElem = document.getElementById('deptChart');
        if (!ctxElem) return;

        if (charts.dept) charts.dept.destroy();
        charts.dept = new Chart(ctxElem, {
            type: 'bar',
            data: {
                labels: sorted.map(s => s[0]),
                datasets: [{
                    label: 'Visits',
                    data: sorted.map(s => s[1]),
                    backgroundColor: COLORS.gold,
                    borderRadius: 4,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { display: false } }
            }
        });
    }

    // NEW: Render Leaderboard instead of Chart
    function renderPurposeList(data) {
        const container = document.getElementById('purposeList');
        if (!container) return;

        // 1. Process Data
        const counts = {};
        data.forEach(v => { 
            // Clean up empty purposes
            const p = v.purpose ? v.purpose.trim() : 'Unspecified';
            counts[p] = (counts[p] || 0) + 1; 
        });

        // 2. Sort High to Low
        const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]);
        
        // 3. Calculate Max for relative bar width
        const maxVal = sorted.length > 0 ? sorted[0][1] : 0;
        const totalVisits = data.length;

        // 4. Generate HTML
        container.innerHTML = ''; // Clear previous
        
        if (sorted.length === 0) {
            container.innerHTML = '<p class="text-muted" style="text-align:center; padding:20px;">No data available</p>';
            return;
        }

        sorted.forEach(([label, count], index) => {
            const widthPct = maxVal > 0 ? (count / maxVal) * 100 : 0;
            const sharePct = totalVisits > 0 ? Math.round((count / totalVisits) * 100) : 0;

            const item = document.createElement('div');
            item.className = 'leaderboard-item';
            // Stagger animation delay
            item.style.animationDelay = `${index * 0.05}s`;

            item.innerHTML = `
                <div class="lb-info" title="${label}">${label}</div>
                <div class="lb-bar-container">
                    <div class="lb-bar-fill" style="width: ${widthPct}%"></div>
                </div>
                <div class="lb-count">${count}</div>
                <div class="lb-percent">${sharePct}%</div>
            `;
            container.appendChild(item);
        });
    }

    

    // ============================================
    // 5. EVENT LISTENERS & EXPORT
    // ============================================

    // Toggle Dropdown - Match logs export dropdown pattern
    const exportToggle = document.getElementById('exportToggle');
    const exportDropdown = document.getElementById('exportDropdown');

    if (exportToggle && exportDropdown) {
        // Move export dropdown to body to prevent clipping by containers
        if (!exportDropdown.__movedToBody) {
            document.body.appendChild(exportDropdown);
            exportDropdown.style.position = 'fixed';
            exportDropdown.style.zIndex = 30000;
            exportDropdown.__movedToBody = true;
        }

        exportToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = exportDropdown.classList.contains('active');

            // Close others
            document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));

            if (!isActive) {
                exportDropdown.classList.add('active');

                // Position as fixed element using viewport coordinates
                const rect = exportToggle.getBoundingClientRect();

                // Temporarily move offscreen to measure size
                exportDropdown.style.left = '-9999px';
                exportDropdown.style.top = '-9999px';
                const dropRect = exportDropdown.getBoundingClientRect();
                const viewportHeight = window.innerHeight;

                // Default: below button, align right
                let top = rect.bottom + 5;
                let left = rect.right - dropRect.width;

                // If not enough space below, place above
                if (viewportHeight - rect.bottom < dropRect.height + 10) {
                    top = rect.top - dropRect.height - 5;
                }

                // Clamp horizontally
                left = Math.max(6, Math.min(left, window.innerWidth - dropRect.width - 6));

                exportDropdown.style.top = `${Math.round(top)}px`;
                exportDropdown.style.left = `${Math.round(left)}px`;
            }
        });
    }

    // Preset Buttons Logic
    document.querySelectorAll('.btn-preset').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // UI
            document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');

            // Logic
            const range = e.target.dataset.range;
            const end = new Date();
            const start = new Date();

            if (range === '7days') start.setDate(end.getDate() - 7);
            else if (range === '30days') start.setDate(end.getDate() - 30);
            else if (range === 'month') start.setDate(1);

            // Use Local Date Strings to avoid timezone issues
            const startStr = getLocalDateStr(start);
            const endStr = getLocalDateStr(end);

            const startInput = document.getElementById('startDate');
            const endInput = document.getElementById('endDate');

            if(startInput) startInput.value = startStr;
            if(endInput) endInput.value = endStr;
            
            state.startDate = startStr;
            state.endDate = endStr;
            updateDashboard();
        });
    });

    // Trend Scale Toggles
    document.querySelectorAll('.btn-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.btn-toggle').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            state.trendScale = e.target.dataset.scale;
            updateDashboard();
        });
    });

    // Manual Inputs
    ['startDate', 'endDate'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', (e) => {
                if(id !== 'statusFilter') document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));
                if(id === 'startDate') state.startDate = e.target.value;
                if(id === 'endDate') state.endDate = e.target.value;
                if(id === 'statusFilter') state.status = e.target.value;
                updateDashboard();
            });
        }
    });

    // Custom Status Dropdown (replaces native select)
    const statusToggle = document.getElementById('statusFilterToggle');
    const statusDropdown = document.getElementById('statusFilterDropdown');
    const statusText = document.getElementById('statusFilterText');

    if (statusToggle && statusDropdown) {
        statusToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = statusDropdown.classList.contains('active');
            // Close others
            document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));
            if (!isActive) {
                statusDropdown.classList.add('active');
                // position below toggle (absolute inside .action-menu)
                statusDropdown.style.top = (statusToggle.offsetHeight + 6) + 'px';
                statusDropdown.style.left = '0px';
            }
        });

        statusDropdown.querySelectorAll('.action-item').forEach(item => {
            item.addEventListener('click', () => {
                const value = item.dataset.value;
                state.status = value;
                statusText.textContent = item.textContent;
                updateDashboard();
                statusDropdown.classList.remove('active');
            });
        });
    }

    // Close custom dropdowns on outside click
    document.addEventListener('click', () => {
        document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));
    });

    // Close dropdowns on scroll and resize
    window.addEventListener('scroll', () => {
        document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));
    }, true);
    window.addEventListener('resize', () => {
        document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));
    });

    // Export PDF
    const pdfBtn = document.getElementById('exportPDF');
    if (pdfBtn) {
        pdfBtn.addEventListener('click', () => {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF('p', 'mm', 'a4');
            const data = getFilteredData();

            // Header
            doc.setFillColor(139, 21, 56);
            doc.rect(0, 0, 210, 20, 'F');
            doc.setTextColor(255, 255, 255);
            doc.setFontSize(14);
            doc.text("CIT-U Campus Pass - Analytics", 14, 13);

            // Summary text
            doc.setTextColor(50);
            doc.setFontSize(10);
            doc.text(`Generated: ${new Date().toLocaleDateString()} | Records: ${data.length}`, 14, 30);

            let yPos = 40;

            // Add Data Table
            if (data.length > 0) {
                const tableData = data.map(v => [
                    v.visit_date || '-',
                    v.visitor_name || 'Guest',
                    v.department || '-',
                    v.purpose || '-',
                    v.status,
                    v.check_in_time || '-',
                    v.check_out_time || '-'
                ]);

                doc.autoTable({
                    head: [['Date', 'Visitor', 'Department', 'Purpose', 'Status', 'Check-In', 'Check-Out']],
                    body: tableData,
                    startY: yPos,
                    styles: { fontSize: 8 },
                    headStyles: { fillColor: [139, 21, 56] },
                    margin: { left: 14, right: 14 }
                });

                yPos = doc.lastAutoTable.finalY + 10;
            }

            // Capture Charts
            const addChart = (id, title) => {
                if (yPos > 220) { doc.addPage(); yPos = 20; }
                const canvas = document.getElementById(id);
                if (!canvas) return;
                const img = canvas.toDataURL("image/png");
                doc.setFontSize(11);
                doc.text(title, 14, yPos);
                doc.addImage(img, 'PNG', 14, yPos + 5, 180, 80);
                yPos += 95;
            };

            addChart('visitTrendsChart', 'Traffic Trends');
            addChart('hourlyChart', 'Peak Hourly Traffic');
            addChart('deptChart', 'Department Stats');

            doc.save('analytics_report.pdf');
        });
    }
    
    // CSV Export
    const csvBtn = document.getElementById('exportCSV');
    if (csvBtn) {
        csvBtn.addEventListener('click', () => {
            const data = getFilteredData();
            let csv = "Date,Visitor,Department,Purpose,Status,Check-In Time,Check-Out Time\n";
            data.forEach(v => {
                csv += `${v.visit_date},"${v.visitor_name||'Guest'}","${v.department||'-'}","${v.purpose||'-'}",${v.status},"${v.check_in_time||'-'}","${v.check_out_time||'-'}"\n`;
            });
            const blob = new Blob([csv], {type: 'text/csv'});
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = 'analytics_report.csv';
            link.click();
        });
    }

    // Initialize: Trigger "Last 30 Days" by default so charts aren't empty
    // We check if the button exists first
    const defaultBtn = document.querySelector('.btn-preset[data-range="30days"]');
    if (defaultBtn) {
        defaultBtn.click();
    } else {
        // Fallback initialization if button missing
        updateDashboard();
    }
});