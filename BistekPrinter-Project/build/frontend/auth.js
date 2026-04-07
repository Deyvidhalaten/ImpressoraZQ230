// config API
const HOSTNAME = window.location.hostname;
const IS_DEV = HOSTNAME === 'localhost' || HOSTNAME === '127.0.0.1';
//const API_BASE = IS_DEV ? 'http://127.0.0.1:8000/api' : `http://${HOSTNAME}:8000/api`;
const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const erroMsg = document.getElementById('errorMessage');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const btn = loginForm.querySelector('button');

            btn.disabled = true;
            btn.textContent = 'Autenticando...';
            erroMsg.style.display = 'none';

            try {
                const response = await fetch(`${API_BASE}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Salvar Token
                    localStorage.setItem('adminToken', data.token);
                    // Redireciona para Admin
                    window.location.href = 'admin.html';
                } else {
                    erroMsg.textContent = data.error || 'Credenciais inválidas.';
                    erroMsg.style.display = 'block';
                }
            } catch (err) {
                erroMsg.textContent = 'Falha na comunicação com o servidor principal.';
                erroMsg.style.display = 'block';
                console.error(err);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Entrar';
            }
        });
    }
});
