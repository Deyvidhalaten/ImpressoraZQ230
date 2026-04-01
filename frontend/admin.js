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

function parseJwt(token) {
    try {
        // itsdangerous usa o payload base64 no índice 0 (Token gerado pelo Flask/auth_service)
        const base64Url = token.split('.')[0];
        let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        
        // Adicionando padding obrigatório para o atob() do Javascript funcionar
        while (base64.length % 4) {
            base64 += '=';
        }

        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

const currentUser = parseJwt(token);
if (!currentUser) {
    localStorage.removeItem('adminToken');
    window.location.href = 'login.html';
}

const currentUserLevel = parseInt(currentUser.nivel) || 1;
document.getElementById('userLevelBadge').textContent = currentUserLevel;

// Exibir abas apenas se permitido
if (currentUserLevel >= 2) {
    document.getElementById('tabUsers').style.display = 'inline-block';
}
if (currentUserLevel >= 3) {
    document.getElementById('tabTemplates').style.display = 'inline-block';
    document.getElementById('optNivel3').style.display = 'block';
    document.getElementById('tabAudit').style.display = 'inline-block';
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

async function shutdownSystem() {
    if (!confirm('ATENÇÃO: Isso desligará o serviço de impressão. Tem certeza absoluta?')) return;
    try {
        const response = await fetch(`${API_BASE}/shutdown`, {
            method: 'POST',
            headers: authHeaders
        });
        if (handleAuthError(response)) return;
        const data = await response.json();
        showToast('info', 'Encerrando', data.message || 'Desligando sistema...');
        setTimeout(() => {
            alert("Sistema foi desligado. Você precisará subí-lo manualmente ou via Serviço Windows.");
            window.location.href = 'index.html'; // Tenta redirecionar
        }, 3000);
    } catch (e) {
        showToast('error', 'Ops', 'Falha ao contatar servidor de desligamento.');
    }
}
// -------------------------

const state = {
    loja: null,
    printers: [],
    allPrinters: [],
    selectedPrinter: null,
    modos: [],
    users: {},
    templates: {},
    currentTemplate: null
};

const elements = {
    storeAdminSelect: document.getElementById('storeAdminSelect'),
    printerAdminSelect: document.getElementById('printerAdminSelect'),
    lsInputsContainer: document.getElementById('lsInputsContainer'),
    lsForm: document.getElementById('lsForm'),
    printersTableBody: document.getElementById('printersTableBody'),
    addPrinterForm: document.getElementById('addPrinterForm'),
    newFuncaoSelect: document.getElementById('newFuncao'),
    newLsInputsContainer: document.getElementById('newLsInputsContainer'),
    toastContainer: document.getElementById('toastContainer'),
    tabBtns: document.querySelectorAll('.admin-tab-btn'),
    adminViews: document.querySelectorAll('.admin-view'),
    
    // Nivel 2: Users
    usersTableBody: document.getElementById('usersTableBody'),
    addUserForm: document.getElementById('addUserForm'),
    
    // Novo: Bind Function ZPL
    bindFunctionForm: document.getElementById('bindFunctionForm'),
    bindPrintersList: document.getElementById('bindPrintersList'),
    bindFuncaoSelect: document.getElementById('bindFuncaoSelect'),
    
    // Nivel 3: Templates
    templatesList: document.getElementById('templatesList'),
    tplFilename: document.getElementById('tplFilename'),
    tplContent: document.getElementById('tplContent'),
    btnSaveTemplate: document.getElementById('btnSaveTemplate'),
    btnDeleteTemplate: document.getElementById('btnDeleteTemplate'),
    btnNewTemplate: document.getElementById('btnNewTemplate'),
    
    // Nivel 3: Auditoria
    auditTableBody: document.getElementById('auditTableBody')
};

// Aba de Navegação
elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        elements.tabBtns.forEach(b => b.classList.remove('active'));
        elements.adminViews.forEach(v => v.classList.remove('active'));
        
        const targetId = e.currentTarget.getAttribute('data-target');
        e.currentTarget.classList.add('active');
        document.getElementById(targetId).classList.add('active');
        
        // Lazy load modules se a aba for clicada
        if(targetId === 'usersSection' && Object.keys(state.users).length === 0) fetchUsers();
        if(targetId === 'templatesSection' && Object.keys(state.templates).length === 0) fetchTemplates();
        if(targetId === 'auditSection') fetchAuditLogs();
    });
});

