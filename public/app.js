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
window.appState = appState;

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
          addSessionRecords(data.cards);
          renderGeneratedCards(data.cards, resultsContainer);
        } else {
          resultsContainer.replaceChildren();
          const emptyState = document.createElement('div');
          emptyState.className = 'empty-state';
          emptyState.textContent = 'Failed to generate cards. Check your inputs.';
          resultsContainer.appendChild(emptyState);
        }
      } catch (err) {
        resultsContainer.replaceChildren();
        const errDiv = document.createElement('div');
        errDiv.className = 'empty-state';
        errDiv.textContent = `Error: ${err.message}`;
        resultsContainer.appendChild(errDiv);
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

// Helper: Append record to appState.lastRecords
function addSessionRecord(record) {
  if (!record) return;
  appState.lastRecords.push(record);
}

function addSessionRecords(records) {
  if (Array.isArray(records)) {
    records.forEach(r => addSessionRecord(r));
  }
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
        if (!data.error && data.pan) {
          addSessionRecord(data);
        }
        renderValidationResult(data, resultsContainer);
      } catch (err) {
        resultsContainer.replaceChildren();
        const errDiv = document.createElement('div');
        errDiv.className = 'empty-state';
        errDiv.textContent = `Error: ${err.message}`;
        resultsContainer.appendChild(errDiv);
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

  const displayPan = appState.settings.mask ? (data.masked || (data.pan ? `${data.pan.slice(0, 6)}xxxxxx${data.pan.slice(-4)}` : '')) : (data.formatted || data.pan);
  const rows = [
    ['Card PAN', displayPan],
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

        renderBinLookupResult(data, resultsContainer);
      } catch (err) {
        resultsContainer.replaceChildren();
        const errDiv = document.createElement('div');
        errDiv.className = 'empty-state';
        errDiv.textContent = `Error: ${err.message}`;
        resultsContainer.appendChild(errDiv);
      } finally {
        btnLookup.disabled = false;
        btnLookup.innerText = '🔎 Lookup BIN';
      }
    });
  }
}

function renderBinLookupResult(data, container) {
  container.replaceChildren();

  if (data.error) {
    const errDiv = document.createElement('div');
    errDiv.className = 'empty-state';
    errDiv.textContent = data.error;
    container.appendChild(errDiv);
    return;
  }

  const box = document.createElement('div');
  box.className = 'bin-result-box';

  const props = [
    ['BIN / IIN', data.bin || 'N/A'],
    ['Brand Scheme', data.brand || 'N/A'],
    ['Card Type', data.type || 'N/A'],
    ['Card Tier', data.level || 'N/A'],
    ['Issuer Bank', data.issuer || 'N/A'],
    ['Country', `${data.flag || ''} ${data.country || ''}`.trim()]
  ];

  props.forEach(([label, val]) => {
    const propDiv = document.createElement('div');
    propDiv.className = 'bin-prop';

    const lblSpan = document.createElement('span');
    lblSpan.className = 'prop-label';
    lblSpan.textContent = label;

    const valSpan = document.createElement('span');
    valSpan.className = 'prop-value';
    valSpan.textContent = val;

    propDiv.appendChild(lblSpan);
    propDiv.appendChild(valSpan);
    box.appendChild(propDiv);
  });

  container.appendChild(box);
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

      const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
      if (lines.length === 0) return;

      const workerCount = Math.max(1, parseInt(appState.settings.threads, 10) || 8);
      btnBulk.disabled = true;
      btnBulk.innerText = `🚀 Validating List (${workerCount} Workers)...`;

      try {
        // Divide input lines into parallel worker chunk batches
        const chunkSize = Math.max(1, Math.ceil(lines.length / workerCount));
        const chunks = [];
        for (let i = 0; i < lines.length; i += chunkSize) {
          chunks.push(lines.slice(i, i + chunkSize));
        }

        // Dispatch concurrent API worker requests using Promise.all
        const workerPromises = chunks.map(chunkLines =>
          fetch('/api/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cards_text: chunkLines.join('\n') })
          }).then(r => r.json())
        );

        const chunkResponses = await Promise.all(workerPromises);

        // Aggregate chunk results
        let totalCount = 0;
        let passCount = 0;
        let failCount = 0;
        const mergedResults = [];

        chunkResponses.forEach(data => {
          totalCount += data.total || 0;
          passCount += data.passed || 0;
          failCount += data.failed || 0;
          if (data.results && Array.isArray(data.results)) {
            data.results.forEach(r => {
              mergedResults.push({
                id: mergedResults.length + 1,
                input: r.input,
                res: r.res
              });
            });
          }
        });

        statsSummary.style.display = 'inline-block';
        document.getElementById('bulk-total-count').textContent = totalCount;
        document.getElementById('bulk-pass-count').textContent = passCount;
        document.getElementById('bulk-fail-count').textContent = failCount;

        const bulkRecords = mergedResults.map(r => r.res).filter(Boolean);
        addSessionRecords(bulkRecords);

        renderBulkTable(mergedResults, tableContainer);
      } catch (err) {
        tableContainer.replaceChildren();
        const errDiv = document.createElement('div');
        errDiv.className = 'empty-state';
        errDiv.textContent = `Error: ${err.message}`;
        tableContainer.appendChild(errDiv);
      } finally {
        btnBulk.disabled = false;
        btnBulk.innerText = '🚀 Run Bulk Validation';
      }
    });
  }
}

