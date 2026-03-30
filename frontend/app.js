/**
 * BistekPrinter - Frontend Application
 * Comunicação com API Flask para impressão de etiquetas
 */

// ============================================
// Estado Global
// ============================================
const state = {
    loja: null,
    printers: [],
    modos: [],
    currentMode: null,
    lsFlor: null,
    lsFlv: null,
    isLoading: false,
    searchType: 'codigo',  // 'codigo' ou 'descricao'
    selectedProduct: null  // Produto selecionado via busca por descrição
};

// ============================================
// API Configuration
// ============================================
// Se estamos acessando pela porta 8000 (servidor Flask), usamos /api relativo
// Caso contrário (Live Server, etc), usamos URL absoluta
const API_BASE = window.location.port === '8000'
    ? '/api'
    : 'http://localhost:8000/api';

// ============================================
// DOM Elements
// ============================================
const elements = {
    statusBadge: document.getElementById('statusBadge'),
    lojaName: document.getElementById('lojaName'),
    printerName: document.getElementById('printerName'),
    modeTabs: document.getElementById('modeTabs'),
    printForm: document.getElementById('printForm'),
    codigoInput: document.getElementById('codigoInput'),
    copiesInput: document.getElementById('copiesInput'),
    printerSelect: document.getElementById('printerSelect'),
    printBtn: document.getElementById('printBtn'),
    qtyMinus: document.getElementById('qtyMinus'),
    qtyPlus: document.getElementById('qtyPlus'),
    toastContainer: document.getElementById('toastContainer'),
    // Novos elementos
    btnBuscaCodigo: document.getElementById('btnBuscaCodigo'),
    btnBuscaDescricao: document.getElementById('btnBuscaDescricao'),
    btnSearch: document.getElementById('btnSearch'),
    labelBusca: document.getElementById('labelBusca'),
    selectedProduct: document.getElementById('selectedProduct'),
    selectedProductName: document.getElementById('selectedProductName'),
    selectedProductCode: document.getElementById('selectedProductCode'),
    btnClearProduct: document.getElementById('btnClearProduct'),
    // Modal
    searchModal: document.getElementById('searchModal'),
    modalClose: document.getElementById('modalClose'),
    modalSearchInput: document.getElementById('modalSearchInput'),
    productList: document.getElementById('productList'),
    productLoading: document.getElementById('productLoading'),
    productEmpty: document.getElementById('productEmpty')
};

// ============================================
// Toast Notifications
// ============================================
function showToast(type, title, message, duration = 5000) {
    // Ajuste para Mobile: Tempo reduzido (2s) se a tela for pequena
    if (window.innerWidth <= 600) {
        duration = 2000;
    }

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };

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

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================
// Status Badge
// ============================================
function updateStatus(status, text) {
    elements.statusBadge.className = `status-badge ${status}`;
    elements.statusBadge.querySelector('.status-text').textContent = text;
}

// ============================================
// API Calls
// ============================================
async function fetchContext() {
    try {
        updateStatus('', 'Conectando...');

        const response = await fetch(`${API_BASE}/context`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro ao conectar');
        }

        const data = await response.json();

        // Atualiza estado
        state.loja = data.loja;
        state.printers = data.printers;
        state.lsFlor = data.ls_flor;
        state.lsFlv = data.ls_flv;

        // Cria array de todas as funções ativas de todas as impressoras da loja
        const activeFunctions = new Set();
        data.printers.forEach(p => {
            if (p.funcao && Array.isArray(p.funcao)) {
                p.funcao.forEach(f => activeFunctions.add(f.toLowerCase()));
            }
        });

        // Filtra os modos removendo aqueles que nenhuma impressora do recinto possui permissão
        state.modos = data.modos.filter(m => activeFunctions.has(m.key.toLowerCase()));

        // Recupera preferências do localStorage ou pega o primeiro modo disponível da loja
        const savedMode = localStorage.getItem('bistekprinter_mode');
        state.currentMode = savedMode && state.modos.some(m => m.key === savedMode)
            ? savedMode
            : (state.modos[0]?.key || null);

        // Atualiza UI
        renderContext();
        updateStatus('connected', 'Conectado');

        // Mostra card de modo teste
        if (data.test_mode) {
            const testCard = document.getElementById('testModeCard');
            if (testCard) testCard.style.display = 'flex';
        }

    } catch (error) {
        console.error('Erro ao buscar contexto:', error);
        updateStatus('error', 'Erro de conexão');
        showToast('error', 'Erro de Conexão', error.message);
    }
}