// Modals
document.getElementById('btnOpenAddPrinterModal')?.addEventListener('click', () => {
    document.getElementById('addPrinterModal').classList.add('active');
});
document.getElementById('btnOpenAddUserModal')?.addEventListener('click', () => {
    document.getElementById('addUserForm').reset();
    document.getElementById('newUsername').readOnly = false;
    document.getElementById('addUserModal').classList.add('active');
});

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

        renderStoreSelect();
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
        const response = await fetch(`${API_BASE}/printers`, { headers: authHeaders });
        if (handleAuthError(response)) return;
        if (response.ok) {
            state.allPrinters = await response.json();
            if (state.modos) { // Só renderiza a tabela se modos já estiver populado
                renderPrintersTable();
                renderStoreSelect();
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

function renderStoreSelect() {
    if (!elements.storeAdminSelect) return;
    const impressoras = state.allPrinters.length > 0 ? state.allPrinters : state.printers;
    // Extrai Lojas Unicas
    const lojasUnicas = [...new Set(impressoras.map(p => String(p.loja || '').padStart(2, '0')).filter(l => l !== '00'))].sort();
    
    const currSelection = elements.storeAdminSelect.value;
    
    elements.storeAdminSelect.innerHTML = lojasUnicas.map(l => 
        `<option value="${l}">Loja ${l}</option>`
    ).join('');
    
    if (lojasUnicas.length > 0) {
        if (currSelection && lojasUnicas.includes(currSelection)) {
            elements.storeAdminSelect.value = currSelection;
        } else if (state.loja && lojasUnicas.includes(String(state.loja).padStart(2, '0'))) {
            elements.storeAdminSelect.value = String(state.loja).padStart(2, '0');
        } else {
            elements.storeAdminSelect.value = lojasUnicas[0];
        }
    }
    
    elements.storeAdminSelect.onchange = () => renderPrinterSelect();
    renderPrinterSelect();
}

// Render printer select
function renderPrinterSelect() {
    const impressoras = state.allPrinters.length > 0 ? state.allPrinters : state.printers;
    const selectedLoja = elements.storeAdminSelect ? elements.storeAdminSelect.value : null;
    
    const impressorasFiltradas = selectedLoja 
        ? impressoras.filter(p => String(p.loja || '').padStart(2, '0') === selectedLoja)
        : impressoras;

    elements.printerAdminSelect.innerHTML = impressorasFiltradas.map(p => `
        <option value="${p.ip}">${p.nome || p.ip} - ${(p.funcao || []).join(', ')}</option>
    `).join('');

    if (impressorasFiltradas.length > 0) {
        state.selectedPrinter = impressorasFiltradas[0];
        renderDynamicLsInputs();
    } else {
        state.selectedPrinter = null;
        elements.lsInputsContainer.innerHTML = '<p style="color:var(--text-secondary); width: 100%; text-align: center; margin-top: 1rem;">Nenhuma impressora disponível nesta filial.</p>';
    }

    elements.printerAdminSelect.onchange = (e) => {
        state.selectedPrinter = impressorasFiltradas.find(p => p.ip === e.target.value);
        if (state.selectedPrinter) {
            renderDynamicLsInputs();
        }
    };
}

// Render printers table
function renderPrintersTable() {
    const printers = state.allPrinters.length > 0 ? state.allPrinters : state.printers;

    // Popula dropdown de vinculo de funcoes
    if (elements.bindPrintersList) {
        elements.bindPrintersList.innerHTML = printers.map(p => 
            `<label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; padding: 0.2rem; border-radius: 4px; transition: background 0.2s;">
                <input type="checkbox" value="${p.ip}" class="printer-bind-cb" style="cursor: pointer; transform: scale(1.2);">
                ${p.nome || p.ip} (Loja ${p.loja || '--'})
            </label>`
        ).join('');
        
        elements.bindFuncaoSelect.innerHTML = state.modos.map(m =>
            `<option value="${m.key}">${m.label}</option>`
        ).join('');

        // Quando trocar a função (A esquerda), marca na lista da direita QUAIS impressoras já tem ela
        elements.bindFuncaoSelect.addEventListener('change', () => {
            const selectedFunc = elements.bindFuncaoSelect.value;
            elements.bindPrintersList.querySelectorAll('.printer-bind-cb').forEach(cb => {
                const printerObj = printers.find(p => p.ip === cb.value);
                const hasFunc = printerObj && printerObj.funcao && printerObj.funcao.includes(selectedFunc);
                cb.checked = hasFunc;
            });
        });
        
        // Dispara logo no inicio pro primeiro da lista
        elements.bindFuncaoSelect.dispatchEvent(new Event('change'));
    }

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

        // A funcao atual segue inalterada, apenas a margem muda
        const funcao = state.selectedPrinter.funcao || [];

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

// Vinculo de Function a Impressoras (Invertido - Nivel 2)
elements.bindFunctionForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const targetFunc = elements.bindFuncaoSelect.value;
    if (!targetFunc) return;
    
    // Lista de IPs selecionados na caixa p/ receber essa funcao
    const selectedIps = Array.from(elements.bindPrintersList.querySelectorAll('.printer-bind-cb:checked')).map(cb => cb.value);
    
    const printers = state.allPrinters.length > 0 ? state.allPrinters : state.printers;
    const promises = [];

    // Avalia todas as impressoras da lista (inclusive pra 'desmarcar' funcoes removidas)
    // Para simplificar, o escopo se limita aos checkboxes renderizados no HTML pro nivel dele
    const availablePrinterIps = Array.from(elements.bindPrintersList.querySelectorAll('.printer-bind-cb')).map(cb => cb.value);
    
    for (const p of printers) {
        if (!availablePrinterIps.includes(p.ip)) continue; // Ignora as q ele nem enxerga
        
        const isSelectedToHave = selectedIps.includes(p.ip);
        const alreadyHas = p.funcao && p.funcao.includes(targetFunc);
        
        // Precisa Adicionar ?
        if (isSelectedToHave && !alreadyHas) {
            const newFuncao = [...(p.funcao || []), targetFunc];
            promises.push(fetch(`${API_BASE}/printers/ls`, {
                method: 'PUT', headers: authHeaders,
                body: JSON.stringify({ loja: p.loja || state.loja, ip: p.ip, ls: p.ls || {}, funcao: newFuncao })
            }));
        } 
        // Precisa Remover ?
        else if (!isSelectedToHave && alreadyHas) {
            const newFuncao = p.funcao.filter(f => f !== targetFunc);
            promises.push(fetch(`${API_BASE}/printers/ls`, {
                method: 'PUT', headers: authHeaders,
                body: JSON.stringify({ loja: p.loja || state.loja, ip: p.ip, ls: p.ls || {}, funcao: newFuncao })
            }));
        }
    }

    if (promises.length === 0) {
       showToast('info', 'Nada a salvar', 'Nenhuma alteração de vínculo detectada.');
       return;
    }

    try {
        await Promise.all(promises);
        showToast('success', 'Salvo!', `O vínculo para [${targetFunc}] foi atualizado em lote.`);
        fetchAllPrinters(); // Faz refresh da tela inteira pra sincronizar local state
    } catch (error) {
        showToast('error', 'Erro', 'Falha ao processar os vínculos em lote.');
    }
});

// Nivel 2: Users Logic

async function fetchUsers() {
    if (currentUserLevel < 2) return;
    try {
        const response = await fetch(`${API_BASE}/users`, { headers: authHeaders });
        if (handleAuthError(response)) return;
        state.users = await response.json();
        renderUsersTable();
    } catch (e) {
        showToast('error', 'Erro', 'Falha ao buscar usuários');
    }
}

function renderUsersTable() {
    elements.usersTableBody.innerHTML = Object.keys(state.users).map(username => {
        const u = state.users[username];
        const isSelf = username === currentUser.user;
        const disabled = (u.nivel === 3 && currentUserLevel < 3) ? 'disabled' : '';
        const levelText = u.nivel === 3 ? '<span style="color:var(--danger-color);font-weight:bold;">3 - Global</span>' : u.nivel;
        
        let lojasDisplay = (u.lojas || []).join(', ');
        if (lojasDisplay.includes('*')) {
            lojasDisplay = 'TODAS (Global)';
        } else if (!lojasDisplay && u.nivel === 3) {
            lojasDisplay = 'TODAS (Global)';
        } else if (!lojasDisplay) {
            lojasDisplay = '--';
        }
        
        return `
        <tr>
            <td>${username} ${isSelf ? ' <span style="font-size:0.8em;color:gray;">(Você)</span>' : ''}</td>
            <td>${levelText}</td>
            <td>${lojasDisplay}</td>
            <td>
                <button class="btn btn-small btn-secondary" onclick="editUser('${username}')" ${disabled}>✏️ Edita</button>
                <button class="btn btn-small btn-danger" onclick="deleteUser('${username}')" ${disabled || isSelf ? 'disabled' : ''}>🗑️</button>
            </td>
        </tr>
    `}).join('');
}

window.editUser = function(username) {
    const u = state.users[username];
    if(!u) return;
    document.getElementById('newUsername').value = username;
    document.getElementById('newUsername').readOnly = true;
    document.getElementById('newUserLevel').value = u.nivel;
    document.getElementById('newUserLojas').value = (u.lojas || []).join(', ');
    document.getElementById('addUserModal').classList.add('active');
};

window.deleteUser = async function(username) {
    if (!confirm(`Remover ACESSO do admin ${username}?`)) return;
    try {
        const res = await fetch(`${API_BASE}/users/${username}`, { method: 'DELETE', headers: authHeaders });
        const data = await res.json();
        if(data.success) {
            showToast('success', 'Deletado', 'Usuário removido com sucesso.');
            fetchUsers();
        } else showToast('error', 'Erro', data.error);
    } catch(e) { showToast('error', 'Erro', 'Falha de rede.');}
};

elements.addUserForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const lojasRaw = document.getElementById('newUserLojas').value.split(',').map(x => x.trim()).filter(x => x !== '');
    const userPayload = {
        username: document.getElementById('newUsername').value,
        nivel: document.getElementById('newUserLevel').value,
        lojas: lojasRaw
    };
    try {
        const res = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(userPayload)
        });
        const data = await res.json();
        if(data.success) {
            showToast('success', 'Salvo', 'Usuário salvo com sucesso.');
            document.getElementById('addUserModal').classList.remove('active');
            fetchUsers();
        } else showToast('error', 'Erro', data.error);
    } catch(e) { showToast('error', 'Erro', 'Falha de rede.');}
});


