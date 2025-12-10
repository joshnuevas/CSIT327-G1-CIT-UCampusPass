(() => {
  const notifDropdown = document.getElementById("notifDropdown");
  const notifBadge = document.querySelector(".notification-badge");
  const dashboardContainer = document.getElementById("notificationsContainer");
  const notifBtn = document.getElementById("notifBtn"); // We need the button element
  const csrftoken = document.querySelector('meta[name="csrf-token"]')?.content;

  let pollInterval = null;
  const POLL_DELAY = 10000; 

  // Store count globally to re-apply without fetching
  let currentNotificationCount = 0;

  function formatTime(dateString) {
    return dateString || "N/A";
  }

  function getIconClass(type, title) {
    if (type === 'personal_alert') return 'fas fa-user-shield';
    if (type === 'system_alert') return 'fas fa-server';
    if (title && title.includes('Staff')) return 'fas fa-user-tie';
    if (title && title.includes('Visitor')) return 'fas fa-users';
    return 'fas fa-bell';
  }

  // === Helper: Force Badge Visibility ===
  function updateBadgeUI(count) {
    if (!notifBadge) return;
    
    currentNotificationCount = count; // Update global state

    // 1. Clear text (Dot mode)
    notifBadge.textContent = "";

    if (count > 0) {
        // 2. FORCE visibility with !important to override framework hiding behavior
        notifBadge.style.setProperty("display", "inline-block", "important");
        
        // 3. Dot Styling
        notifBadge.style.width = "10px";
        notifBadge.style.height = "10px";
        notifBadge.style.padding = "0";
        notifBadge.style.borderRadius = "50%";
        notifBadge.style.backgroundColor = "#8b1538";
        notifBadge.style.border = "1px solid #fff";
        notifBadge.style.position = "absolute"; // Ensure it stays positioned correctly
        notifBadge.style.top = "0";
        notifBadge.style.right = "0";
    } else {
        notifBadge.style.display = "none";
    }
  }

  async function fetchRecentActivities() {
    try {
      const response = await fetch("/api/admin-recent-activities/");
      if (!response.ok) return;
      const data = await response.json();
      const activities = data.activities || [];

      const recentActivitiesCard = document.querySelector('.left-column .card:first-child .card-content');
      
      if (recentActivitiesCard) {
        recentActivitiesCard.innerHTML = '';
        if (activities.length === 0) {
          recentActivitiesCard.innerHTML = `
            <div class="empty-state">
              <div class="empty-icon"><i class="far fa-clipboard"></i></div>
              <h3>No Recent Activities</h3>
              <p>Activity logs will appear here as actions are performed.</p>
            </div>`;
        } else {
          activities.forEach(activity => {
            const item = document.createElement("div");
            item.classList.add("activity-item");
            item.innerHTML = `
              <div class="activity-content">
                <h4>${activity.action_type}</h4>
                <p>${activity.description}</p>
                <small>
                  <i class="far fa-user"></i> ${activity.actor} &bull; ${formatTime(activity.time)}
                </small>
              </div>`;
            recentActivitiesCard.appendChild(item);
          });
        }
      }
    } catch (err) {
      console.error("Error fetching activities:", err);
    }
  }

  async function fetchNotifications() {
    try {
      const response = await fetch("/api/admin-notifications/");
      if (!response.ok) return;
      const data = await response.json();
      const notifications = data.notifications || [];

      // === UPDATE BADGE ===
      updateBadgeUI(notifications.length);

      // === Update Dropdown ===
      if (notifDropdown) {
        notifDropdown.innerHTML = "";
        const headerDiv = document.createElement("div");
        headerDiv.classList.add("dropdown-header");
        headerDiv.innerHTML = `Notifications <a href="#" id="dropdownClearBtn" class="small-clear-btn" style="float:right; font-size:0.8rem; color:#8b1538; text-decoration:none;">Clear All</a>`;
        notifDropdown.appendChild(headerDiv);

        const clearBtn = headerDiv.querySelector("#dropdownClearBtn");
        if(clearBtn) clearBtn.addEventListener("click", (e) => { e.preventDefault(); clearAllNotifications(); });

        if (notifications.length === 0) {
          notifDropdown.innerHTML += '<div class="dropdown-empty">No new notifications</div>';
        } else {
          notifications.forEach(notif => {
            const item = document.createElement("div");
            item.classList.add("dropdown-item");
            if(!notif.is_read) item.style.backgroundColor = "#fff5f7"; 

            const iconClass = getIconClass(notif.type, notif.title);

            item.innerHTML = `
              <div class="activity-icon"><i class="${iconClass}"></i></div>
              <div class="activity-content" style="flex: 1;">
                <h4 style="margin-bottom:2px;">${notif.title}</h4>
                <p style="margin:0;">${notif.message}</p>
                <small>${formatTime(notif.time)}</small>
              </div>
              <button class="btn-delete" data-id="${notif.id}" style="border:none; background:none; cursor:pointer; color:#888;">&times;</button>
            `;
            notifDropdown.appendChild(item);

            item.querySelector(".btn-delete").addEventListener("click", (e) => {
                e.stopPropagation();
                deleteNotification(notif.id, item);
            });
          });
        }
      }

      // === Update Dashboard Container ===
      if (dashboardContainer) {
        dashboardContainer.innerHTML = "";
        notifications.forEach((notif) => {
          const item = document.createElement("div");
          item.classList.add("notification-item");
          const iconClass = getIconClass(notif.type, notif.title);
          
          item.innerHTML = `
            <div class="activity-icon"><i class="${iconClass}"></i></div>
            <div class="activity-content">
              <h4>${notif.title}</h4>
              <p>${notif.message}</p>
              <small>${formatTime(notif.time)}</small>
            </div>
            <button class="btn-delete" data-id="${notif.id}">✕</button>
          `;
          dashboardContainer.appendChild(item);
          item.querySelector(".btn-delete").addEventListener("click", () => {
             deleteNotification(notif.id, item);
          });
        });
      }

    } catch (err) {
      console.error("Error fetching notifications:", err);
    }
  }

  async function deleteNotification(notifId, element) {
    try {
      const res = await fetch("/api/admin-notifications/delete/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({ notif_id: notifId }),
      });
      const data = await res.json();
      if (data.success && element) {
        element.remove();
        fetchNotifications(); 
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function clearAllNotifications() {
    try {
      const res = await fetch("/api/admin-notifications/clear/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({}) 
      });
      const data = await res.json();
      if (data.success) {
        fetchNotifications(); 
      }
    } catch (err) {
      console.error(err);
    }
  }

  function init() {
    fetchNotifications();
    fetchRecentActivities();
    startPolling();
    
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) stopPolling();
      else { fetchNotifications(); startPolling(); }
    });

    const clearDashboardBtn = document.getElementById("clearAllBtn");
    if (clearDashboardBtn) {
        clearDashboardBtn.addEventListener("click", (e) => {
            e.preventDefault();
            clearAllNotifications();
        });
    }

    // === CRITICAL FIX: Persist badge on click ===
    if (notifBtn) {
        // 1. When clicked, wait a split second for the framework to try and hide it, 
        // then force it back if count > 0
        notifBtn.addEventListener("click", (e) => {
            setTimeout(() => {
                updateBadgeUI(currentNotificationCount);
            }, 50); // 50ms delay to run after Bootstrap/CSS changes
        });

        // 2. Also listen for the close event if using Bootstrap
        // (This part uses jQuery syntax often found with Bootstrap, safe to keep if you use jQuery)
        if (typeof $ !== 'undefined') {
            $(notifBtn).parent().on('hidden.bs.dropdown', function () {
                updateBadgeUI(currentNotificationCount);
            });
        }
    }
  }

  function startPolling() {
    if (!pollInterval) {
        pollInterval = setInterval(() => {
            fetchNotifications();
            fetchRecentActivities();
        }, POLL_DELAY);
    }
  }

  function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
  }

  init();
})();