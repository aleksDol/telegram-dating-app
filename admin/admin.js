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
        if (tabId === "reports") loadReports();
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
        const sections = [
            {
                title: "Пользователи",
                items: [
                    { label: "Всего", value: s.total_users },
                    { label: "Заблокировано", value: s.banned_users },
                    { label: "Новых сегодня", value: s.new_users_today },
                    { label: "Активных за 7 дней", value: s.active_users_week },
                    { label: "Онлайн сейчас", value: s.online_now },
                ],
            },
            {
                title: "События",
                items: [
                    { label: "Всего", value: s.total_events },
                    { label: "Активных", value: s.active_events },
                    { label: "Скрытых", value: s.hidden_events },
                ],
            },
            {
                title: "Лайки",
                items: [
                    { label: "Всего лайков", value: s.total_likes },
                    { label: "Взаимных симпатий", value: s.mutual_likes },
                ],
            },
            {
                title: "Жалобы",
                items: [
                    { label: "Всего", value: s.total_reports },
                    { label: "Ожидают рассмотрения", value: s.pending_reports },
                    { label: "Ожидают апелляции", value: s.pending_appeals },
                ],
            },
            {
                title: "Рефералы",
                items: [
                    { label: "Пришли по ссылкам", value: s.referral_users },
                    { label: "Всего приглашено", value: s.total_referrals },
                ],
            },
            {
                title: "Баллы",
                items: [{ label: "В системе", value: s.total_points }],
            },
        ];
        var html = "";
        sections.forEach(function (sec) {
            html += "<div class=\"stats-section\"><h3 class=\"stats-section-title\">" + escapeHtml(sec.title) + "</h3><div class=\"stats-section-cards\">";
            sec.items.forEach(function (i) {
                var val = i.value != null ? Number(i.value).toLocaleString("ru") : "—";
                html += "<div class=\"stat-card\"><div class=\"label\">" + escapeHtml(i.label) + "</div><div class=\"value\">" + val + "</div></div>";
            });
            html += "</div></div>";
        });
        return html;
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
