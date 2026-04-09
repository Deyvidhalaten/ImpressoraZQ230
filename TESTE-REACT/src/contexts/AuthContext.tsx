import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';
import type { AuthState, UserPayload } from '../dtos/ContextDTO';

interface AuthContextProps {
    authState: AuthState;
    setToken: (token: string) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextProps | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [authState, setAuthState] = useState<AuthState>({
        token: null,
        level: 0,
        isAuthenticated: false
    });

    // On Load: Read LocalStorage
    useEffect(() => {
        const localToken = localStorage.getItem('bistekprinter_token');
        if (localToken) {
            handleToken(localToken);
        }
    }, []);

    // Axios Interceptor for automated bearer injection
    useEffect(() => {
        const interceptor = axios.interceptors.request.use(config => {
            if (authState.token) {
                config.headers.Authorization = `Bearer ${authState.token}`;
            }
            return config;
        });
        return () => axios.interceptors.request.eject(interceptor);
    }, [authState.token]);

    const handleToken = (token: string) => {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));

            const payload: UserPayload = JSON.parse(jsonPayload);
            const tsNow = Math.floor(Date.now() / 1000);

            if (payload.exp && payload.exp < tsNow) {
                console.warn('Token expired');
                logout();
                return;
            }

            const lvl = payload.u || 0;
            localStorage.setItem('bistekprinter_token', token);
            setAuthState({
                token,
                level: lvl,
                isAuthenticated: true
            });
            
        } catch (e) {
            console.error('Invalid token', e);
            logout();
        }
    };

    const setToken = (token: string) => {
        handleToken(token);
    };

    const logout = () => {
        localStorage.removeItem('bistekprinter_token');
        setAuthState({
            token: null,
            level: 0,
            isAuthenticated: false
        });
    };

    return (
        <AuthContext.Provider value={{ authState, setToken, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
