document.addEventListener('DOMContentLoaded', () => {
    // === 1. DATA INITIALIZATION ===
    let logs = [];
    try {
        const el = document.getElementById('logs-data');
        logs = JSON.parse(el.textContent || '[]');
    } catch (e) {
        console.error('Failed to parse logs data', e);
    }

    // === 2. STATE MANAGEMENT ===
    const state = {
        search: '',
        role: 'All',
        createdDate: null,
        page: 1,
        perPage: 10 // Match visit records
    };

    const tbody = document.getElementById('logsTbody');
    const paginationContainer = document.getElementById('pagination');

    // === 3. FORMATTERS ===
    function formatToPhilippineTime(dateString) {
        if (!dateString || dateString === 'N/A') return "N/A";

        let cleanDate = dateString.trim();
        if (!cleanDate.endsWith("Z") && !cleanDate.includes("+")) cleanDate += "Z";

        const parsedDate = new Date(cleanDate);
        if (isNaN(parsedDate.getTime())) return "N/A";

        // Convert to Philippine time
        const phDate = new Date(parsedDate.toLocaleString("en-US", {timeZone: "Asia/Manila"}));

        const month = phDate.toLocaleString("en-US", {month: "short"});
        const day = phDate.toLocaleString("en-US", {day: "2-digit"});
        const year = phDate.toLocaleString("en-US", {year: "numeric"});
        const timeStr = phDate.toLocaleString("en-US", {hour: "2-digit", minute: "2-digit", hour12: true});

        return `${month} ${day}, ${year}`;
    }

    // === 4. FILTER LOGIC ===
    function matchesFilters(l) {
        // Search
        if (state.search) {
            const query = state.search.toLowerCase();
            const text = `
                ${l.actor || ''}
                ${l.actor_email || ''}
                ${l.action_type || ''}
                ${l.description || ''}
                ${l.actor_role || ''}
            `.toLowerCase();
            if (!text.includes(query)) return false;
        }

        if (state.role !== 'All' && l.actor_role !== state.role) return false;

        if (state.createdDate) {
            const logDatePH = new Date(l.created_at).toLocaleDateString("en-CA", {
                timeZone: "Asia/Manila",
            });
            if (logDatePH !== state.createdDate) return false;
        }

        return true;
    }

    function getFilteredData() {
        return logs.filter(matchesFilters);
    }

    // === 5. PAGINATION UI ===
    function renderPagination(totalItems) {
        paginationContainer.innerHTML = '';
        const totalPages = Math.ceil(totalItems / state.perPage) || 1;
        const startEntry = totalItems === 0 ? 0 : (state.page - 1) * state.perPage + 1;
        const endEntry = Math.min(state.page * state.perPage, totalItems);

        // A. Left Side: Information
        const infoDiv = document.createElement('div');
        infoDiv.className = 'pagination-info';
        infoDiv.textContent = `Showing ${startEntry} - ${endEntry} of ${totalItems} entries`;

        // B. Right Side: Controls
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'pagination-controls';

        // Prev Button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.disabled = state.page === 1;
        prevBtn.onclick = () => {
            if (state.page > 1) { state.page--; render(); }
        };

        // Input Group: "Page [ 1 ] of 10"
        const inputContainer = document.createElement('div');
        inputContainer.className = 'page-input-container';

        const lblPage = document.createElement('span');
        lblPage.textContent = 'Page';

        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'page-input';
        input.value = state.page;
        input.min = 1;
        input.max = totalPages;

        // Input Logic
        input.onchange = (e) => {
            let val = parseInt(e.target.value);
            if (val >= 1 && val <= totalPages) {
                state.page = val;
                render();
            } else {
                e.target.value = state.page; // Revert if invalid
            }
        };

        const lblTotal = document.createElement('span');
        lblTotal.textContent = `of ${totalPages}`;

        inputContainer.appendChild(lblPage);
        inputContainer.appendChild(input);
        inputContainer.appendChild(lblTotal);

        // Next Button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-btn';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.disabled = state.page === totalPages;
        nextBtn.onclick = () => {
            if (state.page < totalPages) { state.page++; render(); }
        };

        controlsDiv.appendChild(prevBtn);
        controlsDiv.appendChild(inputContainer);
        controlsDiv.appendChild(nextBtn);

        paginationContainer.appendChild(infoDiv);
        paginationContainer.appendChild(controlsDiv);
    }

    // === 6. RENDER TABLE ===
    function render() {
        tbody.innerHTML = '';

        const filtered = getFilteredData();
        const start = (state.page - 1) * state.perPage;
        const end = start + state.perPage;
        const paginated = filtered.slice(start, end);

        if (paginated.length === 0) {
            const msg = filtered.length === 0 && (state.search || state.role !== 'All' || state.createdDate) ? 'No matches found.' : 'No system logs found.';
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 40px; color: #64748b;">${msg}</td></tr>`;
            renderPagination(0);
            return;
        }

        paginated.forEach(l => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <span class="col-primary">${l.actor || '-'}</span>
                    <span class="col-sub">${l.actor_email || '-'}</span>
                </td>
                <td>${l.action_type || '-'}</td>
                <td>${l.description || '-'}</td>
                <td>${l.actor_role || '-'}</td>
                <td>${formatToPhilippineTime(l.created_at)}</td>
            `;
            tbody.appendChild(tr);
        });

        renderPagination(filtered.length);
    }

    // === 7. EVENT LISTENERS & UI LOGIC ===

    // Search & Filters
    document.getElementById('searchInput').addEventListener('input', e => {
        state.search = e.target.value.trim();
        state.page = 1;
        render();
    });

    // Actor Role Filter Dropdown Logic
    const roleToggle = document.getElementById('actorRoleFilterToggle');
    const roleDropdown = document.getElementById('actorRoleFilterDropdown');
    const roleText = document.getElementById('actorRoleFilterText');

    if (roleToggle && roleDropdown) {
        // Move role dropdown to body to prevent clipping by table containers
        if (!roleDropdown.__movedToBody) {
            document.body.appendChild(roleDropdown);
            roleDropdown.style.position = 'fixed';
            roleDropdown.style.zIndex = 30000;
            roleDropdown.__movedToBody = true;
        }

        roleToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = roleDropdown.classList.contains('active');

            // Close others
            document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));

            if (!isActive) {
                roleDropdown.classList.add('active');

                // Position as fixed element using viewport coordinates
                const rect = roleToggle.getBoundingClientRect();

                // Temporarily move offscreen to measure size
                roleDropdown.style.left = '-9999px';
                roleDropdown.style.top = '-9999px';
                const dropRect = roleDropdown.getBoundingClientRect();
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

                roleDropdown.style.top = `${Math.round(top)}px`;
                roleDropdown.style.left = `${Math.round(left)}px`;
            }
        });

        // Handle item clicks
        roleDropdown.querySelectorAll('.action-item').forEach(item => {
            item.addEventListener('click', () => {
                const value = item.dataset.value;
                state.role = value;
                roleText.textContent = item.textContent;
                state.page = 1;
                render();
                roleDropdown.classList.remove('active');
            });
        });
    }

    document.getElementById('createdDateFilter').addEventListener('change', e => {
        state.createdDate = e.target.value || null;
        state.page = 1;
        render();
    });

    // Dropdown Logic (Smart Positioning)
    const toggle = document.getElementById('exportToggle');
    const dropdown = document.getElementById('exportDropdown');

    if (toggle && dropdown) {
        // Move export dropdown to body to prevent clipping by table containers
        if (!dropdown.__movedToBody) {
            document.body.appendChild(dropdown);
            dropdown.style.position = 'fixed';
            dropdown.style.zIndex = 30000;
            dropdown.__movedToBody = true;
        }

        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = dropdown.classList.contains('active');

            // Close others
            document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));

            if (!isActive) {
                dropdown.classList.add('active');

                // Position as fixed element using viewport coordinates
                const rect = toggle.getBoundingClientRect();

                // Temporarily move offscreen to measure size
                dropdown.style.left = '-9999px';
                dropdown.style.top = '-9999px';
                const dropRect = dropdown.getBoundingClientRect();
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

                dropdown.style.top = `${Math.round(top)}px`;
                dropdown.style.left = `${Math.round(left)}px`;
            }
        });
    }

    // Close dropdowns on click outside, scroll, or resize
    const closeAllDropdowns = () => {
        document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));
    };

    document.addEventListener('click', closeAllDropdowns);
    window.addEventListener('scroll', closeAllDropdowns, true);
    window.addEventListener('resize', closeAllDropdowns);

    // === 8. EXPORT FUNCTIONS ===
    function getFilterText() {
        const parts = [];
        if (state.search) parts.push(`Search: ${state.search}`);
        if (state.role !== 'All') parts.push(`Role: ${state.role}`);
        if (state.createdDate) parts.push(`Date: ${state.createdDate}`);
        return parts.length ? `Filters: ${parts.join(', ')}` : 'All Logs';
    }

    document.getElementById('exportCSV').addEventListener('click', () => {
        const filtered = logs.filter(matchesFilters);
        if (!filtered.length) return alert('No data to export.');

        let csv = `"${getFilterText()}"\n\nName,Email,Action Type,Description,Actor Role,Timestamp\n`;

        filtered.forEach(l => {
            const row = [
                l.actor || '',
                l.actor_email || '',
                l.action_type || '',
                l.description || '',
                l.actor_role || '',
                formatToPhilippineTime(l.created_at)
            ].map(f => `"${String(f).replace(/"/g, '""')}"`).join(',');
            csv += row + '\n';
        });

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `system_logs_${Date.now()}.csv`;
        a.click();
    });

    document.getElementById('exportPDF').addEventListener('click', () => {
        const filtered = logs.filter(matchesFilters);
        if (!filtered.length) return alert('No data to export.');

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();

        doc.setFontSize(16);
        doc.setTextColor(139, 21, 56);
        doc.text("System Logs Report", 14, 15);

        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(getFilterText(), 14, 22);

        const headers = [['Name', 'Email', 'Action Type', 'Description', 'Actor Role', 'Timestamp']];
        const tableData = filtered.map(l => [
            l.actor || '',
            l.actor_email || '',
            l.action_type || '',
            l.description || '',
            l.actor_role || '',
            formatToPhilippineTime(l.created_at)
        ]);

        doc.autoTable({
            head: headers,
            body: tableData,
            startY: 28,
            theme: 'grid',
            headStyles: { fillColor: [139, 21, 56] },
            styles: { fontSize: 8 }
        });

        doc.save(`system_logs_${Date.now()}.pdf`);
    });

    // Init
    render();
});
