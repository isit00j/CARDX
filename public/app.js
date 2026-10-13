document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initGenerator();
  initValidator();
  initBinLookup();
  initBulkChecker();
  initBinDatabase();
  initExtrapolation();
  initTemplates();
  initExport();
  initSettings();
  initTelegram();
});

// Global State for active session records, stats, and settings
const appState = {
  lastRecords: [],
  stats: {
    total: 0,
    approved: 0,
    declined: 0
  },
  settings: {
    defaultBrand: 'Visa',
    threads: 8,
    mask: true
  }
};

function updateStatsCounters(totalDelta = 0, approvedDelta = 0, declinedDelta = 0) {
  appState.stats.total += totalDelta;
  appState.stats.approved += approvedDelta;
  appState.stats.declined += declinedDelta;

  const totalEl = document.getElementById('stat-total');
  const approvedEl = document.getElementById('stat-approved');
  const declinedEl = document.getElementById('stat-declined');

  if (totalEl) totalEl.textContent = appState.stats.total.toLocaleString();
  if (approvedEl) approvedEl.textContent = appState.stats.approved.toLocaleString();
  if (declinedEl) declinedEl.textContent = appState.stats.declined.toLocaleString();
}

// Tab Navigation
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab');

      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      contents.forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      const contentEl = document.getElementById(target);
      if (contentEl) contentEl.classList.add('active');
    });
  });
}

// 1. Card Generator Handler
function initGenerator() {
  const btnGenerate = document.getElementById('btn-generate');
  const resultsContainer = document.getElementById('gen-results');
  const btnCopy = document.getElementById('btn-copy-gen');

  let currentGenerated = [];

  if (btnGenerate) {
    btnGenerate.addEventListener('click', async () => {
      const brand = document.getElementById('gen-brand').value;
      const count = parseInt(document.getElementById('gen-count').value, 10) || 10;
      const bin_prefix = document.getElementById('gen-bin').value.trim();
      const pattern = document.getElementById('gen-pattern').value.trim();

      btnGenerate.disabled = true;
      btnGenerate.innerHTML = '⚡ Generating...';

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ brand, count, bin_prefix, pattern })
        });
        const data = await res.json();

        if (data.cards && data.cards.length > 0) {
          currentGenerated = data.cards;
          appState.lastRecords = data.cards;
          renderGeneratedCards(data.cards, resultsContainer);
        } else {
          resultsContainer.innerHTML = '<div class="empty-state">Failed to generate cards. Check your inputs.</div>';
        }
      } catch (err) {
        resultsContainer.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
      } finally {
        btnGenerate.disabled = false;
        btnGenerate.innerHTML = '⚡ Generate Test Cards';
      }
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener('click', () => {
      if (currentGenerated.length === 0) return;
      const text = currentGenerated.map(c => c.pipe_format).join('\n');
      navigator.clipboard.writeText(text);
      btnCopy.innerText = '✅ Copied!';
      setTimeout(() => { btnCopy.innerText = '📋 Copy All'; }, 2000);
    });
  }
}

function renderGeneratedCards(cards, container) {
  container.replaceChildren();

  if (!cards || cards.length === 0) {
    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    emptyState.textContent = 'No cards generated yet. Click "Generate Test Cards" to begin.';
    container.appendChild(emptyState);
    return;
  }

  cards.forEach(c => {
    const item = document.createElement('div');
    item.className = 'card-item';

    const main = document.createElement('div');
    main.className = 'card-main';

    const pipe = document.createElement('span');
    pipe.className = 'card-pipe';
    pipe.textContent = c.pipe_format || '';

    const meta = document.createElement('span');
    meta.className = 'card-meta';
    meta.textContent = `${c.brand || 'Unknown'} • ${c.formatted || ''}`;

    main.appendChild(pipe);
    main.appendChild(meta);

    const btnCopy = document.createElement('button');
    btnCopy.className = 'btn btn-sm btn-secondary';
    btnCopy.textContent = '📋 Copy';
    btnCopy.addEventListener('click', () => {
      navigator.clipboard.writeText(c.pipe_format || '');
      btnCopy.textContent = '✅ Copied!';
      setTimeout(() => { btnCopy.textContent = '📋 Copy'; }, 2000);
    });

    item.appendChild(main);
    item.appendChild(btnCopy);
    container.appendChild(item);
  });
}