// Nivel 3: Templates ZPL
async function fetchTemplates() {
    if (currentUserLevel < 3) return;
    try {
        const response = await fetch(`${API_BASE}/templates`, { headers: authHeaders });
        if (handleAuthError(response)) return;
        state.templates = await response.json();
        renderTemplatesList();
    } catch (e) {
        showToast('error', 'Erro', 'Falha ao buscar gabaritos ZPL');
    }
}

function renderTemplatesList() {
    const keys = Object.keys(state.templates).sort();
    elements.templatesList.innerHTML = keys.map(name => `
        <li>
            <a href="#" class="nav-link" style="display:block; padding: 0.5rem; border-radius: 4px; background: ${state.currentTemplate === name ? 'var(--accent-primary)' : '#f0f0f0'}; color: ${state.currentTemplate === name ? 'white' : 'black'}; text-decoration:none;" onclick="loadTemplateEditor('${name}')">
                📄 ${name}
            </a>
        </li>
    `).join('');
    
    if (keys.length > 0 && !state.currentTemplate) {
        loadTemplateEditor(keys[0]);
    } else if (keys.length === 0){
        elements.tplFilename.value = '';
        elements.tplContent.value = '';
        elements.btnDeleteTemplate.style.display = 'none';
    }
}

window.loadTemplateEditor = function(filename) {
    state.currentTemplate = filename;
    elements.tplFilename.value = filename;
    
    const tplData = state.templates[filename] || {};
    elements.tplContent.value = typeof tplData === 'string' ? tplData : (tplData.content || '');
    
    const cbExtras = document.getElementById('tplPermitirCamposExtras');
    if (cbExtras) {
        cbExtras.checked = tplData.permitir_campos_extras || false;
    }

    elements.btnDeleteTemplate.style.display = 'inline-block';
    renderTemplatesList(); // re-draw colors
};

