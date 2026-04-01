import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { LogOut, FileText, Search, Settings } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { ApiService } from '../services/api';
import type { ContextResponseDTO, ModoDTO, PrinterDTO } from '../dtos/ContextDTO';

export default function Home() {
  const { authState, logout } = useAuth();
  
  // -- Local Application States (Equivalent to app.js `state`)
  const [loadingContext, setLoadingContext] = useState(true);
  const [contextData, setContextData] = useState<ContextResponseDTO | null>(null);
  
  const [modos, setModos] = useState<ModoDTO[]>([]);
  const [printers, setPrinters] = useState<PrinterDTO[]>([]);
  const [currentMode, setCurrentMode] = useState<ModoDTO | null>(null);
  const [selectedPrinterIp, setSelectedPrinterIp] = useState<string>('');
  
  // Print Form States
  const [searchType, setSearchType] = useState<'codigo' | 'descricao'>('codigo');
  const [codigoInput, setCodigoInput] = useState('');
  const [copies, setCopies] = useState<number>(1);
  const [extraCampos, setExtraCampos] = useState({ c1: '', c2: '', c3: '', c4: '' });
  const [selectedProduto, setSelectedProduto] = useState<any | null>(null);
  
  // Modal Search States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalSearchText, setModalSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  
  // -- Initialization Lifecycle
  useEffect(() => {
    carregarContexto();
  }, []);

  const carregarContexto = async () => {
    try {
      const resp = await ApiService.getContext();
      setContextData(resp);
      
      // Filtrar apenas modulos habilitados pelas impressoras cadastradas
      const activeFunctions = new Set<string>();
      resp.printers.forEach(p => p.funcao?.forEach(f => activeFunctions.add(f.toLowerCase())));
      
      const filteredModos = resp.modos.filter(m => activeFunctions.has(m.key.toLowerCase()));
      setModos(filteredModos);
      
      const savedMode = localStorage.getItem('bistekprinter_mode');
      const modoValido = filteredModos.find(m => m.key === savedMode) || filteredModos[0];
      setCurrentMode(modoValido || null);
      
    } catch (e: any) {
      toast.error(e.response?.data?.error || "Erro de servidor (BAPI offline ou fora de alcance).");
    } finally {
      setLoadingContext(false);
    }
  };

  // Re-filtrar listas de impressoras sempre que o Modo Ativo mudar
  useEffect(() => {
    if (currentMode && contextData) {
      const modeLevel = currentMode.key.toLowerCase();
      const availableFilters = contextData.printers.filter(p => p.funcao?.some((pf) => pf.toLowerCase() === modeLevel));
      setPrinters(availableFilters);
      
      // Se não houver impressora selecionada ou a atual não tiver esta função
      const prevIp = localStorage.getItem('bistekprinter_printer');
      if (prevIp && availableFilters.find(a => a.ip === prevIp)) {
        setSelectedPrinterIp(prevIp);
      } else if (availableFilters.length > 0) {
        setSelectedPrinterIp(availableFilters[0].ip);
      } else {
        setSelectedPrinterIp('');
      }
      setSelectedProduto(null);
    }
  }, [currentMode, contextData]);

  const selectModo = (modo: ModoDTO) => {
    setCurrentMode(modo);
    localStorage.setItem('bistekprinter_mode', modo.key);
  };
  
  const increaseCopies = () => setCopies(v => (v < 100 ? v + 1 : v));
  const decreaseCopies = () => setCopies(v => (v > 1 ? v - 1 : v));

  // --- Handlers da Busca Rest API ---
  const handleModalSearchEvent = async (termo: string) => {
    if (!termo || termo.length < 3 || !currentMode) return;
    setIsSearching(true);
    setSearchResults([]);
    try {
      const params = { modo: currentMode.key, tipo: 'descricao', termo };
      const res = await ApiService.buscarProduto(params.modo, params.tipo, params.termo);
      
      if (res.success && Array.isArray(res.dados)) {
        setSearchResults(res.dados);
      } else if (res.success && !Array.isArray(res.dados)) {
        setSearchResults([res.dados]); // Se o db trazer unitário converte para lista
      } else {
        setSearchResults([]);
      }
    } catch (error) {
       console.error(error);
    } finally {
       setIsSearching(false);
    }
  };

  const handleSelectModalProduct = (prod: any) => {
     setSelectedProduto(prod);
     // O código interno preenchido como readOnly pro user não digitar por cima
     setCodigoInput(prod.SEQPRODUTO || prod.CODPROD || prod.codigo || '');
     setIsModalOpen(false);
  };

  const submitPrint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!codigoInput) return toast.warning('Código obrigatório.');
    if (!selectedPrinterIp) return toast.warning('Impressora não selecionada neste setor.');
    
    // Despacho limpo focado na nova integração Epic 13 Simplificada (Backend Blind)
    const payload: any = {
      modo: currentMode?.key,
      codigo: codigoInput,
      copies: copies,
      printer_ip: selectedPrinterIp
    };

    if (selectedProduto) {
      payload.produto_dados = selectedProduto;
    }

    const { c1, c2, c3, c4 } = extraCampos;
    if (c1 || c2 || c3 || c4) {
      payload.campos_extras = {};
      if (c1) payload.campos_extras.CAMPO_1 = c1;
      if (c2) payload.campos_extras.CAMPO_2 = c2;
      if (c3) payload.campos_extras.CAMPO_3 = c3;
      if (c4) payload.campos_extras.CAMPO_4 = c4;
    }
    
    // Notifica andamento
    const idToast = toast.loading('Consultando produto e disparando ZPL...');
    try {
      const res = await ApiService.solicitarImpressao(payload);
      if (res.success) {
        toast.update(idToast, { render: 'Etiqueta Impressa na Zebrinha com sucesso!', type: 'success', isLoading: false, autoClose: 3000 });
        if (!selectedProduto) setCodigoInput(''); // Limpa só se não estava congelada
      } else {
        toast.update(idToast, { render: res.error, type: 'error', isLoading: false, autoClose: 5000 });
      }
    } catch (e: any) {
      toast.update(idToast, { render: e.response?.data?.error || 'Erro Crítico!', type: 'error', isLoading: false, autoClose: 5000 });
    }
  };

  // Renderizadores Visuais
  if (loadingContext) return <div className="loader"><div></div></div>;

  return (
    <div className="app-container">
      {/* HEADER COMPONENT (Extracted natively from index.html) */}
      <header className="header">
        <div className="header-content">
          <div className="logo-area">
             <img src="/logo.png" alt="Bistek Supermercados" className="logo" />
             <div className="system-info">
                 <h1 className="system-title">Bistek Printer ZQ220</h1>
                 <span className="badge badge-success" id="statusBadge" style={{ display: 'inline-block' }}>✓ Conectado</span>
             </div>
          </div>
          <div className="user-area">
            {authState.level >= 2 && (
              <button className="btn btn-secondary btn-small" onClick={() => window.location.href = '/admin'}>
                 <Settings size={16} /> Admin Panel
              </button>
            )}
            <button className="btn btn-outline btn-small" onClick={logout}>
               <LogOut size={16} /> Sair
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="status-cards">
            <div className="card info-card">
               <div className="info-icon"><FileText size={24}/></div>
               <div className="info-text">
                  <span className="info-label">Base de Filiais</span>
                  <span className="info-value" id="lojaName">{contextData?.loja || 'Offline'}</span>
               </div>
            </div>
            {/* Modo Test BAPI */}
            {contextData?.test_mode && (
             <div className="card info-card warning">
               <div className="info-icon" style={{color: '#f59e0b'}}>⚠️</div>
               <div className="info-text">
                  <span className="info-label">Ambiente Crítico</span>
                  <span className="info-value">BAPI Offline (Loja 17 FAKE)</span>
               </div>
             </div>
            )}
        </div>

        {/* MODO TABS */}
        <div className="main-grid">
           <div className="card form-card">
              <h2 className="card-title">Seleção de Operação</h2>
              {modos.length <= 4 ? (
                <div className="mode-tabs">
                    {modos.map(m => (
                      <button 
                        key={m.key} 
                        className={`mode-tab ${currentMode?.key === m.key ? 'active' : ''}`} 
                        onClick={() => selectModo(m)}
                      >
                         {m.label}
                      </button>
                    ))}
                </div>
              ) : (
                <select className="form-select" value={currentMode?.key || ''} onChange={(e) => {
                   const achou = modos.find(m => m.key === e.target.value);
                   if (achou) selectModo(achou);
                }}>
                   {modos.map(m => <option key={m.key} value={m.key}>{m.label}</option>)}
                </select>
              )}

              {/* FORM DE IMPRESSÃO */}
              <form onSubmit={submitPrint} style={{ marginTop: '1.5rem' }}>
                 <div className="form-group">
                   <label className="form-label" style={{ display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                      <span>Buscar Produto por:</span>
                      <div className="search-toggles">
                         <button type="button" className={`toggle-btn ${searchType === 'codigo' ? 'active' : ''}`} onClick={() => {setSearchType('codigo'); setSelectedProduto(null); setCodigoInput('');}}>Código PLU / EAN</button>
                         <button type="button" className={`toggle-btn ${searchType === 'descricao' ? 'active' : ''}`} onClick={() => {setSearchType('descricao'); setCodigoInput('');}}>Nome / Descrição</button>
                      </div>
                   </label>
                   
                   {/* Se for CODIGO -> Digita solto, Se for DESCRICAO -> Modal Input Box */}
                   <div style={{ position: 'relative' }}>
                      <input 
                         type={searchType === 'codigo' ? 'number' : 'text'} 
                         className="form-input search-input"
                         placeholder={searchType === 'codigo' ? "Digite Código EAN ou PLU Interno" : "Digite Produto para Pesquisa..."}
                         value={codigoInput}
                         readOnly={selectedProduto !== null} // Trava se já escolheu no modal
                         onChange={(e) => setCodigoInput(e.target.value)}
                         onKeyDown={(e) => {
                           if (e.key === 'Enter') {
                             e.preventDefault();
                             if (searchType === 'descricao' && !selectedProduto) setIsModalOpen(true);
                             else submitPrint(e);
                           }
                         }}
                      />
                      {searchType === 'descricao' && !selectedProduto && (
                         <button type="button" className="btn-search" onClick={() => setIsModalOpen(true)}>
                           <Search size={18} /> Lupa
                         </button>
                      )}
                   </div>
                 </div>

                 {/* Produto Congelado da Busca de Descricao */}
                 {selectedProduto && (
                   <div className="selected-product-card" style={{ display: 'flex' }}>
                       <div className="selected-product-info">
                           <span className="selected-product-name">{selectedProduto.DESCRICAO || selectedProduto.descricao}</span>
                           <span className="selected-product-code">#{selectedProduto.SEQPRODUTO || selectedProduto.codprod}</span>
                       </div>
                       <button type="button" className="btn-clear-product" onClick={() => { setSelectedProduto(null); setCodigoInput(''); }}>✕</button>
                   </div>
                 )}

                 <div className="form-row">
                    <div className="form-group">
                       <label className="form-label">Quantidade Etiquestas</label>
                       <div className="quantity-control">
                          <button type="button" className="qty-btn" onClick={decreaseCopies}>−</button>
                          <input type="number" className="form-input qty-input" value={copies} readOnly />
                          <button type="button" className="qty-btn" onClick={increaseCopies}>+</button>
                       </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Impressora Endereçada</label>
                        <select className="form-select" value={selectedPrinterIp} onChange={(e) => {
                           setSelectedPrinterIp(e.target.value);
                           localStorage.setItem('bistekprinter_printer', e.target.value);
                        }}>
                           {printers.map(p => <option key={p.ip} value={p.ip}>{p.nome}</option>)}
                           {printers.length === 0 && <option value="" disabled>Aguardando Impressora (Offline)</option>}
                        </select>
                    </div>
                 </div>

                 {/* EPIC 13: Extra Fields Form (Decisão do Backend) */}
                 {currentMode?.permitir_extras && (
                     <div style={{ marginBottom: '1.5rem', padding: '1rem', border: '1px dashed var(--border-color)', borderRadius: '8px', backgroundColor: 'rgba(0,0,0,0.02)' }}>
                        <h4 style={{ marginTop: 0, fontSize: '0.9em', color: 'var(--text-secondary)', marginBottom: '0.8rem' }}>Campos Adicionais Manuais da ZPL</h4>
                        <div className="form-row" style={{ marginBottom: '0.8rem' }}>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label" style={{ fontSize: '0.8em' }}>Campo_1 (ex: validade)</label>
                                <input type="text" className="form-input" placeholder="Sobrescrever..." value={extraCampos.c1} onChange={e => setExtraCampos(p => ({ ...p, c1: e.target.value }))} />
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label" style={{ fontSize: '0.8em' }}>Campo_2</label>
                                <input type="text" className="form-input" placeholder="Sobrescrever..." value={extraCampos.c2} onChange={e => setExtraCampos(p => ({ ...p, c2: e.target.value }))} />
                            </div>
                        </div>
                     </div>
                 )}

                 <button type="submit" className="btn btn-primary btn-print" style={{ width: '100%' }}>
                     <span className="btn-icon">🖨️</span><span className="btn-text">Imprimir Lote</span>
                 </button>
              </form>
           </div>
        </div>
      </main>

      {/* MODAL DE BUSCA DESCRICAO NATIVO DO REACT */}
      {isModalOpen && (
        <div className="modal-overlay active">
           <div className="modal">
              <div className="modal-header">
                 <h3 className="modal-title">Pesquisa Completa no ERP</h3>
                 <button className="modal-close" onClick={() => setIsModalOpen(false)}>✕</button>
              </div>
              <div className="modal-body">
                 <div className="search-box-modal" style={{ display: 'flex', gap: '8px', marginBottom: '1rem' }}>
                    <input 
                       type="text" 
                       className="form-input" 
                       placeholder="Digite qualquer pedaço do nome..." 
                       value={modalSearchText} 
                       onChange={(e) => {
                          setModalSearchText(e.target.value);
                          if (e.target.value.length > 2) handleModalSearchEvent(e.target.value);
                       }} 
                       autoFocus
                    />
                    <button className="btn btn-primary" onClick={() => handleModalSearchEvent(modalSearchText)} disabled={isSearching}>Consultar Nuvens</button>
                 </div>
                 
                 <div className="product-list-container">
                    {isSearching ? (
                       <div className="product-list-message">Procurando Agulhas no Palheiro na Nuvem BAPI...</div>
                    ) : searchResults.length === 0 && modalSearchText.length > 2 ? (
                       <div className="product-list-message">Nenhum resultado com esta grafia.</div>
                    ) : (
                       <ul className="product-list">
                          {searchResults.map((item, idx) => (
                              <li key={idx} className="product-item" onClick={() => handleSelectModalProduct(item)}>
                                 <div className="product-title">{item.DESCRICAO || item.descricao}</div>
                                 <div className="product-meta">Código: {item.SEQPRODUTO || item.codprod} | Validade (Dias): {item.VALIDADE || item.val_dias || '?'}</div>
                              </li>
                          ))}
                       </ul>
                    )}
                 </div>
              </div>
           </div>
        </div>
      )}
    </div>
  );
}
