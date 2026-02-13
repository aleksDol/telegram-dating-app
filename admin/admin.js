(function () {
    "use strict";
    const STORAGE_KEY = "admin_token";
    const API_PREFIX = "/admin/api";

    function ready() {
        window.AdminPanelReady = true;
    }

    function getToken() {
        return localStorage.getItem(STORAGE_KEY);
    }

    function setToken(token) {
        if (token) localStorage.setItem(STORAGE_KEY, token);
        else localStorage.removeItem(STORAGE_KEY);
    }

    async function api(path, options = {}) {
        const token = getToken();
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        };
        if (token) headers["Authorization"] = "Bearer " + token;
        let res;
        try {
            res = await fetch(API_PREFIX + path, { ...options, headers });
        } catch (err) {
            throw new Error(err.message || "Сеть недоступна");
        }
        const body = await res.json().catch(() => ({}));
        if (res.status === 401) {
            setToken(null);
            showLogin();
            throw new Error(body.detail || "Сессия истекла");
        }
        if (!res.ok) {
            throw new Error(body.detail || res.statusText || "Ошибка сервера");
        }
        return body;
    }

    function showLogin() {
        document.getElementById("login-screen").classList.remove("hidden");
        document.getElementById("dashboard-screen").classList.add("hidden");
    }

    function showDashboard() {
        document.getElementById("login-screen").classList.add("hidden");
        document.getElementById("dashboard-screen").classList.remove("hidden");
        if (document.querySelector(".tab.active")) {
            const tab = document.querySelector(".tab.active").dataset.tab;
            openTab(tab);
        }
    }

    // Login form
    var loginForm = document.getElementById("login-form");
    if (!loginForm) {
        console.error("Admin: #login-form not found");
        return;
    }
    loginForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        e.stopPropagation();
        var errEl = document.getElementById("login-error");
        var btn = document.getElementById("login-btn");
        if (errEl) {
            errEl.classList.add("hidden");
            errEl.textContent = "";
        }
        var form = e.target;
        var loginInput = form.querySelector('[name="login"]') || document.getElementById("input-login");
        var passwordInput = form.querySelector('[name="password"]') || document.getElementById("input-password");
        var tokenInput = form.querySelector('[name="token"]') || document.getElementById("input-token");
        var login = loginInput ? loginInput.value.trim() : "";
        var password = passwordInput ? passwordInput.value.trim() : "";
        var token = tokenInput ? tokenInput.value.trim() : "";
        if (!login || !password || !token) {
            if (errEl) {
                errEl.textContent = "Заполните все поля";
                errEl.classList.remove("hidden");
            }
            return;
        }
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Вход…";
        }
        try {
            var data = await api("/auth", {
                method: "POST",
                body: JSON.stringify({ login: login, password: password, token: token }),
            });
            if (!data || !data.access_token) {
                throw new Error("Сервер не вернул токен");
            }
            setToken(data.access_token);
            showDashboard();
        } catch (err) {
            var msg = err.message || "Ошибка входа";
            if (msg.indexOf("fetch") !== -1 || msg === "Failed to fetch" || msg.indexOf("NetworkError") !== -1 || msg.indexOf("Сеть") !== -1) {
                msg = "Не удалось подключиться к серверу. Убедитесь, что бэкенд запущен и админка открыта с того же домена (например https://ваш-домен.ru/admin или http://localhost:8080/admin).";
            }
            if (errEl) {
                errEl.textContent = msg;
                errEl.classList.remove("hidden");
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Войти";
            }
        }
    });
    ready();

    // Logout
    document.getElementById("logout-btn").addEventListener("click", () => {
        setToken(null);
        showLogin();
    });

    // Tabs
    function openTab(tabId) {
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
        const tabBtn = document.querySelector('.tab[data-tab="' + tabId + '"]');
        const panel = document.getElementById("tab-" + tabId);
        if (tabBtn) tabBtn.classList.add("active");
        if (panel) panel.classList.add("active");
        if (tabId === "stats") loadStats();
        if (tabId === "funnel") loadFunnel();
        if (tabId === "reports") loadReports();
        if (tabId === "users") loadRecentUsers();
    }

    document.querySelectorAll(".tab").forEach((btn) => {
        btn.addEventListener("click", () => openTab(btn.dataset.tab));
    });

    // Stats
    async function loadStats() {
        const loading = document.getElementById("stats-loading");
        const content = document.getElementById("stats-content");
        loading.classList.remove("hidden");
        loading.textContent = "Загрузка…";
        content.classList.add("hidden");
        content.innerHTML = "";
        try {
            const s = await api("/stats");
            loading.classList.add("hidden");
            content.innerHTML = renderStats(s);
            content.classList.remove("hidden");
        } catch (err) {
            loading.classList.remove("hidden");
            loading.innerHTML = '<span class="error-msg">Ошибка: ' + escapeHtml(err.message) + '</span>';
        }
    }

    function renderStats(s) {
        const num = (v) => (v != null ? Number(v).toLocaleString("ru") : "—");
        const totalUsers = Number(s.total_users) || 0;
        const totalLikes = Number(s.total_likes) || 1;
        const mutualPct = totalLikes > 0 ? Math.round((Number(s.mutual_likes) || 0) / totalLikes * 100) : 0;
        const activePct = totalUsers > 0 ? Math.round((Number(s.active_users_week) || 0) / totalUsers * 100) : 0;
        const reportsTotal = Number(s.total_reports) || 1;
        const pendingPct = reportsTotal > 0 ? Math.round((Number(s.pending_reports) || 0) / reportsTotal * 100) : 0;

        let html = '<div class="dashboard-hero">';
        html += '<div class="dashboard-kpi kpi-users"><div class="kpi-icon">👥</div><div class="kpi-label">Пользователи</div><div class="kpi-value">' + num(s.total_users) + '</div></div>';
        html += '<div class="dashboard-kpi kpi-events"><div class="kpi-icon">📅</div><div class="kpi-label">События</div><div class="kpi-value">' + num(s.total_events) + '</div></div>';
        html += '<div class="dashboard-kpi kpi-likes"><div class="kpi-icon">❤️</div><div class="kpi-label">Взаимные симпатии</div><div class="kpi-value">' + num(s.mutual_likes) + '</div></div>';
        html += '<div class="dashboard-kpi kpi-reports"><div class="kpi-icon">⚠️</div><div class="kpi-label">Жалобы</div><div class="kpi-value">' + num(s.total_reports) + '</div></div>';
        html += '<div class="dashboard-kpi kpi-online"><div class="kpi-icon">🟢</div><div class="kpi-label">Онлайн сейчас</div><div class="kpi-value">' + num(s.online_now) + '</div></div>';
        html += "</div>";

        html += '<div class="dashboard-section">';
        html += '<h3 class="dashboard-section-title"><span class="section-icon">👥</span> Пользователи</h3>';
        html += '<div class="dashboard-cards">';
        html += '<div class="dashboard-card"><div class="card-label">Всего</div><div class="card-value">' + num(s.total_users) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Заблокировано</div><div class="card-value">' + num(s.banned_users) + '</div><div class="card-bar-wrap"><div class="card-bar danger" style="width:' + (totalUsers > 0 ? Math.min(100, Math.round((Number(s.banned_users) || 0) / totalUsers * 100)) : 0) + '%"></div></div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Новых сегодня</div><div class="card-value">' + num(s.new_users_today) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Активных за 7 дней</div><div class="card-value">' + num(s.active_users_week) + '</div><div class="card-bar-wrap"><div class="card-bar success" style="width:' + activePct + '%"></div></div></div>';
        html += "</div></div>";

        html += '<div class="dashboard-section">';
        html += '<h3 class="dashboard-section-title"><span class="section-icon">📅</span> События</h3>';
        html += '<div class="dashboard-cards">';
        const totalEvents = Number(s.total_events) || 1;
        const activeEvents = Number(s.active_events) || 0;
        const activeEventsPct = totalEvents > 0 ? Math.round(activeEvents / totalEvents * 100) : 0;
        html += '<div class="dashboard-card"><div class="card-label">Всего</div><div class="card-value">' + num(s.total_events) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Активных (будущих)</div><div class="card-value">' + num(s.active_events) + '</div><div class="card-bar-wrap"><div class="card-bar accent" style="width:' + activeEventsPct + '%"></div></div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Скрытых</div><div class="card-value">' + num(s.hidden_events) + '</div></div>';
        html += "</div></div>";

        html += '<div class="dashboard-section">';
        html += '<h3 class="dashboard-section-title"><span class="section-icon">❤️</span> Лайки</h3>';
        html += '<div class="dashboard-cards">';
        html += '<div class="dashboard-card"><div class="card-label">Всего лайков</div><div class="card-value">' + num(s.total_likes) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Взаимных симпатий</div><div class="card-value">' + num(s.mutual_likes) + '</div><div class="card-bar-wrap"><div class="card-bar success" style="width:' + mutualPct + '%"></div></div></div>';
        html += "</div></div>";

        html += '<div class="dashboard-section">';
        html += '<h3 class="dashboard-section-title"><span class="section-icon">⚠️</span> Жалобы</h3>';
        html += '<div class="dashboard-cards">';
        html += '<div class="dashboard-card"><div class="card-label">Всего</div><div class="card-value">' + num(s.total_reports) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Ожидают рассмотрения</div><div class="card-value">' + num(s.pending_reports) + '</div><div class="card-bar-wrap"><div class="card-bar warning" style="width:' + pendingPct + '%"></div></div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Ожидают апелляции</div><div class="card-value">' + num(s.pending_appeals) + '</div></div>';
        html += "</div></div>";

        html += '<div class="dashboard-section">';
        html += '<h3 class="dashboard-section-title"><span class="section-icon">🔗</span> Рефералы и баллы</h3>';
        html += '<div class="dashboard-cards">';
        html += '<div class="dashboard-card"><div class="card-label">Пришли по ссылкам</div><div class="card-value">' + num(s.referral_users) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Всего приглашено</div><div class="card-value">' + num(s.total_referrals) + '</div></div>';
        html += '<div class="dashboard-card"><div class="card-label">Баллов в системе</div><div class="card-value">' + num(s.total_points) + '</div></div>';
        html += "</div></div>";

        if (s.top_cities && s.top_cities.length > 0) {
            html += '<div class="dashboard-grid-2">';
            html += '<div class="dashboard-block"><h4 class="dashboard-block-title">🏙 Топ городов</h4><div class="dashboard-block-list">';
            s.top_cities.forEach(function (row) {
                html += '<div class="dashboard-block-row"><span class="row-label">' + escapeHtml((row.city || "").trim() || "—") + '</span><span class="row-value">' + num(row.count) + '</span></div>';
            });
            html += "</div></div>";
            if (s.top_referrers && s.top_referrers.length > 0) {
                html += '<div class="dashboard-block"><h4 class="dashboard-block-title">⭐ Топ рефереров</h4><div class="dashboard-block-list">';
                s.top_referrers.forEach(function (row) {
                    html += '<div class="dashboard-block-row"><span class="row-label">' + escapeHtml((row.name || "").trim() || "—") + '</span><span class="row-value">' + num(row.referrals_count) + '</span></div>';
                });
                html += "</div></div>";
            }
            html += "</div>";
        } else if (s.top_referrers && s.top_referrers.length > 0) {
            html += '<div class="dashboard-section">';
            html += '<div class="dashboard-block"><h4 class="dashboard-block-title">⭐ Топ рефереров</h4><div class="dashboard-block-list">';
            s.top_referrers.forEach(function (row) {
                html += '<div class="dashboard-block-row"><span class="row-label">' + escapeHtml((row.name || "").trim() || "—") + '</span><span class="row-value">' + num(row.referrals_count) + '</span></div>';
            });
            html += "</div></div></div>";
        }

        return html;
    }

    // Воронка
    async function loadFunnel() {
        const loading = document.getElementById("funnel-loading");
        const content = document.getElementById("funnel-content");
        if (!loading || !content) return;
        loading.classList.remove("hidden");
        loading.textContent = "Загрузка воронки…";
        content.classList.add("hidden");
        try {
            const data = await api("/funnel");
            loading.classList.add("hidden");
            content.classList.remove("hidden");
            const tbodyIds = {
                started_not_registered: "funnel-started",
                registered_no_events: "funnel-registered",
                created_events: "funnel-events",
                has_matching: "funnel-matching",
            };
            for (const [key, tbodyId] of Object.entries(tbodyIds)) {
                const tbody = document.getElementById(tbodyId);
                const list = data[key] || [];
                if (!tbody) continue;
                if (list.length === 0) {
                    tbody.innerHTML = "<tr><td colspan=\"4\" class=\"funnel-empty\">Нет пользователей</td></tr>";
                } else {
                    tbody.innerHTML = list
                        .map(function (u) {
                            const name = escapeHtml((u.name || "").trim() || "—");
                            const gender = escapeHtml((u.gender || "").trim() || "—");
                            const city = escapeHtml((u.city || "").trim() || "—");
                            return (
                                "<tr data-user-id=\"" +
                                u.user_id +
                                "\"><td>" +
                                escapeHtml(String(u.user_id)) +
                                "</td><td>" +
                                name +
                                "</td><td>" +
                                gender +
                                "</td><td>" +
                                city +
                                "</td></tr>"
                            );
                        })
                        .join("");
                }
            }
        } catch (err) {
            loading.classList.remove("hidden");
            loading.innerHTML = '<span class="error-msg">Ошибка: ' + escapeHtml(err.message) + "</span>";
        }
    }

    var funnelContent = document.getElementById("funnel-content");
    if (funnelContent) {
        funnelContent.addEventListener("click", function (e) {
            var row = e.target.closest("tr[data-user-id]");
            if (row) {
                var id = row.getAttribute("data-user-id");
                if (id) {
                    document.getElementById("user-search").value = id;
                    openTab("users");
                    setTimeout(searchUser, 100);
                }
            }
        });
    }

    // Последние пользователи
    async function loadRecentUsers() {
        var loadingEl = document.getElementById("users-recent-loading");
        var listEl = document.getElementById("users-recent-list");
        if (!listEl) return;
        if (loadingEl) {
            loadingEl.classList.remove("hidden");
            loadingEl.textContent = "Загрузка…";
        }
        listEl.innerHTML = "";
        try {
            var data = await api("/users/recent?limit=10");
            if (loadingEl) loadingEl.classList.add("hidden");
            if (!data.users || data.users.length === 0) {
                listEl.innerHTML = "<p class=\"empty\">Нет пользователей</p>";
                return;
            }
            listEl.innerHTML = "<table class=\"users-recent-table\"><thead><tr><th>ID</th><th>Город</th><th>Имя</th></tr></thead><tbody>" +
                data.users.map(function (u) {
                    var city = (u.city || "").trim() || "—";
                    var name = (u.name || "").trim() || "—";
                    return "<tr data-user-id=\"" + u.user_id + "\"><td>" + escapeHtml(String(u.user_id)) + "</td><td>" + escapeHtml(city) + "</td><td>" + escapeHtml(name) + "</td></tr>";
                }).join("") +
                "</tbody></table>";
        } catch (err) {
            if (loadingEl) loadingEl.classList.add("hidden");
            listEl.innerHTML = "<p class=\"error\">" + escapeHtml(err.message) + "</p>";
        }
    }

    var userResultEl = document.getElementById("user-result");
    if (userResultEl) {
        userResultEl.addEventListener("click", function (e) {
            var btn = e.target.closest("[data-action][data-id]");
            if (!btn) return;
            var action = btn.dataset.action;
            var id = parseInt(btn.dataset.id, 10);
            if (action === "ban") {
                var reason = prompt("Причина блокировки:", "Нарушение правил");
                if (reason == null) return;
                api("/user/" + id + "/ban", {
                    method: "POST",
                    body: JSON.stringify({ reason: reason.trim() || "Блокировка через веб-админку" }),
                }).then(function () { searchUser(); }).catch(function (err) { alert(err.message); });
            } else if (action === "unban") {
                api("/user/" + id + "/unban", { method: "POST" }).then(function () { searchUser(); }).catch(function (err) { alert(err.message); });
            }
        });
    }

    var usersRecentListEl = document.getElementById("users-recent-list");
    if (usersRecentListEl) {
        usersRecentListEl.addEventListener("click", function (e) {
            var row = e.target.closest("tr[data-user-id]");
            if (row) {
                var id = row.getAttribute("data-user-id");
                if (id) {
                    document.getElementById("user-search").value = id;
                    searchUser();
                }
            }
        });
    }

    // User search
    async function searchUser() {
        const input = document.getElementById("user-search");
        const resultEl = document.getElementById("user-result");
        const q = (input.value || "").trim();
        if (!q) {
            resultEl.innerHTML = '<p class="empty">Введите ID или username</p>';
            return;
        }
        resultEl.innerHTML = '<p class="loading">Поиск…</p>';
        try {
            const user = await api("/user/" + encodeURIComponent(q));
            resultEl.innerHTML = renderUserCard(user);
        } catch (err) {
            resultEl.innerHTML = '<p class="error">' + escapeHtml(err.message) + "</p>";
        }
    }

    document.getElementById("user-search-btn").addEventListener("click", searchUser);
    document.getElementById("user-search").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            searchUser();
        }
    });

    function renderUserCard(u) {
        const id = u.user_id;
        const banned = !!u.is_banned;
        let photoHtml = "";
        if (u.photo_url) {
            photoHtml = '<div class="photo-wrap"><img src="' + escapeHtml(u.photo_url) + '" alt=""></div>';
        }
        let actions = "";
        if (banned) {
            actions =
                '<button type="button" class="btn btn-success" data-action="unban" data-id="' +
                id +
                '">Разблокировать</button>';
        } else {
            actions =
                '<button type="button" class="btn btn-danger" data-action="ban" data-id="' +
                id +
                '">Заблокировать</button>';
        }
        const rows = [
            ["Имя", u.name],
            ["ID", id],
            ["Username", u.username ? "@" + u.username : "—"],
            ["Возраст", u.age],
            ["Пол", u.gender],
            ["Город", u.city || "—"],
            ["Статус", u.relationship_status || "—"],
            ["Регистрация", u.reg_date ? u.reg_date.slice(0, 10) : "—"],
            ["Очки", u.points],
            ["Событий", u.events_count],
            ["Лайков получено", u.likes_received],
            ["Лайков поставлено", u.likes_given],
            ["Взаимных", u.mutual_likes],
            ["Рефералов", u.referrals_count],
        ];
        if (banned && u.ban_reason) {
            rows.push(["Причина блокировки", u.ban_reason]);
            if (u.banned_date) rows.push(["Дата блокировки", u.banned_date.slice(0, 10)]);
        }
        const meta = rows
            .map(
                (r) =>
                    "<div><span>" +
                    escapeHtml(r[0]) +
                    ":</span> " +
                    escapeHtml(String(r[1] ?? "—")) +
                    "</div>"
            )
            .join("");
        return (
            '<div class="user-card" data-user-id="' +
            id +
            '">' +
            photoHtml +
            "<h3>" +
            escapeHtml(u.name || "Без имени") +
            "</h3>" +
            '<div class="meta">' +
            meta +
            "</div>" +
            '<div class="actions">' +
            actions +
            "</div>" +
            "</div>"
        );
    }

    document.getElementById("user-result").addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-action][data-id]");
        if (!btn) return;
        const action = btn.dataset.action;
        const id = parseInt(btn.dataset.id, 10);
        if (action === "ban") {
            const reason = prompt("Причина блокировки:", "Нарушение правил");
            if (reason == null) return;
            try {
                await api("/user/" + id + "/ban", {
                    method: "POST",
                    body: JSON.stringify({ reason: reason.trim() || "Блокировка через веб-админку" }),
                });
                searchUser();
            } catch (err) {
                alert(err.message);
            }
        } else if (action === "unban") {
            try {
                await api("/user/" + id + "/unban", { method: "POST" });
                searchUser();
            } catch (err) {
                alert(err.message);
            }
        }
    });

    // Reports
    async function loadReports() {
        const status = document.getElementById("reports-status").value;
        const loading = document.getElementById("reports-loading");
        const list = document.getElementById("reports-list");
        loading.classList.remove("hidden");
        list.innerHTML = "";
        try {
            const data = await api("/reports?status=" + encodeURIComponent(status));
            loading.classList.add("hidden");
            if (!data.reports || data.reports.length === 0) {
                list.innerHTML = '<p class="empty">Нет жалоб с выбранным статусом</p>';
            } else {
                list.innerHTML = data.reports
                    .map(function (r) {
                        const created = r.created ? r.created.slice(0, 16).replace("T", " ") : "";
                        return (
                            '<div class="report-item">' +
                            '<div class="report-meta">#' +
                            r.id +
                            " · " +
                            escapeHtml(created) +
                            ' · Пользователь ID: <a href="#" data-user-id="' +
                            r.reported_user_id +
                            '">' +
                            r.reported_user_id +
                            "</a></div>" +
                            '<div class="report-reason">' +
                            escapeHtml(r.reason || "") +
                            "</div>" +
                            "</div>"
                        );
                    })
                    .join("");
            }
        } catch (err) {
            loading.classList.add("hidden");
            list.innerHTML = '<p class="error">' + escapeHtml(err.message) + "</p>";
        }
    }

    document.getElementById("reports-status").addEventListener("change", loadReports);
    document.getElementById("reports-refresh").addEventListener("click", loadReports);
    document.getElementById("reports-list").addEventListener("click", (e) => {
        const a = e.target.closest("a[data-user-id]");
        if (!a) return;
        e.preventDefault();
        const id = a.dataset.userId;
        document.getElementById("user-search").value = id;
        openTab("users");
        setTimeout(searchUser, 100);
    });

    // Рассылка
    var broadcastPreviewEl = document.getElementById("broadcast-preview");
    var broadcastErrorEl = document.getElementById("broadcast-error");
    var broadcastPhotoDataUrl = null;

    var broadcastPhotoInput = document.getElementById("broadcast-photo");
    var broadcastPhotoPreviewEl = document.getElementById("broadcast-photo-preview");
    var broadcastPhotoClearBtn = document.getElementById("broadcast-photo-clear");
    if (broadcastPhotoInput) {
        broadcastPhotoInput.addEventListener("change", function () {
            var file = this.files && this.files[0];
            broadcastPhotoDataUrl = null;
            if (broadcastPhotoPreviewEl) {
                broadcastPhotoPreviewEl.classList.add("hidden");
                broadcastPhotoPreviewEl.innerHTML = "";
            }
            if (broadcastPhotoClearBtn) broadcastPhotoClearBtn.classList.add("hidden");
            if (!file || !file.type.match(/^image\/(jpeg|png|webp)$/i)) return;
            var reader = new FileReader();
            reader.onload = function (e) {
                broadcastPhotoDataUrl = e.target.result;
                if (broadcastPhotoPreviewEl) {
                    var img = document.createElement("img");
                    img.src = broadcastPhotoDataUrl;
                    img.alt = "Превью";
                    broadcastPhotoPreviewEl.innerHTML = "";
                    broadcastPhotoPreviewEl.appendChild(img);
                    broadcastPhotoPreviewEl.classList.remove("hidden");
                }
                if (broadcastPhotoClearBtn) broadcastPhotoClearBtn.classList.remove("hidden");
            };
            reader.readAsDataURL(file);
        });
    }
    if (broadcastPhotoClearBtn) {
        broadcastPhotoClearBtn.addEventListener("click", function () {
            broadcastPhotoDataUrl = null;
            if (broadcastPhotoInput) broadcastPhotoInput.value = "";
            if (broadcastPhotoPreviewEl) {
                broadcastPhotoPreviewEl.classList.add("hidden");
                broadcastPhotoPreviewEl.innerHTML = "";
            }
            broadcastPhotoClearBtn.classList.add("hidden");
        });
    }

    function broadcastWrapTag(openTag, closeTag) {
        var ta = document.getElementById("broadcast-text");
        if (!ta) return;
        var start = ta.selectionStart;
        var end = ta.selectionEnd;
        var text = ta.value;
        var selected = text.slice(start, end);
        var before = text.slice(0, start);
        var after = text.slice(end);
        ta.value = before + openTag + selected + closeTag + after;
        ta.selectionStart = start;
        ta.selectionEnd = start + openTag.length + selected.length + closeTag.length;
        ta.focus();
    }

    document.getElementById("broadcast-format-bold").addEventListener("click", function () {
        broadcastWrapTag("<b>", "</b>");
    });
    document.getElementById("broadcast-format-italic").addEventListener("click", function () {
        broadcastWrapTag("<i>", "</i>");
    });
    document.getElementById("broadcast-format-link").addEventListener("click", function () {
        var ta = document.getElementById("broadcast-text");
        if (!ta) return;
        var start = ta.selectionStart;
        var end = ta.selectionEnd;
        var selected = ta.value.slice(start, end);
        var url = prompt("Введите URL ссылки:", "https://");
        if (url == null) return;
        url = url.trim();
        if (!url) return;
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "https://" + url;
        broadcastWrapTag('<a href="' + url.replace(/"/g, "&quot;") + '">', "</a>");
    });

    document.getElementById("broadcast-preview-btn").addEventListener("click", async function () {
        var textEl = document.getElementById("broadcast-text");
        var genderEl = document.getElementById("broadcast-gender");
        var text = textEl ? textEl.value.trim() : "";
        var gender = genderEl ? genderEl.value : "all";
        if (broadcastErrorEl) {
            broadcastErrorEl.classList.add("hidden");
            broadcastErrorEl.textContent = "";
        }
        if (broadcastPreviewEl) {
            broadcastPreviewEl.classList.add("hidden");
            broadcastPreviewEl.textContent = "";
        }
        try {
            var data = await api("/broadcast/preview", {
                method: "POST",
                body: JSON.stringify({ text: text, gender: gender }),
            });
            var label = gender === "all" ? "Все пользователи" : gender === "Мужской" ? "Мужчины" : "Женщины";
            if (broadcastPreviewEl) {
                broadcastPreviewEl.textContent = "Сегмент: " + label + ". Получателей: " + (data.count || 0).toLocaleString("ru") + ".";
                broadcastPreviewEl.classList.remove("hidden");
            }
        } catch (err) {
            if (broadcastErrorEl) {
                broadcastErrorEl.textContent = err.message || "Ошибка предпросмотра";
                broadcastErrorEl.classList.remove("hidden");
            }
        }
    });
    document.getElementById("broadcast-send-btn").addEventListener("click", async function () {
        var textEl = document.getElementById("broadcast-text");
        var genderEl = document.getElementById("broadcast-gender");
        var text = textEl ? textEl.value.trim() : "";
        var gender = genderEl ? genderEl.value : "all";
        if (broadcastErrorEl) {
            broadcastErrorEl.classList.add("hidden");
            broadcastErrorEl.textContent = "";
        }
        if (!text) {
            if (broadcastErrorEl) {
                broadcastErrorEl.textContent = "Введите текст сообщения.";
                broadcastErrorEl.classList.remove("hidden");
            }
            return;
        }
        if (!confirm("Отправить рассылку выбранному сегменту? Отменить будет нельзя.")) return;
        var btn = document.getElementById("broadcast-send-btn");
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Отправка…";
        }
        try {
            var payload = { text: text, gender: gender };
            if (broadcastPhotoDataUrl) payload.photo = broadcastPhotoDataUrl;
            var data = await api("/broadcast/send", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            if (broadcastPreviewEl) {
                broadcastPreviewEl.textContent = "Рассылка #" + (data.broadcast_id || "") + " запущена. Получателей: " + (data.total_recipients || 0).toLocaleString("ru") + ". Сообщения отправляются в фоне.";
                broadcastPreviewEl.classList.remove("hidden");
            }
            if (textEl) textEl.value = "";
            broadcastPhotoDataUrl = null;
            if (broadcastPhotoInput) broadcastPhotoInput.value = "";
            if (broadcastPhotoPreviewEl) {
                broadcastPhotoPreviewEl.classList.add("hidden");
                broadcastPhotoPreviewEl.innerHTML = "";
            }
            if (broadcastPhotoClearBtn) broadcastPhotoClearBtn.classList.add("hidden");
        } catch (err) {
            if (broadcastErrorEl) {
                broadcastErrorEl.textContent = err.message || "Ошибка отправки";
                broadcastErrorEl.classList.remove("hidden");
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Отправить рассылку";
            }
        }
    });

    function escapeHtml(s) {
        if (s == null) return "";
        const div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }

    // Init
    if (getToken()) {
        showDashboard();
    } else {
        showLogin();
    }
})();
