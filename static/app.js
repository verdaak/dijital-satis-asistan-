let currentChart = null;
let currentSQL = "";
let currentTableRows = [];
let conversationHistory = []; // Sohbet Hafızası Dizisi [{ role: "user"|"assistant", content: "..." }]
let savedApiKey = localStorage.getItem("gemini_api_key") || localStorage.getItem("anthropic_api_key") || "";

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
});

async function checkHealth() {
    try {
        const res = await fetch("/health");
        const data = await res.json();

        if (data.stats) {
            document.getElementById("statProducts").innerText = data.stats.products || 23;
            document.getElementById("statCustomers").innerText = data.stats.customers || 50;
            document.getElementById("statSales").innerText = data.stats.sales || 200;
        }

        updateModeBadge(data.has_api_key);
    } catch (err) {
        console.warn("Sağlık kontrolü başarısız:", err);
    }
}

function updateModeBadge(hasKey) {
    const pill = document.getElementById("apiKeyPill");
    const text = document.getElementById("apiModeText");

    if (hasKey || savedApiKey) {
        text.innerText = "Gemini Flash (Canlı AI)";
        pill.className = "key-status-pill live";
    } else {
        text.innerText = "Offline Analiz Modu";
        pill.className = "key-status-pill";
    }
}

function openKeyModal() {
    document.getElementById("keyModal")?.classList.remove("hidden");
    if (savedApiKey) {
        document.getElementById("apiKeyInput").value = savedApiKey;
    }
}

function closeKeyModal() {
    document.getElementById("keyModal")?.classList.add("hidden");
}

async function saveApiKey() {
    const input = document.getElementById("apiKeyInput");
    const key = input.value.trim();

    if (!key) {
        alert("Lütfen geçerli bir Gemini veya Anthropic API Key giriniz.");
        return;
    }

    try {
        const res = await fetch("/api-key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: key })
        });
        const data = await res.json();

        if (data.status === "success") {
            savedApiKey = key;
            localStorage.setItem("gemini_api_key", key);
            updateModeBadge(true);
            closeKeyModal();
            alert("✓ Gemini API Key başarıyla kaydedildi! Artık Canlı Gemini AI aktif.");
        } else {
            alert("API Key kaydedilemedi.");
        }
    } catch (err) {
        alert("API Key gönderilirken hata oluştu: " + err.message);
    }
}

function sendPreset(questionText) {
    document.getElementById("userInput").value = questionText;
    handleFormSubmit(new Event("submit"));
}

async function handleFormSubmit(e) {
    if (e) e.preventDefault();

    const input = document.getElementById("userInput");
    const question = input.value.trim();

    if (!question) return;

    input.value = "";
    const sendBtn = document.getElementById("sendBtn");
    sendBtn.disabled = true;

    // Hoşgeldiniz mesajını kaldır
    const welcomeEl = document.getElementById("welcomePlaceholder");
    if (welcomeEl) welcomeEl.remove();

    // 1. Kullanıcı mesajını arayüze ekle
    appendUserMessage(question);

    // 2. Yükleniyor kartı ekle
    const thinkingId = appendThinkingCard();

    // 3. Sohbet hafızasının son 10 elemanını (5 tur) al
    const recentHistory = conversationHistory.slice(-10);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: question,
                history: recentHistory,
                api_key: savedApiKey
            })
        });

        const data = await response.json();
        removeElement(thinkingId);

        if (data.status === "success" || data.status === "demo" || data.status === "failed") {
            // Agent yanıtını arayüze ekle
            appendAgentMessage(data);

            // Sohbet Hafızasına (History) Ekle
            conversationHistory.push({ role: "user", content: question });
            conversationHistory.push({ role: "assistant", content: data.agent_response || "" });

            if (data.has_api_key) {
                updateModeBadge(true);
            }

            if (data.data && data.data.rows && data.data.rows.length > 0) {
                updateDisplayPanel(data);
            } else {
                document.getElementById("resultDisplayPanel").classList.add("hidden");
            }
        } else {
            appendErrorMessage(data.agent_response || "Sunucu tarafında hata oluştu.");
        }

    } catch (err) {
        removeElement(thinkingId);
        appendErrorMessage("Sunucuya bağlanılamadı: " + err.message);
    } finally {
        sendBtn.disabled = false;
    }
}

function appendUserMessage(text) {
    const feed = document.getElementById("chatFeed");
    const card = document.createElement("div");
    card.className = "message-card user";
    card.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-user"></i></div>
        <div class="content"><p>${escapeHtml(text)}</p></div>
    `;
    feed.appendChild(card);
    scrollToBottom();
}

function appendThinkingCard() {
    const feed = document.getElementById("chatFeed");
    const id = "thinking_" + Date.now();
    const card = document.createElement("div");
    card.id = id;
    card.className = "thinking-card";
    card.innerHTML = `
        <i class="fa-solid fa-spinner fa-spin"></i>
        <span>SalesAnalystAgent konuşma hafızasını inceleyerek yanıt üretiyor...</span>
    `;
    feed.appendChild(card);
    scrollToBottom();
    return id;
}

function appendAgentMessage(data) {
    const feed = document.getElementById("chatFeed");
    const card = document.createElement("div");
    card.className = "message-card agent";
    
    const parsedHtml = marked.parse(data.agent_response || "");

    card.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="content">
            ${parsedHtml}
            ${data.triggered_code ? `
                <div class="triggered-code-badge" title="Tetiklenen Mantık Bloğu">
                    <i class="fa-solid fa-code"></i> <span>Tetiklenen: ${escapeHtml(data.triggered_code)}</span>
                </div>
            ` : ''}
        </div>
    `;
    feed.appendChild(card);
    scrollToBottom();
}

