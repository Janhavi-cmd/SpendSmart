/* ── CATEGORY CONFIG ──────────────────────────────────────────────────────── */
const CAT_CONFIG = {
  Food:          { icon: '🍔', class: 'cat-food' },
  Transport:     { icon: '🚗', class: 'cat-transport' },
  Shopping:      { icon: '🛍️', class: 'cat-shopping' },
  Bills:         { icon: '📄', class: 'cat-bills' },
  Entertainment: { icon: '🎬', class: 'cat-entertainment' },
  Health:        { icon: '💊', class: 'cat-health' },
  Education:     { icon: '📚', class: 'cat-education' },
  Other:         { icon: '📦', class: 'cat-other' },
};

const COLOR_MAP = { blue:'color-blue', green:'color-green', purple:'color-purple',
                    orange:'color-orange', red:'color-red', teal:'color-teal' };

/* ── DOM READY ────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initCategoryButtons();
  animateStats();
  autoLoadInsights();
  initAiTabs();
  initChatEnter();
  markActiveNav();
  autoHideFlash();
  applyTxIcons();
  initHealthRing();
});

/* ── CATEGORY BUTTONS ─────────────────────────────────────────────────────── */
function initCategoryButtons() {
  const hidden = document.getElementById('category-input');
  if (!hidden) return;
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (hidden) hidden.value = btn.dataset.cat;
    });
  });
}

/* ── HEALTH RING ANIMATION ────────────────────────────────────────────────── */
function initHealthRing() {
  const ring = document.querySelector('.ring-fill');
  const bar  = document.querySelector('.health-bar-fill');
  const scoreEl = document.getElementById('health-score-val');
  if (!ring || !scoreEl) return;
  const score = parseInt(scoreEl.dataset.score || 0);
  const circumference = 220;
  const offset = circumference - (score / 100) * circumference;
  setTimeout(() => {
    ring.style.strokeDashoffset = offset;
    if (bar) bar.style.width = score + '%';
    // Color based on score
    if (score >= 85) ring.style.stroke = '#00ff88';
    else if (score >= 70) ring.style.stroke = '#00d4ff';
    else if (score >= 50) ring.style.stroke = '#ffb236';
    else ring.style.stroke = '#ff4757';
  }, 300);
}

/* ── STAT COUNTER ANIMATION ───────────────────────────────────────────────── */
function animateStats() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const isInt  = Number.isInteger(target);
    const prefix = el.dataset.prefix || '';
    let current  = 0;
    const step   = target / 40;
    const timer  = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = prefix + (isInt ? Math.round(current) : current.toFixed(0));
      if (current >= target) clearInterval(timer);
    }, 25);
  });
}

/* ── TX CATEGORY ICONS ────────────────────────────────────────────────────── */
function applyTxIcons() {
  document.querySelectorAll('.tx-cat-icon[data-cat]').forEach(el => {
    const cfg = CAT_CONFIG[el.dataset.cat] || CAT_CONFIG['Other'];
    el.textContent = cfg.icon;
    el.classList.add(cfg.class);
  });
}

/* ── AI TABS ──────────────────────────────────────────────────────────────── */
function initAiTabs() {
  document.querySelectorAll('.ai-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.ai-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.ai-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const target = document.getElementById('panel-' + tab.dataset.tab);
      if (target) target.classList.add('active');
    });
  });
}

/* ── AUTO-LOAD INSIGHTS ON PAGE LOAD ─────────────────────────────────────── */
function autoLoadInsights() {
  const grid = document.getElementById('insights-grid');
  if (!grid) return;
  loadInsights();
}

