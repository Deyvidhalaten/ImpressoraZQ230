export interface UserPayload {
    sub?: string;
    u?: number; // User Level (1, 2, 3)
    exp?: number;
}

export interface AuthState {
    token: string | null;
    level: number;
    isAuthenticated: boolean;
}

export interface ContextResponseDTO {
    loja: string | null;
    test_mode: boolean;
    printers: PrinterDTO[];
    modos: ModoDTO[];
    ls: Record<string, number>;
}

export interface PrinterDTO {
    ip: string;
    nome: string;
    funcao: string[];
    ls: Record<string, number>;
}

export interface ModoDTO {
    key: string;
    label: string;
    permitir_extras: boolean;
}