async function searchProducts(query) {
    try {
        const response = await fetch(
            `${API_BASE}/search?q=${encodeURIComponent(query)}&type=${state.searchType}&modo=${state.currentMode}`,
            { method: 'GET', headers: { 'Content-Type': 'application/json' } }
        );

        if (!response.ok) {
            throw new Error('Erro na busca');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao buscar produtos:', error);
        return { products: [], error: error.message };
    }
}

async function sendPrint(codigo, copies, printerIp) {
    try {
        setLoading(true);

        const url = `${API_BASE}/print`;
        const body = {
            modo: state.currentMode,
            codigo: codigo,
            copies: copies,
            printer_ip: printerIp
        };

        // DEBUG
        console.log('[DEBUG sendPrint] URL:', url);
        console.log('[DEBUG sendPrint] Body:', JSON.stringify(body));

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (data.success) {
            showToast('success', 'Impresso!', `${copies} etiqueta(s) de "${data.produto}" enviadas`);
            clearSelectedProduct();
            elements.codigoInput.value = '';
            elements.codigoInput.focus();
        } else {
            showToast('error', 'Falha', data.error || 'Erro ao imprimir');
        }

    } catch (error) {
        console.error('Erro ao imprimir:', error);
        showToast('error', 'Erro', 'Falha na comunicação com o servidor');
    } finally {
        setLoading(false);
    }
}

// ============================================
// UI Rendering
// ============================================
function renderContext() {
    // Info cards
    elements.lojaName.textContent = state.loja || '--';

    // Mode tabs
    renderModeTabs();

    // Printer select (depends on currentMode)
    updatePrinterOptions();
}

function renderModeTabs() {
    if (state.modos.length <= 4) {
        elements.modeTabs.innerHTML = state.modos.map(modo => `
            <button 
                class="mode-tab ${modo.key === state.currentMode ? 'active' : ''}"
                data-mode="${modo.key}"
            >
                ${modo.label}
            </button>
        `).join('');

        // Event listeners for buttons
        elements.modeTabs.querySelectorAll('.mode-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                selectMode(tab.dataset.mode);
            });
        });
    } else {
        elements.modeTabs.innerHTML = `
            <select class="mode-select" id="modeSelectDropdown">
                ${state.modos.map(modo => `
                    <option value="${modo.key}" ${modo.key === state.currentMode ? 'selected' : ''}>
                        ${modo.label}
                    </option>
                `).join('')}
            </select>
        `;

        const select = document.getElementById('modeSelectDropdown');
        select.addEventListener('change', (e) => {
            selectMode(e.target.value);
        });
    }
}

function selectMode(newMode) {
    if (state.currentMode === newMode) return;
    state.currentMode = newMode;
    localStorage.setItem('bistekprinter_mode', state.currentMode);
    renderModeTabs();
    updatePrinterOptions();
    // Limpa produto selecionado ao mudar modo
    clearSelectedProduct();
}

function updatePrinterOptions() {
    // Filtra impressoras pelo modo atual
    const availablePrinters = state.printers.filter(p =>
        p.funcao.map(f => f.toLowerCase()).includes(state.currentMode)
    );

    // Recupera impressora salva
    const savedPrinterIp = localStorage.getItem('bistekprinter_printer');

    elements.printerSelect.innerHTML = availablePrinters.map(p => `
        <option value="${p.ip}" ${p.ip === savedPrinterIp ? 'selected' : ''}>
            ${p.nome || p.ip}
        </option>
    `).join('');

    if (availablePrinters.length === 0) {
        elements.printerSelect.innerHTML = '<option disabled>Nenhuma máq. liberada para este Setor</option>';
        elements.printerSelect.disabled = true;
        elements.printerName.textContent = 'Não autorizada (Vá no Admin)';
    } else {
        elements.printerSelect.disabled = false;
        // Atualiza nome exibido no card
        const selectedPrinter = availablePrinters.find(p => p.ip === elements.printerSelect.value)
            || availablePrinters[0];
        elements.printerName.textContent = selectedPrinter.nome || selectedPrinter.ip;
    }
}

