(() => {
  const notifDropdown = document.getElementById("notifDropdown");
  const notifBadge = document.querySelector(".notification-badge");
  const dashboardContainer = document.getElementById("notificationsContainer");
  const notifBtn = document.getElementById("notifBtn");
  const csrftoken = document.querySelector('meta[name="csrf-token"]').content;

  let pollInterval = null;
  const POLL_DELAY = 30000; // 30 seconds

  // === Helper: Format time in PH timezone ===
  function formatPHTime(dateString) {
    if (!dateString) return "N/A";
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return "N/A";
    // Convert to Philippine time
    const phDate = new Date(d.toLocaleString("en-US", {timeZone: "Asia/Manila"}));
    const month = phDate.toLocaleString("en-US", {month: "short"});
    const day = phDate.toLocaleString("en-US", {day: "2-digit"});
    const year = phDate.toLocaleString("en-US", {year: "numeric"});
    return `${month} ${day}, ${year}`;
  }

  // === Fetch notifications from API ===
  async function fetchNotifications() {
    try {
      const response = await fetch("/api/admin-notifications/");
      if (!response.ok) throw new Error("Failed to fetch notifications");
      const data = await response.json();
      const notifications = data.notifications || [];

      // === Badge logic ===
      if (notifBadge) {
        notifBadge.style.display = notifications.length > 0 ? "inline-block" : "none";
      }

      // === Populate dropdown ===
      if (notifDropdown) {
        notifDropdown.innerHTML = "";
        const headerDiv = document.createElement("div");
        headerDiv.classList.add("dropdown-header");
        headerDiv.textContent = "Notifications";

        const clearAllBtn = document.createElement("a");
        clearAllBtn.textContent = "Clear All";
        clearAllBtn.href = "#";
        clearAllBtn.classList.add("small-clear-btn");
        clearAllBtn.style.cssText = "font-size: 0.8rem; color: #8b1538; float: right; text-decoration: none;";
        clearAllBtn.addEventListener("click", (e) => {
          e.preventDefault();
          clearAllNotifications();
        });

        headerDiv.appendChild(clearAllBtn);
        notifDropdown.appendChild(headerDiv);

        if (notifications.length === 0) {
          notifDropdown.innerHTML += '<div class="dropdown-empty">No new notifications</div>';
          if (notifBadge) notifBadge.style.display = "none";
        } else {
          notifications.forEach((notif, index) => {
            const item = document.createElement("div");
            item.classList.add("dropdown-item", "new-notification");
  
            let iconClass = 'fas fa-bell';
            if (notif.title.includes('Staff')) {
              iconClass = 'fas fa-user-tie';
            } else if (notif.title.includes('Visitor')) {
              iconClass = 'fas fa-users';
            }
  
            item.innerHTML = `
              <div class="activity-icon" style="margin-right: 10px;">
                <i class="${iconClass}"></i>
              </div>
              <div class="activity-content" style="flex: 1;">
                <h4 style="margin-bottom:2px;">${notif.title}</h4>
                <p style="margin:0;">${notif.message}</p>
                <small>${formatPHTime(notif.time)}</small>
              </div>
              <button class="btn-delete" data-id="${notif.id}"
                      style="position:absolute; top:8px; right:8px; background:none; border:none; color:#8b1538; font-size:13px; cursor:pointer; display:none;">
                ✕
              </button>
            `;
            notifDropdown.appendChild(item);

            // Hover behavior for delete button
            item.addEventListener("mouseenter", () => {
              item.querySelector(".btn-delete").style.display = "inline-block";
            });
            item.addEventListener("mouseleave", () => {
              item.querySelector(".btn-delete").style.display = "none";
            });

            item.querySelector(".btn-delete").addEventListener("click", () => {
              deleteNotification(notif.id, item);
            });
          });
        }
      }

      // === Populate dashboard container ===
      if (dashboardContainer) {
        dashboardContainer.innerHTML = "";
        notifications.forEach((notif) => {
          const item = document.createElement("div");
          item.classList.add("notification-item");
          item.dataset.id = notif.id;

          let iconClass = 'fas fa-bell';
          if (notif.title.includes('Staff')) {
            iconClass = 'fas fa-user-tie';
          } else if (notif.title.includes('Visitor')) {
            iconClass = 'fas fa-users';
          }

          item.innerHTML = `
            <div class="activity-icon">
              <i class="${iconClass}"></i>
            </div>
            <div class="activity-content">
              <h4>${notif.title}</h4>
              <p>${notif.message}</p>
              <small>${formatPHTime(notif.time)}</small>
            </div>
            <button class="btn-delete" data-id="${notif.id}"
                    style="background:none; border:none; color:#8b1538; font-size:14px; cursor:pointer; position:absolute; top:8px; right:8px; display:none;">✕</button>
          `;
          dashboardContainer.appendChild(item);

          item.addEventListener("mouseenter", () => {
            item.querySelector(".btn-delete").style.display = "inline-block";
          });
          item.addEventListener("mouseleave", () => {
            item.querySelector(".btn-delete").style.display = "none";
          });

          item.querySelector(".btn-delete").addEventListener("click", () => {
            deleteNotification(notif.id, item);
          });
        });
      }
    } catch (err) {
      console.error("Error fetching notifications:", err);
    }
  }

  // === Delete single notification (persist via API) ===
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
      }
    } catch (err) {
      console.error(err);
    }
  }

  // === Clear all notifications (persist via API) ===
  async function clearAllNotifications() {
    try {
      // collect all visible IDs from dropdown or dashboard
      let ids = [];
      const visibleItems = Array.from((notifDropdown || document).querySelectorAll(".dropdown-item, .notification-item"));
      if (visibleItems.length > 0) {
        ids = visibleItems.map(it => it.dataset.id || (it.querySelector("[data-id]")?.dataset.id)).filter(Boolean);
      }

      const res = await fetch("/api/admin-notifications/clear/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({ notif_ids: ids })
      });
      const data = await res.json();
      if (data.success) {
        if (notifDropdown) {
          notifDropdown.innerHTML = `
            <div class="dropdown-header">Notifications</div>
            <div class="dropdown-empty">No new notifications</div>
          `;
        }
        if (dashboardContainer) dashboardContainer.innerHTML = "";
        if (notifBadge) notifBadge.style.display = "none";
      }
    } catch (err) {
      console.error(err);
    }
  }

  // === Polling controls ===
  function startPolling() {
    if (!pollInterval) pollInterval = setInterval(fetchNotifications, POLL_DELAY);
  }
  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  // Pause polling when tab is hidden, resume when active
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopPolling();
    } else {
      fetchNotifications();
      startPolling();
    }
  });

  // Clear all button on dashboard
  const clearDashboardBtn = document.getElementById("clearAllBtn");
  if (clearDashboardBtn) {
    clearDashboardBtn.addEventListener("click", (e) => {
      e.preventDefault();
      clearAllNotifications();
    });
  }

  // === Init ===
  fetchNotifications();
  startPolling();
})();