function renderBulkTable(results, container) {
  container.replaceChildren();

  if (!results || results.length === 0) {
    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    emptyState.textContent = 'No valid lines found.';
    container.appendChild(emptyState);
    return;
  }

  const table = document.createElement('table');
  table.className = 'data-table';

  const thead = document.createElement('thead');
  const trHead = document.createElement('tr');
  ['#', 'Masked PAN', 'Brand', 'Verdict', 'Issuer'].forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    trHead.appendChild(th);
  });
  thead.appendChild(trHead);

  const tbody = document.createElement('tbody');
  results.forEach(r => {
    const res = r.res || {};
    const tr = document.createElement('tr');

    const tdId = document.createElement('td');
    tdId.textContent = `#${r.id || ''}`;

    const tdPan = document.createElement('td');
    tdPan.textContent = appState.settings.mask ? (res.masked || mask_pan(res.pan)) : (res.formatted || res.pan);

    const tdBrand = document.createElement('td');
    tdBrand.textContent = res.brand || 'Unknown';

    const tdVerdict = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `badge ${res.overall_valid ? 'badge-success' : 'badge-danger'}`;
    badge.textContent = res.status || (res.overall_valid ? 'PASS' : 'FAIL');
    tdVerdict.appendChild(badge);

    const tdIssuer = document.createElement('td');
    const issuer = res.bin_info?.issuer || 'Unknown';
    const country = res.bin_info?.country || '';
    tdIssuer.textContent = country ? `${issuer} (${country})` : issuer;

    tr.appendChild(tdId);
    tr.appendChild(tdPan);
    tr.appendChild(tdBrand);
    tr.appendChild(tdVerdict);
    tr.appendChild(tdIssuer);

    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
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
      container.replaceChildren();
      const errDiv = document.createElement('div');
      errDiv.className = 'empty-state';
      errDiv.textContent = `Error loading BIN DB: ${err.message}`;
      container.appendChild(errDiv);
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
  container.replaceChildren();

  if (!list || list.length === 0) {
    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    emptyState.textContent = 'No BIN records match query.';
    container.appendChild(emptyState);
    return;
  }

  const table = document.createElement('table');
  table.className = 'data-table';

  const thead = document.createElement('thead');
  const trHead = document.createElement('tr');
  ['BIN', 'Brand', 'Type', 'Tier', 'Issuer', 'Country'].forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    trHead.appendChild(th);
  });
  thead.appendChild(trHead);

  const tbody = document.createElement('tbody');
  list.forEach(item => {
    const tr = document.createElement('tr');

    const tdBin = document.createElement('td');
    const code = document.createElement('code');
    code.textContent = item.bin || '';
    tdBin.appendChild(code);

    const tdBrand = document.createElement('td');
    tdBrand.textContent = item.brand || '';

    const tdType = document.createElement('td');
    tdType.textContent = item.type || '';

    const tdLevel = document.createElement('td');
    tdLevel.textContent = item.level || '';

    const tdIssuer = document.createElement('td');
    tdIssuer.textContent = item.issuer || '';

    const tdCountry = document.createElement('td');
    tdCountry.textContent = `${item.flag || ''} ${item.country || ''}`.trim();

    tr.appendChild(tdBin);
    tr.appendChild(tdBrand);
    tr.appendChild(tdType);
    tr.appendChild(tdLevel);
    tr.appendChild(tdIssuer);
    tr.appendChild(tdCountry);

    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
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

        if (data.extrapolated && Array.isArray(data.extrapolated)) {
          currentExtrapolations = data.extrapolated;
          addSessionRecords(data.extrapolated);
          renderGeneratedCards(data.extrapolated, resultsContainer);
        } else {
          resultsContainer.replaceChildren();
          const errDiv = document.createElement('div');
          errDiv.className = 'empty-state';
          errDiv.textContent = data.error || 'Failed to extrapolate.';
          resultsContainer.appendChild(errDiv);
        }
      } catch (err) {
        resultsContainer.replaceChildren();
        const errDiv = document.createElement('div');
        errDiv.className = 'empty-state';
        errDiv.textContent = `Error: ${err.message}`;
        resultsContainer.appendChild(errDiv);
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

      if (!appState.lastRecords || appState.lastRecords.length === 0) {
        alert('No active session records found to export. Please generate or validate cards first.');
        return;
      }

      try {
        const res = await fetch('/api/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ records: appState.lastRecords, format })
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
  const genBrandSelect = document.getElementById('gen-brand');

  function applySettingsToUi(settings) {
    if (settings.default_brand) {
      appState.settings.defaultBrand = settings.default_brand;
      if (genBrandSelect) genBrandSelect.value = settings.default_brand;
    }
    if (settings.threads) {
      appState.settings.threads = parseInt(settings.threads, 10) || 8;
    }
    if (typeof settings.mask === 'boolean') {
      appState.settings.mask = settings.mask;
    }
  }

  // Load saved settings from localStorage
  const savedSettings = localStorage.getItem('cardx_settings');
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings);
      if (parsed.default_brand && brandSelect) brandSelect.value = parsed.default_brand;
      if (parsed.threads && threadsSelect) threadsSelect.value = parsed.threads;
      if (typeof parsed.mask === 'boolean' && maskCheckbox) maskCheckbox.checked = parsed.mask;
      applySettingsToUi(parsed);
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

      // Save in browser localStorage immediately and apply to UI state
      localStorage.setItem('cardx_settings', JSON.stringify(payload));
      applySettingsToUi(payload);

      try {
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          btnSave.innerText = '✅ Settings Saved in Browser!';
          setTimeout(() => { btnSave.innerText = '💾 Save Configuration'; }, 2000);
        } else {
          btnSave.innerText = '✅ Settings Saved in Browser!';
          setTimeout(() => { btnSave.innerText = '💾 Save Configuration'; }, 2000);
        }
      } catch (err) {
        btnSave.innerText = '✅ Settings Saved in Browser!';
        setTimeout(() => { btnSave.innerText = '💾 Save Configuration'; }, 2000);
        console.warn('Server settings sync failed, saved locally:', err.message);
      }
    });
  }
}