function setLoading(loading) {
    state.isLoading = loading;
    elements.printBtn.disabled = loading;
    elements.printBtn.classList.toggle('loading', loading);
}

// ============================================
// Search Type Toggle
// ============================================
function setSearchType(type) {
    state.searchType = type;

    // Atualiza botões
    elements.btnBuscaCodigo.classList.toggle('active', type === 'codigo');
    elements.btnBuscaDescricao.classList.toggle('active', type === 'descricao');

    // Atualiza label e placeholder
    if (type === 'descricao') {
        elements.labelBusca.textContent = 'Nome do Produto';
        elements.codigoInput.placeholder = 'Digite parte do nome do produto';
    } else {
        elements.labelBusca.textContent = 'Código do Produto';
        elements.codigoInput.placeholder = 'Digite ou escaneie o código';
    }

    // Limpa seleção atual
    clearSelectedProduct();
}

// ============================================
// Product Selection
// ============================================
function selectProduct(product) {
    selectedProduct = product;
    console.log("Produto completo carregado:", product.full_data);
    state.selectedProduct = product;
    elements.selectedProductName.textContent = product.descricao;
    elements.selectedProductCode.textContent = `Código: ${product.codprod} | EAN: ${product.ean}`;
    elements.selectedProduct.style.display = 'flex';
    elements.codigoInput.value = product.codprod;
    closeModal();
}

function clearSelectedProduct() {
    state.selectedProduct = null;
    elements.selectedProduct.style.display = 'none';
    elements.selectedProductName.textContent = '';
    elements.selectedProductCode.textContent = '';
}

// ============================================
// Modal
// ============================================
function openModal(query = '') {
    elements.searchModal.classList.add('active');
    elements.modalSearchInput.value = query;
    elements.modalSearchInput.focus();

    if (query) {
        performModalSearch(query);
    } else {
        showProductList([]);
    }
}

function closeModal() {
    elements.searchModal.classList.remove('active');
}

async function performModalSearch(query) {
    if (!query || query.length < 2) {
        showProductList([]);
        return;
    }

    // Mostra loading
    elements.productLoading.style.display = 'flex';
    elements.productEmpty.style.display = 'none';
    clearProductList();

    const result = await searchProducts(query, 'descricao');

    elements.productLoading.style.display = 'none';

    if (result.products.length === 0) {
        elements.productEmpty.style.display = 'flex';
    } else {
        showProductList(result.products);
    }
}

function showProductList(products) {
    clearProductList();
    elements.productEmpty.style.display = products.length === 0 ? 'flex' : 'none';

    products.forEach(product => {
        const item = document.createElement('div');
        item.className = 'product-item';
        item.innerHTML = `
            <div class="product-item-icon">📦</div>
            <div class="product-item-info">
                <span class="product-item-name">${product.descricao}</span>
                <span class="product-item-details">Código: ${product.codprod} | EAN: ${product.ean}</span>
            </div>
        `;
        item.addEventListener('click', () => selectProduct(product));
        elements.productList.appendChild(item);
    });
}

function clearProductList() {
    // Remove apenas os items, mantém loading e empty
    const items = elements.productList.querySelectorAll('.product-item');
    items.forEach(item => item.remove());
}

