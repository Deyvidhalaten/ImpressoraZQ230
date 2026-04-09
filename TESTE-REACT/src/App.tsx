import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { AuthProvider, useAuth } from './contexts/AuthContext';
import Home from './pages/Home';
import Admin from './pages/Admin';
import Login from './pages/Login';

// Proteger rotas baseadas no Level do AuthContext
const ProtectedRoute = ({ children, minLevel = 1 }: { children: React.ReactNode, minLevel?: number }) => {
  const { authState } = useAuth();
  if (!authState.isAuthenticated) return <Navigate to="/login" replace />;
  if (authState.level < minLevel) return <Navigate to="/" replace />; // Ex: Operador (1) tentando ver Admin (3)
  return children;
};

// Se já logado, não precisa ver o Login de novo
const PublicOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const { authState } = useAuth();
  if (authState.isAuthenticated) return <Navigate to="/" replace />;
  return children;
};

function AppRoutes() {
  return (
    <>
      <Routes>
        <Route 
          path="/login" 
          element={
            <PublicOnlyRoute>
              <Login />
            </PublicOnlyRoute>
          } 
        />
        <Route 
          path="/" 
          element={<Home />} 
        />
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute minLevel={2}>
              <Admin />
            </ProtectedRoute>
          } 
        />
      </Routes>
      <ToastContainer position="top-right" autoClose={3000} theme="colored" />
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
