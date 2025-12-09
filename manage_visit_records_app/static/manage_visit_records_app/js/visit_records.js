document.addEventListener('DOMContentLoaded', () => {
    // === 1. DATA INITIALIZATION ===
    let visits = [];
    try {
        const el = document.getElementById('visits-data');
        visits = JSON.parse(el.textContent || '[]');
    } catch (e) {
        console.error('Failed to parse visits data', e);
    }

    // Sort by ID Descending (Newest first)
    visits.sort((a, b) => (b.visit_id || 0) - (a.visit_id || 0));

    // === 2. STATE MANAGEMENT ===
    const state = {
        search: '',
        status: 'All',
        registerDate: null,
        page: 1,
        perPage: 10 // Show 10 for better spacing
    };

    const tbody = document.getElementById('visitsTbody');
    const paginationContainer = document.getElementById('pagination');

    // === 3. FORMATTERS ===
    function formatDate(dStr) {
        if (!dStr) return '-';
        const d = new Date(dStr);
        if (isNaN(d)) return dStr;
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: '2-digit'
        });
    }

    function formatTime(tStr) {
        if (!tStr) return '-';
        const timePart = tStr.slice(0, 5); // HH:MM
        return timePart; // Return as-is (24-hour format)
    }

    // === 4. FILTER LOGIC ===
    function matchesFilters(v) {
        // Search
        if (state.search) {
            const query = state.search.toLowerCase();
            const text = `
                ${v.user_email || ''} 
                ${v.code || ''} 
                ${v.purpose || ''} 
                ${v.department || ''} 
                ${v.visitor_name || ''}
            `.toLowerCase();
            if (!text.includes(query)) return false;
        }

        // Status
        if (state.status !== 'All') {
            const statusValue = v.status || '';
            const filterValue = state.status;
            // Filter values match database values directly
            if (statusValue !== filterValue) {
                return false;
            }
        }

        // Date
        if (state.registerDate) {
            // Compare YYYY-MM-DD
            const visitDate = new Date(v.visit_date).toISOString().split('T')[0];
            if (visitDate !== state.registerDate) return false;
        }

        return true;
    }

    function getFilteredData() {
        return visits.filter(matchesFilters);
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
            const msg = filtered.length === 0 && state.search ? 'No matches found.' : 'No visit records found.';
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 40px; color: #64748b;">${msg}</td></tr>`;
            renderPagination(0);
            return;
        }

        paginated.forEach(v => {
            const tr = document.createElement('tr');
            let statusLower = (v.status || 'Upcoming').toLowerCase();

            // Visitor Name/Email + Code in one column
            const visitorName = v.visitor_name || v.user_email || 'Unknown';

            // Status display matches database values
            let displayStatus = v.status || 'Upcoming';
            // Set CSS class based on status
            if (displayStatus === 'Active') {
                statusLower = 'ongoing'; // Green color
            } else if (displayStatus === 'Expired') {
                statusLower = 'cancelled'; // Gray color
            } else if (displayStatus === 'Upcoming') {
                statusLower = 'upcoming'; // Orange color
            } else if (displayStatus === 'Completed') {
                statusLower = 'completed'; // Blue color
            }

            tr.innerHTML = `
                <td>
                    <span class="col-primary">${visitorName}</span>
                    <span class="col-sub">${v.code || '-'}</span>
                </td>
                <td>${v.purpose || '-'}</td>
                <td>${v.department || '-'}</td>
                <td>${formatDate(v.visit_date)}</td>
                <td>${formatTime(v.start_time)}</td>
                <td>${formatTime(v.end_time)}</td>
                <td style="text-align: center;">
                    <span class="status-badge status-${statusLower}">${displayStatus}</span>
                </td>
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

    // Status Filter Dropdown Logic
    const statusToggle = document.getElementById('statusFilterToggle');
    const statusDropdown = document.getElementById('statusFilterDropdown');
    const statusText = document.getElementById('statusFilterText');

    if (statusToggle && statusDropdown) {
        // Ensure dropdown is appended to body to avoid being clipped by overflowed containers
        if (!statusDropdown.__movedToBody) {
            document.body.appendChild(statusDropdown);
            statusDropdown.style.position = 'fixed';
            statusDropdown.style.zIndex = 30000;
            statusDropdown.__movedToBody = true;
        }

        statusToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = statusDropdown.classList.contains('active');

            // Close others
            document.querySelectorAll('.action-dropdown').forEach(d => d.classList.remove('active'));

            if (!isActive) {
                statusDropdown.classList.add('active');

                // Position as a fixed element using viewport coordinates
                const rect = statusToggle.getBoundingClientRect();

                // Temporarily move offscreen to measure size accurately
                statusDropdown.style.left = '-9999px';
                statusDropdown.style.top = '-9999px';
                const dropRect = statusDropdown.getBoundingClientRect();
                const viewportHeight = window.innerHeight;

                // Default: place below button, align right edge of dropdown with button's right edge
                let top = rect.bottom + 5;
                let left = rect.right - dropRect.width;

                // If not enough space below, place above
                if (viewportHeight - rect.bottom < dropRect.height + 10) {
                    top = rect.top - dropRect.height - 5;
                }

                // Clamp within viewport horizontally
                left = Math.max(6, Math.min(left, window.innerWidth - dropRect.width - 6));

                statusDropdown.style.top = `${Math.round(top)}px`;
                statusDropdown.style.left = `${Math.round(left)}px`;
            }
        });

        // Handle item clicks
        statusDropdown.querySelectorAll('.action-item').forEach(item => {
            item.addEventListener('click', () => {
                const value = item.dataset.value;
                state.status = value;
                statusText.textContent = item.textContent;
                state.page = 1;
                render();
                statusDropdown.classList.remove('active');
            });
        });
    }

    document.getElementById('registerDateFilter').addEventListener('change', e => {
        state.registerDate = e.target.value || null;
        state.page = 1;
        render();
    });

    // Dropdown Logic (Smart Positioning)
    const toggle = document.getElementById('exportToggle');
    const dropdown = document.getElementById('exportDropdown');

    if (toggle && dropdown) {
        // Ensure export dropdown is appended to body to avoid clipping
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

                const rect = toggle.getBoundingClientRect();

                // Temporarily offscreen to measure
                dropdown.style.left = '-9999px';
                dropdown.style.top = '-9999px';
                const dropRect = dropdown.getBoundingClientRect();
                const viewportHeight = window.innerHeight;

                let top = rect.bottom + 5;
                let left = rect.right - dropRect.width;
                if (viewportHeight - rect.bottom < dropRect.height + 10) {
                    top = rect.top - dropRect.height - 5;
                }
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
        if (state.status !== 'All') parts.push(`Status: ${state.status}`);
        if (state.registerDate) parts.push(`Date: ${state.registerDate}`);
        return parts.length ? `Filters: ${parts.join(', ')}` : 'All Records';
    }

    document.getElementById('exportCSV').addEventListener('click', async () => {
        try {
            // Fetch data from server with current filters
            const params = new URLSearchParams({
                search: state.search,
                status: state.status,
                register_date: state.registerDate || ''
            });

            const response = await fetch(`${window.EXPORT_URL}?${params}`);
            if (!response.ok) throw new Error('Failed to fetch data');

            const data = await response.json();
            const filtered = data.visits;

            if (!filtered.length) return alert('No data to export.');

            let csv = `"${getFilterText()}"\n\nVisitor,Code,Purpose,Department,Date,Start Time,End Time,Status\n`;

            filtered.forEach(v => {
                // Status display matches database values
                let displayStatus = v.status || 'Upcoming';

                const row = [
                    v.visitor_name || v.user_email || '',
                    v.code || '',
                    v.purpose || '',
                    v.department || '',
                    formatDate(v.visit_date),
                    formatTime(v.start_time),
                    formatTime(v.end_time),
                    displayStatus
                ].map(f => `"${String(f).replace(/"/g, '""')}"`).join(',');
                csv += row + '\n';
            });

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `visit_records_${Date.now()}.csv`;
            a.click();
        } catch (error) {
            console.error('Export error:', error);
            alert('Failed to export data. Please try again.');
        }
    });

    document.getElementById('exportPDF').addEventListener('click', async () => {
        try {
            // Fetch data from server with current filters
            const params = new URLSearchParams({
                search: state.search,
                status: state.status,
                register_date: state.registerDate || ''
            });

            const response = await fetch(`${window.EXPORT_URL}?${params}`);
            if (!response.ok) throw new Error('Failed to fetch data');

            const data = await response.json();
            const filtered = data.visits;

            if (!filtered.length) return alert('No data to export.');

            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();

            doc.setFontSize(16);
            doc.setTextColor(139, 21, 56);
            doc.text("Visit Records Report", 14, 15);

            doc.setFontSize(10);
            doc.setTextColor(100);
            doc.text(getFilterText(), 14, 22);

            const headers = [['Visitor', 'Code', 'Purpose', 'Dept', 'Date', 'Start Time', 'End Time', 'Status']];
            const tableData = filtered.map(v => {
                // Status display matches database values
                let displayStatus = v.status || 'Upcoming';

                return [
                    v.visitor_name || v.user_email || '',
                    v.code || '',
                    v.purpose || '',
                    v.department || '',
                    formatDate(v.visit_date),
                    formatTime(v.start_time),
                    formatTime(v.end_time),
                    displayStatus
                ];
            });

            doc.autoTable({
                head: headers,
                body: tableData,
                startY: 28,
                theme: 'grid',
                headStyles: { fillColor: [139, 21, 56] },
                styles: { fontSize: 8 }
            });

            doc.save(`visit_records_${Date.now()}.pdf`);
        } catch (error) {
            console.error('Export error:', error);
            alert('Failed to export data. Please try again.');
        }
    });

    // Init
    render();
});