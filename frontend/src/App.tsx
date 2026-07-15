import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LoginPage } from "./pages/auth/LoginPage";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

import { AppLayout } from "./components/layout/AppLayout";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { KeyManagementPage } from "./pages/keys/KeyManagementPage";
import { AuditLogsPage } from "./pages/audit/AuditLogsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-cyan-500">Initializing secure connection...</div>;
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<DashboardPage />} />
              <Route path="keys" element={<KeyManagementPage />} />
              <Route path="audit" element={<AuditLogsPage />} />
              {/* Other routes will go here: /settings */}
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
