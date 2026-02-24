/**
 * BistekPrinter - Admin Application
 * Gerenciamento de impressoras e configurações
 */

// Se estamos acessando pela porta 8000 (servidor Flask), usamos /api relativo
// Caso contrário (Live Server, etc), usamos URL absoluta
const API_BASE = window.location.port === '8000'
    ? '/api'
    : 'http://localhost:8000/api';

// --- Auth Verification ---
const token = localStorage.getItem('adminToken');
if (!token) {
    window.location.href = 'login.html';
}

const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
};

function handleAuthError(response) {
    if (response.status === 401) {
        localStorage.removeItem('adminToken');
        window.location.href = 'login.html';
        return true;
    }
    return false;
}
// -------------------------

const state = {
    loja: null,
    printers: [],
    allPrinters: [],
    selectedPrinter: null
};

const elements = {
    printerAdminSelect: document.getElementById('printerAdminSelect'),
    lsInputsContainer: document.getElementById('lsInputsContainer'),
    lsForm: document.getElementById('lsForm'),
    printersTableBody: document.getElementById('printersTableBody'),
    addPrinterForm: document.getElementById('addPrinterForm'),
    newFuncaoSelect: document.getElementById('newFuncao'),
    newLsInputsContainer: document.getElementById('newLsInputsContainer'),
    toastContainer: document.getElementById('toastContainer'),
    editFuncaoSelect: document.getElementById('editFuncao')
};

// Toast
function showToast(type, title, message) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

// Fetch context
async function fetchContext() {
    try {
        const response = await fetch(`${API_BASE}/context`);
        const data = await response.json();

        state.loja = data.loja;
        state.printers = data.printers;
        state.modos = data.modos; // [{key: 'flv', label: 'Flv'}, ...]

        renderPrinterSelect();
        renderNewFuncaoOptions();
    } catch (error) {
        showToast('error', 'Erro', 'Falha ao carregar dados do Contexto: ' + error.message);
        throw error;
    }
}

function renderNewFuncaoOptions() {
    if (!state.modos) return;
    elements.newFuncaoSelect.innerHTML = state.modos.map(m =>
        `<option value="${m.key}">${m.label}</option>`
    ).join('');

    // Atualiza os inputs criados dinamicamente ao selecionar funções
    elements.newFuncaoSelect.addEventListener('change', () => {
        const funcoesSelecionadas = Array.from(elements.newFuncaoSelect.selectedOptions).map(opt => opt.value);
        elements.newLsInputsContainer.innerHTML = funcoesSelecionadas.map(func => {
            const modoInfo = state.modos.find(m => m.key === func);
            return `
                <div class="form-group" style="padding: 0 0.5rem; flex: 1; min-width: 120px;">
                    <label class="form-label">LS ${modoInfo ? modoInfo.label : func}</label>
                    <input type="number" class="form-input ls-new-input" data-modo="${func}" value="0">
                </div>
            `;
        }).join('');
    });
}

// Fetch all printers (admin only)
async function fetchAllPrinters() {
    try {
        const response = await fetch(`${API_BASE}/printers`);
        if (response.ok) {
            state.allPrinters = await response.json();
            if (state.modos) { // Só renderiza a tabela se modos já estiver populado
                renderPrintersTable();
            }
        }
    } catch (error) {
        console.error('Erro ao buscar impressoras:', error);
        showToast('error', 'Erro', 'Falha ao buscar Impressoras (All): ' + error.message);
        throw error;
    }
}

function renderDynamicLsInputs(rebuildingInputsOnly = false) {
    if (!state.selectedPrinter || !state.modos) return;

    // Mostra inputs para todas as funções que a impressora selecionada possui
    const permissoesPrinter = state.selectedPrinter.funcao || [];
    const objLs = state.selectedPrinter.ls || {};

    if (!rebuildingInputsOnly && elements.editFuncaoSelect) {
        elements.editFuncaoSelect.innerHTML = state.modos.map(m => {
            const isSelected = permissoesPrinter.includes(m.key) ? 'selected' : '';
            return `<option value="${m.key}" ${isSelected}>${m.label}</option>`;
        }).join('');
    }

    elements.lsInputsContainer.innerHTML = permissoesPrinter.map(func => {
        const valorAtual = objLs[func] !== undefined ? objLs[func] : 0;
        const modoInfo = state.modos.find(m => m.key === func);
        const label = modoInfo ? modoInfo.label : func;

        return `
            <div class="form-group" style="padding: 0 0.5rem; flex: 1; min-width: 120px;">
                <label class="form-label">LS ${label}</label>
                <input type="number" class="form-input ls-edit-input" data-modo="${func}" value="${valorAtual}">
            </div>
        `;
    }).join('');

    if (permissoesPrinter.length === 0) {
        elements.lsInputsContainer.innerHTML = '<p style="color:var(--text-secondary); width: 100%; text-align: center; margin-top: 1rem;">Nenhuma função habilitada nesta impressora. Adicione uma função acima.</p>';
    }
}