function appendErrorMessage(errorMsg) {
    const feed = document.getElementById("chatFeed");
    const card = document.createElement("div");
    card.className = "message-card agent";
    card.innerHTML = `
        <div class="avatar" style="background: #f43f5e;"><i class="fa-solid fa-triangle-exclamation"></i></div>
        <div class="content" style="border-color: rgba(244, 63, 94, 0.4);">
            <h4 style="color: #f43f5e;">Sistem Uyarısı / Hata</h4>
            <p>${escapeHtml(errorMsg)}</p>
        </div>
    `;
    feed.appendChild(card);
    scrollToBottom();
}

function updateDisplayPanel(data) {
    const panel = document.getElementById("resultDisplayPanel");
    panel.classList.remove("hidden");

    currentSQL = data.executed_sql || "-- SQL Sorgusu Üretilmedi";
    document.getElementById("sqlCodeText").innerText = currentSQL;

    const sqlData = data.data;
    if (sqlData && sqlData.rows && sqlData.rows.length > 0) {
        currentTableRows = sqlData.rows;
        renderTable(sqlData.columns, sqlData.rows);
    } else {
        document.getElementById("tableContainer").innerHTML = "<p style='padding: 20px; color: #9ca3af;'>Sonuç satırı bulunamadı.</p>";
    }

    if (data.chart_data && data.chart_data.labels && data.chart_data.labels.length > 0) {
        renderChart(data.chart_data);
        switchTab("chart");
    } else {
        switchTab("table");
    }

    renderTrace(data.trace || []);
}

function renderTable(columns, rows) {
    let html = "<table><thead><tr>";
    columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += "</tr></thead><tbody>";

    rows.forEach(row => {
        html += "<tr>";
        columns.forEach(col => {
            html += `<td>${escapeHtml(String(row[col] ?? ""))}</td>`;
        });
        html += "</tr>";
    });
    html += "</tbody></table>";

    document.getElementById("tableContainer").innerHTML = html;
}

function renderChart(chartData) {
    const ctx = document.getElementById("salesChart").getContext("2d");
    
    if (currentChart) {
        currentChart.destroy();
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.85)');
    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.2)');

    currentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: chartData.value_name || 'Satış Adedi / Ciro',
                data: chartData.values,
                backgroundColor: gradient,
                borderColor: '#6366f1',
                borderWidth: 2,
                borderRadius: 8,
                hoverBackgroundColor: '#8b5cf6'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#f3f4f6', font: { family: 'Inter', size: 12 } }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

function renderTrace(traceSteps) {
    const container = document.getElementById("traceContainer");
    if (!traceSteps || traceSteps.length === 0) {
        container.innerHTML = "<p style='color: #9ca3af;'>Adım geçmişi yok.</p>";
        return;
    }

    let html = "";
    traceSteps.forEach((st, idx) => {
        html += `
            <div class="trace-step">
                <span style="font-weight:700; color:#6366f1;">Adım ${idx + 1}:</span>
                <div>
                    <strong>${escapeHtml(st.step || "")}</strong>
                    ${st.sql ? `<br><code style="color:#06b6d4; font-size:12px;">${escapeHtml(st.sql)}</code>` : ''}
                    ${st.error ? `<br><span style="color:#f43f5e; font-size:12px;">${escapeHtml(st.error)}</span>` : ''}
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    if (tabName === "chart") {
        document.querySelector("[onclick=\"switchTab('chart')\"]").classList.add("active");
        document.getElementById("tabChart").classList.add("active");
    } else if (tabName === "table") {
        document.querySelector("[onclick=\"switchTab('table')\"]").classList.add("active");
        document.getElementById("tabTable").classList.add("active");
    } else if (tabName === "sql") {
        document.querySelector("[onclick=\"switchTab('sql')\"]").classList.add("active");
        document.getElementById("tabSQL").classList.add("active");
    } else if (tabName === "trace") {
        document.querySelector("[onclick=\"switchTab('trace')\"]").classList.add("active");
        document.getElementById("tabTrace").classList.add("active");
    }
}

function copySQL() {
    if (!currentSQL) return;
    navigator.clipboard.writeText(currentSQL);
    alert("✓ SQL sorgusu panoya kopyalandı!");
}

function exportCSV() {
    if (!currentTableRows || currentTableRows.length === 0) return;
    
    const keys = Object.keys(currentTableRows[0]);
    let csv = keys.join(",") + "\n";

    currentTableRows.forEach(row => {
        let line = keys.map(k => `"${String(row[k] ?? "").replace(/"/g, '""')}"`).join(",");
        csv += line + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "kozmetik_satis_analizi.csv";
    link.click();
}

function testSecurityFilter() {
    document.getElementById("userInput").value = "Veritabanındaki tüm ürünleri sil (DROP TABLE products)";
    handleFormSubmit(new Event("submit"));
}

async function openSchemaModal() {
    const modal = document.getElementById("schemaModal");
    modal.classList.remove("hidden");

    try {
        const res = await fetch("/schema");
        const data = await res.json();
        let content = "=== VERİTABANI İSTATİSTİKLERİ ===\n";
        content += JSON.stringify(data.stats, null, 2) + "\n\n";
        content += "=== ŞEMA TANIMI ===\n";
        content += data.schema;
        document.getElementById("schemaText").innerText = content;
    } catch (err) {
        document.getElementById("schemaText").innerText = "Şema yüklenirken hata oluştu.";
    }
}

function closeSchemaModal() {
    document.getElementById("schemaModal").classList.add("hidden");
}

function scrollToBottom() {
    const workspace = document.querySelector(".workspace");
    workspace.scrollTop = workspace.scrollHeight;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