// 10. Telegram Bot Webhook Tester
function initTelegram() {
  const btnTest = document.getElementById('btn-test-tg');
  const inputCmd = document.getElementById('tg-cmd-input');
  const inputSender = document.getElementById('tg-sender-input');
  const inputSecret = document.getElementById('tg-secret-input');
  const boxOutput = document.getElementById('tg-response-box');

  if (btnTest) {
    btnTest.addEventListener('click', async () => {
      const text = inputCmd.value.trim();
      if (!text) return;

      btnTest.disabled = true;
      btnTest.innerText = '🚀 Sending Payload...';

      const senderVal = (inputSender && inputSender.value.trim()) ? inputSender.value.trim() : '999888';
      const senderId = /^\d+$/.test(senderVal) ? parseInt(senderVal, 10) : senderVal;

      try {
        const payload = {
          update_id: 10001,
          message: {
            message_id: 1,
            from: { id: senderId, is_bot: false, first_name: 'Tester' },
            chat: { id: 999888, type: 'private' },
            text: text
          }
        };

        const headers = { 'Content-Type': 'application/json' };
        if (inputSecret && inputSecret.value.trim()) {
          headers['X-Telegram-Bot-Api-Secret-Token'] = inputSecret.value.trim();
        }

        const res = await fetch('/api/webhook', {
          method: 'POST',
          headers,
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
