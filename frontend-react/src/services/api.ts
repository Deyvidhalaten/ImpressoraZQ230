import axios from 'axios';
import type { ContextResponseDTO } from '../dtos/ContextDTO';
import { toast } from 'react-toastify';

export const apiClient = axios.create({
    baseURL: '/api',
    // O Axios interceptor no AuthContext cuida do JWT Token Header globalmente.
});

// Respostas unificadas de erro
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expirou ou o level de acesso mudou pelo administrador remotamente
            localStorage.removeItem('bistekprinter_token');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

// Camada isolada de Comunicação BAPI & Backend (Padronizando as Responses)
export const ApiService = {
    getContext: async (): Promise<ContextResponseDTO> => {
        const { data } = await apiClient.get('/context');
        return data as ContextResponseDTO;
    },
    
    buscarProduto: async (modo: string, tipo: string, termo: string) => {
        const { data } = await apiClient.get('/search', { params: { modo, tipo, termo } });
        return data; // Pode ser Object (unico) ou Array (lista de descrições)
    },

    solicitarImpressao: async (payload: any) => {
        const { data } = await apiClient.post('/print', payload);
        return data;
    }
};