elements.btnNewTemplate?.addEventListener('click', () => {
    state.currentTemplate = 'novo_modal.zpl.j2';
    elements.tplFilename.value = 'novo_modal.zpl.j2';
    elements.tplContent.value = '^XA\n// Digite seu ZPL Jinja aqui\n^XZ';
    
    const cbExtras = document.getElementById('tplPermitirCamposExtras');
    if (cbExtras) cbExtras.checked = false;
    
    elements.btnDeleteTemplate.style.display = 'none';
    renderTemplatesList();
});

elements.btnSaveTemplate?.addEventListener('click', async () => {
    const filename = elements.tplFilename.value.trim();
    if (!filename) return showToast('error', 'Erro', 'Dê um nome ao arquivo (ex: funcao.zpl.j2)');
    try {
        const cbExtras = document.getElementById('tplPermitirCamposExtras');
        const permitir = cbExtras ? cbExtras.checked : false;
        
        const res = await fetch(`${API_BASE}/templates`, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({ 
                filename: filename, 
                content: elements.tplContent.value,
                permitir_campos_extras: permitir
            })
        });
        const data = await res.json();
        if(data.success) {
            showToast('success', 'Salvo', `Gabarito ${filename} salvo.`);
            await fetchTemplates();
            loadTemplateEditor(data.filename); // reload c/ nome correto (se adicionou a .j2 extensão)
        } else showToast('error', 'Erro', data.error);
    } catch(e) { showToast('error', 'Erro', 'Falha de rede.');}
});