// 2. Validator Handler
function initValidator() {
  const btnCheck = document.getElementById('btn-check');
  const inputCard = document.getElementById('check-input');
  const resultsContainer = document.getElementById('check-results');

  if (btnCheck) {
    btnCheck.addEventListener('click', async () => {
      const card = inputCard.value.trim();
      if (!card) return;

      btnCheck.disabled = true;
      btnCheck.innerText = '🔍 Checking...';

      try {
        const res = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ card })
        });
        const data = await res.json();
        renderValidationResult(data, resultsContainer);
      } catch (err) {
        resultsContainer.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
      } finally {
        btnCheck.disabled = false;
        btnCheck.innerText = '🔍 Validate Card Now';
      }
    });
  }
}

function renderValidationResult(data, container) {
  container.replaceChildren();

  if (data.error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'empty-state';
    errorDiv.style.color = 'var(--danger-color)';
    errorDiv.textContent = data.error;
    container.appendChild(errorDiv);
    return;
  }

  updateStatsCounters(1, data.overall_valid ? 1 : 0, data.overall_valid ? 0 : 1);

  const badgeWrapper = document.createElement('div');
  badgeWrapper.style.marginBottom = '1rem';

  const badge = document.createElement('span');
  badge.className = `badge ${data.overall_valid ? 'badge-success' : 'badge-danger'}`;
  badge.style.fontSize = '1rem';
  badge.style.padding = '0.4rem 0.8rem';
  badge.textContent = data.status || (data.overall_valid ? 'APPROVED / PASS' : 'DECLINED / FAIL');
  badgeWrapper.appendChild(badge);

  const table = document.createElement('table');
  table.className = 'data-table';

  const rows = [
    ['Card PAN', `${data.formatted || ''} (${data.masked || ''})`],
    ['Brand Scheme', data.brand || 'Unknown'],
    ['Luhn Mod-10 Check', data.is_luhn_valid ? '✅ PASS' : '❌ FAIL'],
    ['Length Check', `${data.length || 0} digits (${data.is_length_valid ? 'Valid' : 'Invalid, expected ' + (data.expected_length || '')})`],
    ['Expiry Format', `${data.expiry || 'N/A'} (${data.is_expiry_valid ? 'Valid' : 'Invalid'})`],
    ['CVV Format', `${data.cvv || 'N/A'} (${data.is_cvv_valid ? 'Valid' : 'Invalid'})`],
    ['Issuer Bank', `${data.bin_info?.issuer || 'Unknown'} (${data.bin_info?.flag || ''} ${data.bin_info?.country || ''})`]
  ];

  rows.forEach(([label, value]) => {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = label;
    const td = document.createElement('td');
    td.textContent = value;
    tr.appendChild(th);
    tr.appendChild(td);
    table.appendChild(tr);
  });

  container.appendChild(badgeWrapper);
  container.appendChild(table);
}

// 3. BIN Lookup Handler
function initBinLookup() {
  const btnLookup = document.getElementById('btn-bin-lookup');
  const inputBin = document.getElementById('bin-input');
  const resultsContainer = document.getElementById('bin-results');

  if (btnLookup) {
    btnLookup.addEventListener('click', async () => {
      const bin = inputBin.value.trim();
      if (!bin) return;

      btnLookup.disabled = true;
      btnLookup.innerText = '🔎 Looking up...';

      try {
        const res = await fetch('/api/bin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bin })
        });
        const data = await res.json();

        resultsContainer.innerHTML = `
          <div class="bin-result-box">
            <div class="bin-prop"><span class="prop-label">BIN / IIN</span><span class="prop-value">${data.bin}</span></div>
            <div class="bin-prop"><span class="prop-label">Brand Scheme</span><span class="prop-value">${data.brand}</span></div>
            <div class="bin-prop"><span class="prop-label">Card Type</span><span class="prop-value">${data.type}</span></div>
            <div class="bin-prop"><span class="prop-label">Card Tier</span><span class="prop-value">${data.level}</span></div>
            <div class="bin-prop"><span class="prop-label">Issuer Bank</span><span class="prop-value">${data.issuer}</span></div>
            <div class="bin-prop"><span class="prop-label">Country</span><span class="prop-value">${data.flag} ${data.country}</span></div>
          </div>
        `;
      } catch (err) {
        resultsContainer.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
      } finally {
        btnLookup.disabled = false;
        btnLookup.innerText = '🔎 Lookup BIN';
      }
    });
  }
}