/* ── AI INSIGHTS ──────────────────────────────────────────────────────────── */
async function loadInsights() {
  const grid = document.getElementById('insights-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="ai-skeleton" style="grid-column:1/-1;padding:20px;text-align:center;color:var(--text-muted);font-size:0.85rem;">Analyzing your spending patterns…</div>';
  try {
    const res  = await fetch('/api/ai-insights');
    const data = await res.json();
    grid.innerHTML = '';
    (data.insights || []).forEach(card => {
      const div = document.createElement('div');
      div.className = `ai-card ${COLOR_MAP[card.color] || 'color-blue'}`;
      div.innerHTML = `<div class="ai-card-icon">${card.icon}</div>
                       <div class="ai-card-title">${card.title}</div>
                       <div class="ai-card-body">${card.body}</div>`;
      grid.appendChild(div);
    });
  } catch (e) {
    grid.innerHTML = '<div style="padding:16px;color:var(--text-muted);font-size:0.85rem;">Could not load insights.</div>';
  }
}

/* ── AI BUDGET ────────────────────────────────────────────────────────────── */
async function loadBudget() {
  const grid = document.getElementById('budget-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="ai-skeleton" style="grid-column:1/-1;padding:20px;text-align:center;color:var(--text-muted);font-size:0.85rem;">Generating budget recommendations…</div>';
  try {
    const res  = await fetch('/api/ai-budget');
    const data = await res.json();
    grid.innerHTML = '';
    (data.recommendations || []).forEach(card => {
      const div = document.createElement('div');
      div.className = `ai-card ${COLOR_MAP[card.color] || 'color-blue'}`;
      div.innerHTML = `<div class="ai-card-icon">${card.icon}</div>
                       <div class="ai-card-title">${card.title}</div>
                       <div class="ai-card-body">${card.body}</div>`;
      grid.appendChild(div);
    });
  } catch (e) {
    grid.innerHTML = '<div style="padding:16px;color:var(--text-muted);font-size:0.85rem;">Could not load recommendations.</div>';
  }
}

/* ── AI CHAT ──────────────────────────────────────────────────────────────── */
function initChatEnter() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const box   = document.getElementById('chat-box');
  if (!input || !box) return;
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  // User bubble
  appendMsg(box, msg, 'user');

  // Typing indicator
  const typingId = 'typing-' + Date.now();
  box.innerHTML += `<div class="chat-msg bot" id="${typingId}">
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>
  </div>`;
  box.scrollTop = box.scrollHeight;

  try {
    const res  = await fetch('/api/ai-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    document.getElementById(typingId)?.remove();
    appendMsg(box, data.response || 'Sorry, I had trouble answering that.', 'bot');
  } catch (e) {
    document.getElementById(typingId)?.remove();
    appendMsg(box, 'Connection error. Please try again.', 'bot');
  }
}

function appendMsg(box, text, role) {
  const avatar  = role === 'user' ? '👤' : '🤖';
  // Parse **bold** markdown
  const html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  const div  = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = `<div class="chat-avatar">${avatar}</div><div class="chat-bubble">${html}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

/* ── TAB LOAD TRIGGER ─────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.ai-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      if (tab.dataset.tab === 'budget') loadBudget();
    });
  });
});

/* ── ACTIVE NAV ───────────────────────────────────────────────────────────── */
function markActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === path || (path === '/' && href === '/')) {
      link.classList.add('active');
    } else if (href !== '/' && path.startsWith(href)) {
      link.classList.add('active');
    }
  });
}

/* ── AUTO-HIDE FLASH ──────────────────────────────────────────────────────── */
function autoHideFlash() {
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(f => {
      f.style.transition = 'opacity 0.5s';
      f.style.opacity = '0';
      setTimeout(() => f.remove(), 500);
    });
  }, 4000);
}

/* ── ANALYTICS CHARTS ─────────────────────────────────────────────────────── */
async function initAnalytics() {
  try {
    const res  = await fetch('/api/analytics-data');
    const data = await res.json();
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const textColor = isDark ? '#7d8590' : '#5a6a7e';
    const gridColor = isDark ? 'rgba(48,54,61,0.5)' : 'rgba(200,210,220,0.5)';

    const defaults = {
      plugins: { legend: { labels: { color: textColor, font: { family: 'DM Mono', size: 11 } } } },
      scales: {
        x: { ticks: { color: textColor }, grid: { color: gridColor } },
        y: { ticks: { color: textColor }, grid: { color: gridColor } }
      }
    };

    // Trend line chart
    new Chart(document.getElementById('trendChart'), {
      type: 'line',
      data: {
        labels: data.trend.labels,
        datasets: [{
          label: 'Monthly Spend (₹)',
          data: data.trend.data,
          borderColor: '#00ff88', backgroundColor: 'rgba(0,255,136,0.08)',
          fill: true, tension: 0.4, pointBackgroundColor: '#00ff88',
          pointRadius: 5, pointHoverRadius: 8
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, ...defaults }
    });

    // Donut
    new Chart(document.getElementById('donutChart'), {
      type: 'doughnut',
      data: {
        labels: data.donut.labels,
        datasets: [{
          data: data.donut.data,
          backgroundColor: ['#00ff88','#00d4ff','#b06cff','#ffb236','#ff4757','#4ecdc4','#ff9a00','#7d8590'],
          borderWidth: 0, hoverOffset: 8
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: textColor, font: { family: 'DM Mono', size: 11 }, padding: 12 } } },
        cutout: '65%'
      }
    });

    // Bar comparison
    new Chart(document.getElementById('barChart'), {
      type: 'bar',
      data: {
        labels: data.bar.categories,
        datasets: [
          { label: 'This Month', data: data.bar.this_month, backgroundColor: 'rgba(0,255,136,0.7)', borderRadius: 4 },
          { label: 'Last Month', data: data.bar.last_month, backgroundColor: 'rgba(0,212,255,0.5)', borderRadius: 4 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false, ...defaults }
    });
  } catch(e) {
    console.error('Analytics error:', e);
  }
}

if (document.getElementById('trendChart')) {
  document.addEventListener('DOMContentLoaded', initAnalytics);
}
