/**
 * BistekPrinter - Stats Application
 * Gráficos de consumo de etiquetas
 */

const API_BASE = window.location.port === '5500' || window.location.port === '5501'
    ? 'http://localhost:8000/api'
    : '/api';

let lojaChart = null;
let redeChart = null;

const elements = {
    lojaFilter: document.getElementById('lojaFilter'),
    periodoFilter: document.getElementById('periodoFilter'),
    refreshStats: document.getElementById('refreshStats'),
    totalEtiquetas: document.getElementById('totalEtiquetas'),
    totalLojas: document.getElementById('totalLojas'),
    mediaDiaria: document.getElementById('mediaDiaria'),
    toastContainer: document.getElementById('toastContainer')
};

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

// Cores para gráficos
const chartColors = [
    '#6366f1', '#8b5cf6', '#ec4899', '#14b8a6',
    '#f59e0b', '#ef4444', '#22c55e', '#3b82f6'
];

// Fetch stats
async function fetchStats() {
    try {
        const dias = elements.periodoFilter.value;
        const loja = elements.lojaFilter.value;

        const params = new URLSearchParams({ dias });
        if (loja) params.append('loja', loja);

        const response = await fetch(`${API_BASE}/stats?${params}`);

        if (!response.ok) {
            throw new Error('Falha ao buscar estatísticas');
        }

        const data = await response.json();

        updateSummary(data);
        updateLojaFilter(data.lojas);
        renderLojaChart(data.por_loja);
        renderRedeChart(data.por_dia);

    } catch (error) {
        console.error('Erro:', error);
        showToast('error', 'Erro', 'Falha ao carregar estatísticas');
    }
}

// Update summary cards
function updateSummary(data) {
    elements.totalEtiquetas.textContent = data.total?.toLocaleString() || '--';
    elements.totalLojas.textContent = data.lojas?.length || '--';
    elements.mediaDiaria.textContent = data.media_diaria?.toLocaleString() || '--';
}

// Update loja filter
function updateLojaFilter(lojas) {
    if (!lojas || elements.lojaFilter.options.length > 1) return;

    lojas.forEach(loja => {
        const option = document.createElement('option');
        option.value = loja;
        option.textContent = `Loja ${loja}`;
        elements.lojaFilter.appendChild(option);
    });
}

// Render loja chart
function renderLojaChart(data) {
    if (!data) return;

    const ctx = document.getElementById('lojaChart').getContext('2d');

    if (lojaChart) lojaChart.destroy();

    lojaChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(data).map(l => `Loja ${l}`),
            datasets: [{
                label: 'Etiquetas',
                data: Object.values(data),
                backgroundColor: chartColors,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' } },
                x: { grid: { display: false } }
            }
        }
    });
}

// Render rede chart
function renderRedeChart(data) {
    if (!data) return;

    const ctx = document.getElementById('redeChart').getContext('2d');

    if (redeChart) redeChart.destroy();

    redeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Object.keys(data),
            datasets: [{
                label: 'Etiquetas',
                data: Object.values(data),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' } },
                x: { grid: { display: false } }
            }
        }
    });
}

// Event listeners
elements.refreshStats.addEventListener('click', fetchStats);
elements.periodoFilter.addEventListener('change', fetchStats);
elements.lojaFilter.addEventListener('change', fetchStats);

// Init
document.addEventListener('DOMContentLoaded', fetchStats);