// Quando o admin clica nas funcoes na hora da edicao, refaz os quadrados de ls:
if (elements.editFuncaoSelect) {
    elements.editFuncaoSelect.addEventListener('change', () => {
        if (!state.selectedPrinter) return;

        // Save current LS values so they aren't lost when adding/removing functions
        document.querySelectorAll('.ls-edit-input').forEach(input => {
            if (!state.selectedPrinter.ls) state.selectedPrinter.ls = {};
            state.selectedPrinter.ls[input.dataset.modo] = parseInt(input.value) || 0;
        });

        // Update selected functions
        const funcoesSelecionadas = Array.from(elements.editFuncaoSelect.selectedOptions).map(opt => opt.value);
        state.selectedPrinter.funcao = funcoesSelecionadas;

        // Re-render only the inputs, not the selector
        renderDynamicLsInputs(true);
    });
}

// Render printer select
function renderPrinterSelect() {
    elements.printerAdminSelect.innerHTML = state.printers.map(p => `
        <option value="${p.ip}">${p.nome || p.ip} - ${(p.funcao || []).join(', ')}</option>
    `).join('');

    if (state.printers.length > 0) {
        state.selectedPrinter = state.printers[0];
        renderDynamicLsInputs();
    }

    elements.printerAdminSelect.addEventListener('change', (e) => {
        state.selectedPrinter = state.printers.find(p => p.ip === e.target.value);
        if (state.selectedPrinter) {
            renderDynamicLsInputs();
        }
    });
}

// Render printers table
function renderPrintersTable() {
    const printers = state.allPrinters.length > 0 ? state.allPrinters : state.printers;

    elements.printersTableBody.innerHTML = printers.map(p => {
        const lsKeys = Object.keys(p.ls || {});
        let lsFormatado = '--';
        if (lsKeys.length > 0) {
            lsFormatado = lsKeys.map(k => `${k}: ${p.ls[k]}`).join('<br>');
        }

        return `
        <tr>
            <td>${p.loja || '--'}</td>
            <td>${p.nome || '--'}</td>
            <td>${Array.isArray(p.funcao) ? p.funcao.join(', ') : p.funcao}</td>
            <td style="font-size: 0.85em; color: var(--text-secondary);">${lsFormatado}</td>
            <td>
                <button class="btn btn-small btn-danger" onclick="deletePrinter('${p.ip}', '${p.pattern || ''}')">
                    🗑️
                </button>
            </td>
        </tr>
    `}).join('');
}

// Save LS config
elements.lsForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!state.selectedPrinter) {
        showToast('warning', 'Atenção', 'Selecione uma impressora');
        return;
    }

    try {
        const lsObject = {};
        document.querySelectorAll('.ls-edit-input').forEach(input => {
            lsObject[input.dataset.modo] = parseInt(input.value) || 0;
        });

        const funcao = Array.from(elements.editFuncaoSelect.selectedOptions).map(opt => opt.value);

        const response = await fetch(`${API_BASE}/printers/ls`, {
            method: 'PUT',
            headers: authHeaders,
            body: JSON.stringify({
                loja: state.loja,
                ip: state.selectedPrinter.ip,
                ls: lsObject,
                funcao: funcao
            })
        });

        if (handleAuthError(response)) return;

        const data = await response.json();

        if (data.success) {
            showToast('success', 'Salvo!', 'Configurações de LS atualizadas');
            fetchContext();
        } else {
            showToast('error', 'Erro', data.error || 'Falha ao salvar');
        }
    } catch (error) {
        showToast('error', 'Erro', 'Falha na comunicação');
    }
});

// Add printer
elements.addPrinterForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const funcaoSelect = document.getElementById('newFuncao');
    const funcao = Array.from(funcaoSelect.selectedOptions).map(opt => opt.value);

    const lsObject = {};
    document.querySelectorAll('.ls-new-input').forEach(input => {
        lsObject[input.dataset.modo] = parseInt(input.value) || 0;
    });

    try {
        const newPrinter = {
            loja: document.getElementById('newLoja').value,
            nome: document.getElementById('newNome').value,
            ip: document.getElementById('newIp').value,
            funcao: funcao,
            ls: lsObject
        };

        const response = await fetch(`${API_BASE}/printers`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(newPrinter)
        });

        if (handleAuthError(response)) return;

        const data = await response.json();

        if (data.success) {
            showToast('success', 'Adicionada!', 'Impressora cadastrada com sucesso');
            elements.addPrinterForm.reset();
            fetchAllPrinters();
        } else {
            showToast('error', 'Erro', data.error || 'Falha ao adicionar');
        }
    } catch (error) {
        showToast('error', 'Erro', 'Falha na comunicação');
    }
});

// Delete printer
async function deletePrinter(ip, pattern) {
    if (!confirm('Confirma exclusão desta impressora?')) return;

    try {
        const response = await fetch(`${API_BASE}/printers`, {
            method: 'DELETE',
            headers: authHeaders,
            body: JSON.stringify({ ip, pattern })
        });

        if (handleAuthError(response)) return;

        const data = await response.json();

        if (data.success) {
            showToast('success', 'Excluída!', 'Impressora removida');
            fetchAllPrinters();
        } else {
            showToast('error', 'Erro', data.error || 'Falha ao excluir');
        }
    } catch (error) {
        showToast('error', 'Erro', 'Falha na comunicação');
    }
}

// Init
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Garante primeiro o carregamento de context (loja, modos)
        await fetchContext();
        // Em seguida roda o getAll para não quebrar tabelas
        await fetchAllPrinters();
    } catch (err) {
        alert("Erro fatal na inicialização do Admin: " + err.message + "\nStack: " + err.stack);
    }
});