// ============================================
// Event Handlers
// ============================================
function setupEventListeners() {
    // Form submit (ou Enter no input, ou clique em Imprimir)
    elements.printForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Verifica se tem modo selecionado
        if (!state.currentMode) {
            showToast('warning', 'Atenção', 'Selecione o tipo de impressão (FLV ou Floricultura)');
            return;
        }

        const codigo = elements.codigoInput.value.trim();
        const copies = parseInt(elements.copiesInput.value) || 1;
        const printerIp = elements.printerSelect.value;

        if (!codigo) {
            showToast('warning', 'Atenção', 'Digite um código de produto');
            elements.codigoInput.focus();
            return;
        }

        // Lógica de "Busca antes de Imprimir"
        // Se não tem produto selecionado, ou se o código mudou -> BUSCAR
        if (!state.selectedProduct || state.selectedProduct.codprod !== codigo) {
            // Realiza busca
            const result = await searchProducts(codigo, state.searchProducts);

            if (result.products.length === 0) {
                showToast('error', 'Não encontrado', 'Produto não encontrado');
                clearSelectedProduct();
            } else {
                // Encontrou: Seleciona e exibe. NÃO imprime.
                selectProduct(result.products[0]);
                // Se foi pelo botão de Imprimir, avisa que agora pode imprimir
                showToast('info', 'Produto Carregado', 'Confira os dados e clique em Imprimir para confirmar.');
            }
            return; // Interrompe fluxo de impressão
        }

        // Se chegou aqui, produto está selecionado e código confere -> IMPRIMIR
        if (!printerIp) {
            showToast('warning', 'Atenção', 'Nenhuma impressora disponível');
            return;
        }

        sendPrint(codigo, copies, printerIp);
    });

    // Botão de busca
    elements.btnSearch.addEventListener('click', async () => {
        const query = elements.codigoInput.value.trim();

        if (!query) {
            showToast('warning', 'Atenção', 'Digite algo para buscar');
            elements.codigoInput.focus();
            return;
        }

        if (state.searchType === 'descricao') {
            // Abre modal com resultados
            openModal(query);
        } else {
            // Busca por código - exibe produto para confirmação (NÃO imprime direto)
            const result = await searchProducts(query, 'codigo');
            if (result.products.length === 0) {
                showToast('error', 'Não encontrado', 'Produto não encontrado com este código');
                clearSelectedProduct();
            } else {
                // Seleciona e exibe o primeiro encontrado
                selectProduct(result.products[0]);
                showToast('success', 'Encontrado', 'Produto localizado. Verifique e clique em Imprimir.');
            }
        }
    });

    // Toggle de tipo de busca
    elements.btnBuscaCodigo.addEventListener('click', () => setSearchType('codigo'));
    elements.btnBuscaDescricao.addEventListener('click', () => setSearchType('descricao'));

    // Limpar produto selecionado
    elements.btnClearProduct.addEventListener('click', clearSelectedProduct);

    // Modal
    elements.modalClose.addEventListener('click', closeModal);
    elements.searchModal.addEventListener('click', (e) => {
        if (e.target === elements.searchModal) closeModal();
    });

    // Busca dentro do modal
    let searchTimeout;
    elements.modalSearchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performModalSearch(e.target.value.trim());
        }, 300); // Debounce de 300ms
    });

    // Quantity buttons
    elements.qtyMinus.addEventListener('click', () => {
        const current = parseInt(elements.copiesInput.value) || 1;
        if (current > 1) {
            elements.copiesInput.value = current - 1;
        }
    });

    elements.qtyPlus.addEventListener('click', () => {
        const current = parseInt(elements.copiesInput.value) || 1;
        if (current < 100) {
            elements.copiesInput.value = current + 1;
        }
    });

    // Input validation
    elements.copiesInput.addEventListener('change', () => {
        let value = parseInt(elements.copiesInput.value) || 1;
        value = Math.max(1, Math.min(100, value));
        elements.copiesInput.value = value;
    });

    // Salvar impressora selecionada no localStorage
    elements.printerSelect.addEventListener('change', (e) => {
        localStorage.setItem('bistekprinter_printer', e.target.value);
        // Atualiza nome no card
        const printer = state.printers.find(p => p.ip === e.target.value);
        if (printer) {
            elements.printerName.textContent = printer.nome || printer.ip;
        }
    });

    // Auto-submit on Enter in codigo input (comum para scanners)
    elements.codigoInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (state.searchType === 'descricao') {
                openModal(elements.codigoInput.value.trim());
            } else {
                elements.printForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    // Escape para fechar modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.searchModal.classList.contains('active')) {
            closeModal();
        }
    });
}

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    fetchContext();

    // Foca no input de código
    elements.codigoInput.focus();
});
