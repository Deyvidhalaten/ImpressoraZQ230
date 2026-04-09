import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { LogIn } from 'lucide-react';
import '../index.css';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { setToken } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username) {
      toast.warning('Preencha pelo menos a Matrícula do usuário local.');
      return;
    }

    setLoading(true);
    try {
      const resp = await axios.post('/api/auth/login', {
        username: username.trim(),
        password: password
      });

      if (resp.data.success && resp.data.token) {
        toast.success(`Login concluído! BAPI Conectada.`);
        // Removemos o navigate('/') forçado. 
        // Quando o setToken rodar, o App.tsx vai detectar o token e o PublicOnlyRoute
        // vai fazer o redirecionamento Declarativo para '/' automaticamente sem estourar o Router.
        setTimeout(() => {
            setToken(resp.data.token);
        }, 800);
      } else {
        toast.error(resp.data.error || 'Autenticação Inválida');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Erro de comunicação de rede ou AD fora do ar.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#f0f2f5' }}>
      <div style={{ background: '#fff', padding: '2.5rem', borderRadius: '12px', boxShadow: '0 8px 30px rgba(0,0,0,0.12)', width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <LogIn size={48} color="var(--primary-color, #e60000)" />
          <h2 style={{ marginTop: '1rem', color: '#1a1a1a' }}>Acesso Restrito</h2>
          <p style={{ color: '#666', fontSize: '0.9rem' }}>Insira sua matrícula e senha da rede.</p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: '#333' }}>Matrícula</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Ex: 5678"
              style={{ width: '100%', padding: '0.8rem', border: '1px solid #ccc', borderRadius: '6px', fontSize: '1rem' }}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: '#333' }}>Senha</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="•••••••• (Opcional p/ Modo Teste)"
              style={{ width: '100%', padding: '0.8rem', border: '1px solid #ccc', borderRadius: '6px', fontSize: '1rem' }}
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            style={{ 
              marginTop: '1rem', 
              padding: '1rem', 
              backgroundColor: 'var(--primary-color, #e60000)', 
              color: 'white', 
              border: 'none', 
              borderRadius: '6px', 
              fontWeight: 'bold', 
              fontSize: '1rem', 
              cursor: loading ? 'wait' : 'pointer',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Validando NTLM...' : 'Entrar no Sistema'}
          </button>
        </form>
      </div>
    </div>
  );
}