elements.btnDeleteTemplate?.addEventListener('click', async () => {
    const filename = state.currentTemplate;
    if (!filename) return;
    if (!confirm(`Certeza ABSOLUTA que deseja remover o gabarito ${filename}? Isso afetará as impressões dessa função!`)) return;
    try {
        const res = await fetch(`${API_BASE}/templates/${filename}`, { method: 'DELETE', headers: authHeaders });
        const data = await res.json();
        if(data.success) {
            showToast('success', 'Removido', `Gabarito ${filename} excluído.`);
            state.currentTemplate = null;
            await fetchTemplates();
        } else showToast('error', 'Erro', data.error);
    } catch(e) { showToast('error', 'Erro', 'Falha ao remover o template.');}
});

// Init
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Garante primeiro o carregamento de context (loja, modos)
        await fetchContext();
        // Em seguida roda o getAll para não quebrar tabelas se Nivel >= 2
        if(currentUserLevel >= 1) { // 1 só ve as do context, >= 2 getAll
            await fetchAllPrinters();
        }
    } catch (err) {
        console.error("Erro na inicialização do Admin: ", err);
    }
});

// ==========================================
// Nivel 3: Auditoria Geral
// ==========================================
async function fetchAuditLogs() {
    if (currentUserLevel < 3) return;
    try {
        const response = await fetch(`${API_BASE}/logs/audit`, { headers: authHeaders });
        if (handleAuthError(response)) return;
        const logs = await response.json();
        renderAuditTable(logs);
    } catch (e) {
        showToast('error', 'Erro', 'Falha ao buscar logs de auditoria');
    }
}

function renderAuditTable(logsArray) {
    if (!elements.auditTableBody) return;
    
    if (logsArray.length === 0) {
        elements.auditTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Nenhum log encontrado.</td></tr>';
        return;
    }
    
    elements.auditTableBody.innerHTML = logsArray.map(log => {
        const dateStr = log.timestamp || '--';
        const clientIp = log.client_ip || '--';
        const action = log.action || 'Desconhecida';
        
        let details = '';
        const metaKeys = Object.keys(log).filter(k => !['timestamp', 'client_ip', 'action', 'method', 'path', 'user_agent'].includes(k));
        
        if (metaKeys.length > 0) {
            details = metaKeys.map(k => `<strong>${k}:</strong> ${JSON.stringify(log[k])}`).join(' | ');
        } else {
            details = '<span style="color:#aaa;">Sem detalhes adicionais</span>';
        }
        
        return `
            <tr>
                <td style="font-size: 0.85em;">${dateStr}</td>
                <td style="font-family: monospace;">${clientIp}</td>
                <td><span style="background:var(--bg-color); padding:0.2rem 0.5rem; border-radius:4px; font-weight:600;">${action}</span></td>
                <td style="font-size: 0.85em; color:var(--text-secondary);">${details}</td>
            </tr>
        `;
    }).join('');
}
