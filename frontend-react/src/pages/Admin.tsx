import { useEffect, useState } from 'react';
import { Shield, KeyRound, Printer, Users, FileCode, ScrollText, LogOut, ArrowLeft, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useAdminController } from '../controllers/useAdminController';
import { AdminApi } from '../services/adminApi';

export default function Admin() {
    const { authState, logout } = useAuth();
    const ctrl = useAdminController();
    
    // Tab State Manager
    const [activeTab, setActiveTab] = useState<'vault' | 'printers' | 'users' | 'templates' | 'audit'>('vault');

    useEffect(() => {
        ctrl.refreshAll();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Desligar Sistema Seguro
    const handleShutdown = async () => {
        if (!confirm('ATENÇÃO: Você desligará todo o Serviço de Impressão Bistek e a BAPI Server. Prosseguir?')) return;
        try {
            await AdminApi.shutdown();
            alert("Sistema desligado. Reinicie o serviço no Servidor Hospedeiro.");
            logout();
        } catch { }
    };

    return (
        <div className="admin-container" style={{ display: 'flex', height: '100vh' }}>
            {/* SIDEBAR NAVIGATION */}
            <nav className="admin-nav" style={{ width: '260px', backgroundColor: '#fff', borderRight: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '1.5rem' }}>
                    <h2 style={{ fontSize: '1.25rem', color: '#1e293b', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Shield size={24} color="#e31e24" /> Painel Admin
                    </h2>
                    <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.5rem' }}>Nível de Acesso: N{authState.level}</p>
                </div>
                
                <div style={{ flex: 1 }}>
                    <button className={`nav-btn ${activeTab === 'vault' ? 'active' : ''}`} onClick={() => setActiveTab('vault')}><KeyRound size={18}/> Cofre & Loja</button>
                    <button className={`nav-btn ${activeTab === 'printers' ? 'active' : ''}`} onClick={() => setActiveTab('printers')}><Printer size={18}/> Equipamentos</button>
                    
                    {authState.level >= 2 && (
                        <button className={`nav-btn ${activeTab === 'users' ? 'active' : ''}`} onClick={() => setActiveTab('users')}><Users size={18}/> Operadores</button>
                    )}
                    
                    {authState.level >= 3 && (
                        <>
                            <button className={`nav-btn ${activeTab === 'templates' ? 'active' : ''}`} onClick={() => setActiveTab('templates')}><FileCode size={18}/> ZPL Templates</button>
                            <button className={`nav-btn ${activeTab === 'audit' ? 'active' : ''}`} onClick={() => setActiveTab('audit')}><ScrollText size={18}/> Auditoria</button>
                        </>
                    )}
                </div>

                <div style={{ padding: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
                    <button className="btn btn-secondary" style={{ width: '100%', marginBottom: '1rem' }} onClick={() => window.location.href = '/'}>
                        <ArrowLeft size={16}/> Voltar Operação
                    </button>
                    <button className="btn btn-danger" style={{ width: '100%', backgroundColor: '#ef4444' }} onClick={handleShutdown}>
                        <LogOut size={16}/> Desligar BAPI
                    </button>
                </div>
            </nav>

            {/* MAIN CONTENT AREA */}
            <div className="admin-content" style={{ flex: 1, padding: '2rem', backgroundColor: '#f8fafc', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <h1>{activeTab.toUpperCase()} OVERVIEW</h1>
                    <button className="btn btn-secondary" onClick={ctrl.refreshAll} disabled={ctrl.isRefreshing}>
                         <RefreshCw size={16} className={ctrl.isRefreshing ? 'spin' : ''}/> Atualizar Dados
                    </button>
                </div>

                {activeTab === 'vault' && (
                    <div className="card">
                        <h3>Cofre UAC Transparente e AD Context</h3>
                        <p style={{ color: '#64748b', marginTop: '1rem' }}>Sua credencial (Nivel {authState.level}) está logada com JWT Criptografado blindando alterações não autorizadas nos endpoints Python. Os Tokens da Base de Filial operam na memória de AppData do Hospedeiro Local.</p>
                    </div>
                )}

                {activeTab === 'printers' && (
                    <div className="card">
                        <h3>Gestor de Impressoras (Zebra ZQ)</h3>
                        <table className="admin-table" style={{ width: '100%', textAlign: 'left', marginTop: '1.5rem', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #e2e8f0' }}><th>IP da Máquina</th><th>Referência</th><th>Setores de Trabalho</th><th>Ação</th></tr>
                            </thead>
                            <tbody>
                                {ctrl.printers.map((p, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0' }}>
                                        <td style={{ padding: '1rem 0' }}>{p.ip}</td>
                                        <td>{p.nome}</td>
                                        <td>{p.funcao?.join(' | ') || 'Nenhum'}</td>
                                        <td>
                                            <button className="btn btn-small btn-danger" onClick={() => ctrl.deletePrinter(p.ip)}>🗑️</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {activeTab === 'users' && authState.level >= 2 && (
                    <div className="card">
                        <h3>Painel de Usuários (RBAC)</h3>
                        <table className="admin-table" style={{ width: '100%', textAlign: 'left', marginTop: '1.5rem', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #e2e8f0' }}><th>Matrícula / User</th><th>Nível Perfil</th><th>Loja Ref</th><th>Remover</th></tr>
                            </thead>
                            <tbody>
                                {Object.keys(ctrl.users).map((u) => (
                                    <tr key={u} style={{ borderBottom: '1px solid #e2e8f0' }}>
                                        <td style={{ padding: '1rem 0' }}>{u}</td>
                                        <td>{ctrl.users[u].nivel}</td>
                                        <td>{(ctrl.users[u].lojas || []).join() || 'Local'}</td>
                                        <td>
                                           {ctrl.users[u].nivel < authState.level && (
                                              <button className="btn btn-small btn-danger" onClick={() => ctrl.deleteUser(u)}>Demissão</button>
                                           )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {activeTab === 'templates' && authState.level >= 3 && (
                    <div className="card">
                         <h3>Edição Pura Jinja2/ZPL</h3>
                         <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                             <div style={{ flex: 1 }}>
                                 {Object.keys(ctrl.templates).map(file => (
                                     <button key={file} onClick={() => alert("Exibição desativada placeholder. Edite código na IDE por enquanto!")} style={{ display: 'block', margin: '0.5rem 0', width: '100%', padding: '0.5rem', textAlign: 'left', cursor: 'pointer' }}>
                                         📄 {file} (Epic 13 Form: {ctrl.templates[file]?.permitir_campos_extras ? 'Sim' : 'Não'})
                                     </button>
                                 ))}
                             </div>
                             <div style={{ flex: 2, backgroundColor: '#1e293b', padding: '1rem', borderRadius: '8px', color: '#38bdf8' }}>
                                  <p>{`>> IDE Integrada para Alteração ZPL a construir (Ver Roadmap).`} </p>
                             </div>
                         </div>
                    </div>
                )}

                {activeTab === 'audit' && authState.level >= 3 && (
                     <div className="card" style={{ backgroundColor: '#1e1e1e', color: '#00ff00', fontFamily: 'monospace' }}>
                         <h3>Logs de Auditoria (Security N3)</h3>
                         <pre style={{ overflowX: 'auto', whiteSpace: 'pre-wrap', marginTop: '1rem' }}>
                             {ctrl.logs || 'Carregando buffer de intrusos...'}
                         </pre>
                     </div>
                )}
            </div>
        </div>
    );
}
