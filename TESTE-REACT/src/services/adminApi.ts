import { apiClient } from './api';

export const AdminApi = {
    // --- USUÁRIOS ---
    getUsers: async () => {
        const { data } = await apiClient.get('/users');
        return data; // Record<string, any>
    },
    saveUser: async (payload: any) => {
        const { data } = await apiClient.post('/users', payload);
        return data;
    },
    deleteUser: async (username: string) => {
        const { data } = await apiClient.delete(`/users/${username}`);
        return data;
    },

    // --- IMPRESSORAS ---
    getPrinters: async () => {
        const { data } = await apiClient.get('/printers');
        return data; // Array
    },
    savePrinter: async (payload: any) => {
        const { data } = await apiClient.post('/printers', payload);
        return data;
    },
    deletePrinter: async (ip: string) => {
        const { data } = await apiClient.delete(`/printers/${ip}`);
        return data;
    },

    // --- LOGS ---
    getAuditLogs: async () => {
        const { data } = await apiClient.get('/audit');
        return data;
    },

    // --- TEMPLATES ---
    getTemplates: async () => {
        const { data } = await apiClient.get('/templates');
        return data; // Record<string, { content, permitir_campos_extras }>
    },
    saveTemplate: async (payload: any) => {
        const { data } = await apiClient.post('/templates', payload);
        return data;
    },

    // --- SISTEMA ---
    shutdown: async () => {
        const { data } = await apiClient.post('/shutdown');
        return data;
    }
};
