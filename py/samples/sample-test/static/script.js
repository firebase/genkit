const API_BASE = '/api';

// State
let currentState = {
    scenarios: [],
    models: [],
    selectedScenarioId: null,
    selectedModel: null,
    stats: { pass: 0, fail: 0 }
};

// DOM Elements
const els = {
    samplesList: document.getElementById('samples-list'),
    currentScenarioTitle: document.getElementById('current-scenario-title'),
    modelCount: document.getElementById('model-count'),
    modelSelect: document.getElementById('model-select'),
    paramConfig: document.getElementById('param-config'),
    systemPrompt: document.getElementById('system-prompt'),
    userPrompt: document.getElementById('user-prompt'),
    runBtn: document.getElementById('run-btn'),
    resultsList: document.getElementById('results-list'),
    statsBar: document.getElementById('stats-bar'),
    passCount: document.getElementById('pass-count'),
    failCount: document.getElementById('fail-count')
};

// Init
async function init() {
    try {
        const scenarios = await fetchAPI('/scenarios');
        currentState.scenarios = scenarios;
        renderScenariosList();

        // Select first by default
        if (scenarios.length > 0) {
            selectScenario(scenarios[0].id);
        }
    } catch (e) {
        console.error('Failed to init:', e);
        els.samplesList.innerHTML = `<div class="nav-item error">Failed to load samples</div>`;
    }
}

// Actions
async function selectScenario(id) {
    currentState.selectedScenarioId = id;
    const scenario = currentState.scenarios.find(s => s.id === id);

    // Update UI
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.id === id);
    });

    els.currentScenarioTitle.textContent = scenario.name;
    els.systemPrompt.value = scenario.system_prompt;
    els.userPrompt.value = scenario.user_prompt;

    await loadModels(id);
}

async function loadModels(scenarioId) {
    els.modelSelect.innerHTML = '<option>Loading models...</option>';
    els.modelSelect.disabled = true;

    try {
        const models = await fetchAPI(`/models?scenario=${scenarioId}`);
        currentState.models = models;

        els.modelCount.textContent = `${models.length} Models`;

        // Render Select
        els.modelSelect.innerHTML = models.length ?
            models.map(m => `<option value="${m.name}">${m.name}</option>`).join('') :
            '<option value="">No models found</option>';

        els.modelSelect.disabled = false;

        // Trigger select change to load params
        if (models.length > 0) {
            handleModelChange(models[0].name);
        } else {
            els.paramConfig.innerHTML = '';
        }
    } catch (e) {
        console.error('Failed to load models:', e);
        els.modelSelect.innerHTML = '<option>Error loading models</option>';
    }
}

function handleModelChange(modelName) {
    const model = currentState.models.find(m => m.name === modelName);
    currentState.selectedModel = model;

    renderParams(model.params);
}

function renderParams(params) {
    if (!params || Object.keys(params).length === 0) {
        els.paramConfig.innerHTML = '<div class="empty-params">No configurable parameters</div>';
        return;
    }

    let html = '<h3>Configuration</h3>';

    for (const [key, config] of Object.entries(params)) {
        html += `<div class="form-group">
            <label>${key}</label>`;

        if (config.enum) {
            html += `<select class="config-input" data-key="${key}" data-type="${config.type}">
                ${config.enum.map(val => `<option value="${val}">${val}</option>`).join('')}
            </select>`;
        } else if (config.type === 'boolean') {
            html += `<select class="config-input" data-key="${key}" data-type="boolean">
                <option value="true">True</option>
                <option value="false">False</option>
            </select>`;
        } else if (config.type === 'number') {
            const min = config.minimum !== undefined ? `min="${config.minimum}"` : '';
            const max = config.maximum !== undefined ? `max="${config.maximum}"` : '';
            const step = (config.maximum - config.minimum) <= 1 ? '0.1' : '1';
            const val = config.default !== undefined ? config.default :
                (config.minimum !== undefined ? config.minimum : 0);

            html += `<input type="number" class="config-input" data-key="${key}" 
                     data-type="number" value="${val}" ${min} ${max} step="${step}">`;
        } else {
            // Default text
            html += `<input type="text" class="config-input" data-key="${key}" 
                      data-type="string" value="${config.default || ''}">`;
        }

        html += `</div>`;
    }

    els.paramConfig.innerHTML = html;
}

async function runTest() {
    if (!currentState.selectedModel) return;

    els.runBtn.disabled = true;
    els.runBtn.textContent = 'Running...';

    // Collect Config
    const config = {};
    document.querySelectorAll('.config-input').forEach(input => {
        const key = input.dataset.key;
        const type = input.dataset.type;
        let value = input.value;

        if (type === 'number') value = parseFloat(value);
        if (type === 'boolean') value = value === 'true';

        config[key] = value;
    });

    try {
        const result = await fetchAPI('/run', 'POST', {
            model: currentState.selectedModel.name,
            config: config,
            scenario_id: currentState.selectedScenarioId,
            user_prompt: els.userPrompt.value,
            system_prompt: els.systemPrompt.value
        });

        addResultCard(result);
        updateStats(result.success);

    } catch (e) {
        console.error(e);
        addResultCard({ success: false, error: e.message, timing: 0 });
        updateStats(false);
    } finally {
        els.runBtn.disabled = false;
        els.runBtn.textContent = 'Run Test';
    }
}

// Helpers
async function fetchAPI(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(API_BASE + endpoint, options);
    if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
    return await res.json();
}

function renderScenariosList() {
    els.samplesList.innerHTML = currentState.scenarios.map(s =>
        `<div class="nav-item" data-id="${s.id}" onclick="selectScenario('${s.id}')">
            ${s.name}
        </div>`
    ).join('');
}

function addResultCard(result) {
    const card = document.createElement('div');
    card.className = `result-card ${result.success ? 'success' : 'error'}`;

    card.innerHTML = `
        <div class="result-meta">
            <span class="model-name">${currentState.selectedModel.name}</span>
            <span class="timing">${result.timing}s</span>
        </div>
        <div class="result-content">${result.success ? escapeHtml(result.response) : result.error}</div>
    `;

    els.resultsList.prepend(card);

    // Clear empty state
    const empty = els.resultsList.querySelector('.empty-state');
    if (empty) empty.remove();
}

function updateStats(success) {
    if (success) currentState.stats.pass++;
    else currentState.stats.fail++;

    els.passCount.textContent = currentState.stats.pass;
    els.failCount.textContent = currentState.stats.fail;
    els.statsBar.classList.remove('hidden');
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Event Listeners
els.modelSelect.addEventListener('change', (e) => handleModelChange(e.target.value));
els.runBtn.addEventListener('click', runTest);

// Start
init();
