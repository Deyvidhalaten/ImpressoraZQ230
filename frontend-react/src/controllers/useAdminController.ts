import { useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { AdminApi } from '../services/adminApi';

export function useAdminController() {
    // --- STATES ---
    const [users, setUsers] = useState<Record<string, any>>({});
    const [printers, setPrinters] = useState<any[]>([]);
    const [templates, setTemplates] = useState<Record<string, any>>({});
    const [logs, setLogs] = useState<string>('');
    const [isRefreshing, setIsRefreshing] = useState(false);

    // --- FETCHERS ---
    const fetchUsers = useCallback(async () => {
        try {
            const data = await AdminApi.getUsers();
            setUsers(data);
        } catch (e) {
            toast.error("Erro ao buscar usuários");
        }
    }, []);

    const fetchPrinters = useCallback(async () => {
        try {
            const data = await AdminApi.getPrinters();
            setPrinters(data);
        } catch (e) {
            toast.error("Erro ao buscar impressoras");
        }
    }, []);

    const fetchTemplates = useCallback(async () => {
        try {
            const data = await AdminApi.getTemplates();
            setTemplates(data);
        } catch (e) {
            toast.error("Erro ao puxar templates ZPL");
        }
    }, []);

    const fetchLogs = useCallback(async () => {
        try {
            const data = await AdminApi.getAuditLogs();
            setLogs(typeof data === "string" ? data : JSON.stringify(data));
        } catch (e) {
            toast.error("Erro ao buscar registros de auditoria");
        }
    }, []);

    const refreshAll = useCallback(async () => {
        setIsRefreshing(true);
        await Promise.all([
            fetchUsers(),
            fetchPrinters(),
            fetchTemplates(),
            fetchLogs()
        ]);
        setIsRefreshing(false);
    }, [fetchUsers, fetchPrinters, fetchTemplates, fetchLogs]);

    // --- MUTATORS ---
    const deleteUser = async (username: string) => {
        if (!confirm(`Excluir usuário ${username}?`)) return;
        try {
            await AdminApi.deleteUser(username);
            toast.success("Usuário removido.");
            fetchUsers();
        } catch (e) {
            toast.error("Acesso Negado ou usuário não existe");
        }
    };

    const deletePrinter = async (ip: string) => {
        if (!confirm(`Remover impressora ${ip}?`)) return;
        try {
            await AdminApi.deletePrinter(ip);
            toast.success("Impressora removida do Cofre.");
            fetchPrinters();
        } catch (e) {
            toast.error("Erro ao remover impressora.");
        }
    };

    const saveTemplate = async (filename: string, content: string, permitir_campos_extras: boolean) => {
        try {
            await AdminApi.saveTemplate({ filename, content, permitir_campos_extras });
            toast.success(`Template ${filename} modificado com sucesso!`);
            fetchTemplates();
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Falha ao gravar arquivo ZPL no backend");
        }
    };

    return {
        users, printers, templates, logs, isRefreshing,
        refreshAll, deleteUser, deletePrinter, saveTemplate,
        fetchUsers, fetchPrinters
    };
}