// 4. Bulk Checker Handler
function initBulkChecker() {
  const btnBulk = document.getElementById('btn-bulk-check');
  const inputBulk = document.getElementById('bulk-input');
  const tableContainer = document.getElementById('bulk-table-container');
  const statsSummary = document.getElementById('bulk-stats-summary');

  if (btnBulk) {
    btnBulk.addEventListener('click', async () => {
      const text = inputBulk.value.trim();
      if (!text) return;

      btnBulk.disabled = true;
      btnBulk.innerText = '🚀 Validating List...';

      try {
        const res = await fetch('/api/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cards_text: text })
        });
        const data = await res.json();

        statsSummary.style.display = 'inline-block';
        document.getElementById('bulk-total-count').innerText = data.total;
        document.getElementById('bulk-pass-count').innerText = data.passed;
        document.getElementById('bulk-fail-count').innerText = data.failed;

        renderBulkTable(data.results, tableContainer);
      } catch (err) {
        tableContainer.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
      } finally {
        btnBulk.disabled = false;
        btnBulk.innerText = '🚀 Run Bulk Validation';
      }
    });
  }
}

function renderBulkTable(results, container) {
  if (!results || results.length === 0) {
    container.innerHTML = '<div class="empty-state">No valid lines found.</div>';
    return;
  }

  const rows = results.map(r => {
    const res = r.res;
    const badgeClass = res.overall_valid ? 'badge-success' : 'badge-danger';
    return `
      <tr>
        <td>#${r.id}</td>
        <td>${res.masked}</td>
        <td>${res.brand}</td>
        <td><span class="badge ${badgeClass}">${res.status}</span></td>
        <td>${res.bin_info.issuer} (${res.bin_info.country})</td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Masked PAN</th>
          <th>Brand</th>
          <th>Verdict</th>
          <th>Issuer</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}

// 5. BIN Database Handler
async function initBinDatabase() {
  const searchInput = document.getElementById('bindb-search');
  const container = document.getElementById('bindb-table-container');

  async function loadDb(query = '') {
    try {
      const res = await fetch('/api/bindb', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      const data = await res.json();
      renderBinDbTable(data.results, container);
    } catch (err) {
      container.innerHTML = `<div class="empty-state">Error loading BIN DB: ${err.message}</div>`;
    }
  }

  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        loadDb(searchInput.value);
      }, 300);
    });
  }

  loadDb();
}

function renderBinDbTable(list, container) {
  if (!list || list.length === 0) {
    container.innerHTML = '<div class="empty-state">No BIN records match query.</div>';
    return;
  }

  const rows = list.map(item => `
    <tr>
      <td><code>${item.bin}</code></td>
      <td>${item.brand}</td>
      <td>${item.type}</td>
      <td>${item.level}</td>
      <td>${item.issuer}</td>
      <td>${item.flag} ${item.country}</td>
    </tr>
  `).join('');

  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>BIN</th>
          <th>Brand</th>
          <th>Type</th>
          <th>Tier</th>
          <th>Issuer</th>
          <th>Country</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}

// 6. Extrapolation Handler
function initExtrapolation() {
  const btnExtrap = document.getElementById('btn-extrap');
  const inputSeed = document.getElementById('extrap-seed');
  const countInput = document.getElementById('extrap-count');
  const resultsContainer = document.getElementById('extrap-results');
  const btnCopy = document.getElementById('btn-copy-extrap');

  let currentExtrapolations = [];

  if (btnExtrap) {
    btnExtrap.addEventListener('click', async () => {
      const seed = inputSeed.value.trim();
      const count = parseInt(countInput.value, 10) || 10;

      if (!seed) return;

      btnExtrap.disabled = true;
      btnExtrap.innerText = '🔮 Extrapolating...';

      try {
        const res = await fetch('/api/extrapolate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ seed, count })
        });
        const data = await res.json();

        if (data.extrapolated) {
          currentExtrapolations = data.extrapolated;
          renderGeneratedCards(data.extrapolated, resultsContainer);
        } else {
          resultsContainer.innerHTML = `<div class="empty-state">${data.error || 'Failed to extrapolate.'}</div>`;
        }
      } catch (err) {
        resultsContainer.innerHTML = `<div class="empty-state">Error: ${err.message}</div>`;
      } finally {
        btnExtrap.disabled = false;
        btnExtrap.innerText = '🔮 Extrapolate Cards';
      }
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener('click', () => {
      if (currentExtrapolations.length === 0) return;
      const text = currentExtrapolations.map(c => c.pipe_format).join('\n');
      navigator.clipboard.writeText(text);
      btnCopy.innerText = '✅ Copied!';
      setTimeout(() => { btnCopy.innerText = '📋 Copy Yield'; }, 2000);
    });
  }
}

// 7. Templates Handler
async function initTemplates() {
  const container = document.getElementById('templates-grid');
  if (!container) return;

  try {
    const res = await fetch('/api/templates');
    const data = await res.json();

    if (data.templates && Array.isArray(data.templates)) {
      container.replaceChildren();

      data.templates.forEach(t => {
        const card = document.createElement('div');
        card.className = 'template-card';

        const title = document.createElement('h3');
        title.textContent = t.name || '';

        const code = document.createElement('code');
        code.textContent = t.pattern || '';

        const desc = document.createElement('p');
        desc.textContent = t.description || '';

        card.appendChild(title);
        card.appendChild(code);
        card.appendChild(desc);

        card.addEventListener('click', () => {
          const genTab = document.querySelector('[data-tab="tab-generator"]');
          if (genTab) genTab.click();
          const patternInput = document.getElementById('gen-pattern');
          if (patternInput) patternInput.value = t.pattern || '';
        });

        container.appendChild(card);
      });
    }
  } catch (err) {
    container.replaceChildren();
    const errDiv = document.createElement('div');
    errDiv.className = 'empty-state';
    errDiv.textContent = `Error loading templates: ${err.message}`;
    container.appendChild(errDiv);
  }
}

// 8. Export Handler
function initExport() {
  const btnDownload = document.getElementById('btn-export-download');

  if (btnDownload) {
    btnDownload.addEventListener('click', async () => {
      const format = document.getElementById('export-format').value;

      // Use actual active session records if available, otherwise sample records
      const exportRecords = (appState.lastRecords && appState.lastRecords.length > 0)
        ? appState.lastRecords
        : [
            { pan: '4000161234567890', brand: 'Visa', expiry: '12/28', cvv: '123', status: 'PASS' },
            { pan: '5156761234567890', brand: 'Mastercard', expiry: '05/29', cvv: '456', status: 'PASS' },
            { pan: '3400051234567890', brand: 'Amex', expiry: '10/27', cvv: '1234', status: 'PASS' }
          ];

      try {
        const res = await fetch('/api/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ records: exportRecords, format })
        });
        const data = await res.json();

        if (data.content) {
          // Trigger file download
          const blob = new Blob([data.content], { type: data.mime_type });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = data.filename;
          a.click();
          window.URL.revokeObjectURL(url);
        } else {
          alert('Export error: ' + (data.error || 'Failed to generate export file'));
        }
      } catch (err) {
        alert('Export failed: ' + err.message);
      }
    });
  }
}

// 9. Settings Handler
function initSettings() {
  const btnSave = document.getElementById('btn-save-settings');
  const brandSelect = document.getElementById('setting-default-brand');
  const threadsSelect = document.getElementById('setting-threads');
  const maskCheckbox = document.getElementById('setting-mask-output');

  // Load saved settings from localStorage
  const savedSettings = localStorage.getItem('cardx_settings');
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings);
      if (parsed.default_brand && brandSelect) brandSelect.value = parsed.default_brand;
      if (parsed.threads && threadsSelect) threadsSelect.value = parsed.threads;
      if (typeof parsed.mask === 'boolean' && maskCheckbox) maskCheckbox.checked = parsed.mask;
    } catch (e) {
      console.error('Failed to parse saved settings:', e);
    }
  }

  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      const default_brand = brandSelect ? brandSelect.value : 'Visa';
      const threads = threadsSelect ? threadsSelect.value : '8';
      const mask = maskCheckbox ? maskCheckbox.checked : true;

      const payload = { default_brand, threads, mask };

      try {
        localStorage.setItem('cardx_settings', JSON.stringify(payload));
        await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        btnSave.innerText = '✅ Settings Saved!';
        setTimeout(() => { btnSave.innerText = '💾 Save Configuration'; }, 2000);
      } catch (err) {
        alert('Failed to save settings: ' + err.message);
      }
    });
  }
}

// 10. Telegram Bot Webhook Tester
function initTelegram() {
  const btnTest = document.getElementById('btn-test-tg');
  const inputCmd = document.getElementById('tg-cmd-input');
  const boxOutput = document.getElementById('tg-response-box');

  if (btnTest) {
    btnTest.addEventListener('click', async () => {
      const text = inputCmd.value.trim();
      if (!text) return;

      btnTest.disabled = true;
      btnTest.innerText = '🚀 Sending Payload...';

      try {
        const payload = {
          update_id: 10001,
          message: {
            message_id: 1,
            chat: { id: 999888, type: 'private' },
            text: text
          }
        };

        const res = await fetch('/api/webhook', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        boxOutput.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        boxOutput.innerText = `Error: ${err.message}`;
      } finally {
        btnTest.disabled = false;
        btnTest.innerText = '🚀 Send Test Webhook Message';
      }
    });
  }
}
