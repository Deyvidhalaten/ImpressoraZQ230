/**
 * BistekPrinter - Admin Application
 * Gerenciamento de impressoras e configurações
 */

// Se estamos acessando pela porta 8000 (servidor Flask), usamos /api relativo
// Caso contrário (Live Server, etc), usamos URL absoluta
const API_BASE = window.location.port === '8000'
    ? '/api'
    : 'http://localhost:8000/api';

const state = {
    loja: null,
    printers: [],
    allPrinters: [],
    selectedPrinter: null
};

const elements = {
    printerAdminSelect: document.getElementById('printerAdminSelect'),
    lsFlor: document.getElementById('lsFlor'),
    lsFlv: document.getElementById('lsFlv'),
    lsForm: document.getElementById('lsForm'),
    printersTableBody: document.getElementById('printersTableBody'),
    addPrinterForm: document.getElementById('addPrinterForm'),
    toastContainer: document.getElementById('toastContainer')
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

        renderPrinterSelect();
        renderPrintersTable();
    } catch (error) {
        showToast('error', 'Erro', 'Falha ao carregar dados');
    }
}

// Fetch all printers (admin only)
async function fetchAllPrinters() {
    try {
        const response = await fetch(`${API_BASE}/printers`);
        if (response.ok) {
            state.allPrinters = await response.json();
            renderPrintersTable();
        }
    } catch (error) {
        console.error('Erro ao buscar impressoras:', error);
    }
}

// Render printer select
function renderPrinterSelect() {
    elements.printerAdminSelect.innerHTML = state.printers.map(p => `
        <option value="${p.ip}">${p.nome || p.ip} - ${p.funcao.join(', ')}</option>
    `).join('');

    if (state.printers.length > 0) {
        state.selectedPrinter = state.printers[0];
        elements.lsFlor.value = state.selectedPrinter.ls_flor || 0;
        elements.lsFlv.value = state.selectedPrinter.ls_flv || 0;
    }

    elements.printerAdminSelect.addEventListener('change', (e) => {
        state.selectedPrinter = state.printers.find(p => p.ip === e.target.value);
        if (state.selectedPrinter) {
            elements.lsFlor.value = state.selectedPrinter.ls_flor || 0;
            elements.lsFlv.value = state.selectedPrinter.ls_flv || 0;
        }
    });
}

// Render printers table
function renderPrintersTable() {
    const printers = state.allPrinters.length > 0 ? state.allPrinters : state.printers;

    elements.printersTableBody.innerHTML = printers.map(p => `
        <tr>
            <td>${p.loja || '--'}</td>
            <td>${p.nome || '--'}</td>
            <td>${Array.isArray(p.funcao) ? p.funcao.join(', ') : p.funcao}</td>
            <td>${p.ls_flor || 0}</td>
            <td>${p.ls_flv || 0}</td>
            <td>
                <button class="btn btn-small btn-danger" onclick="deletePrinter('${p.ip}', '${p.pattern || ''}')">
                    🗑️
                </button>
            </td>
        </tr>
    `).join('');
}

// Save LS config
elements.lsForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!state.selectedPrinter) {
        showToast('warning', 'Atenção', 'Selecione uma impressora');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/printers/ls`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                loja: state.loja,
                ip: state.selectedPrinter.ip,
                ls_flor: parseInt(elements.lsFlor.value),
                ls_flv: parseInt(elements.lsFlv.value)
            })
        });

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

    try {
        const response = await fetch(`${API_BASE}/printers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                loja: document.getElementById('newLoja').value,
                nome: document.getElementById('newNome').value,
                ip: document.getElementById('newIp').value,
                funcao: funcao,
                ls_flor: parseInt(document.getElementById('newLsFlor').value),
                ls_flv: parseInt(document.getElementById('newLsFlv').value)
            })
        });

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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip, pattern })
        });

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
document.addEventListener('DOMContentLoaded', () => {
    fetchContext();
    fetchAllPrinters();
});
