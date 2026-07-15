import React, { useState } from "react";
import { Shield, LockKeyhole } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../../components/ui/Card";
import { motion } from "framer-motion";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    
    try {
      const res = await api.post("/auth/login", { email, password });
      login(res.data);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid credentials");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4 relative overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Card className="w-full max-w-md glass">
          <CardHeader className="space-y-3 text-center pt-8">
            <div className="mx-auto bg-slate-900 p-3 rounded-2xl border border-slate-700/50 w-14 h-14 flex items-center justify-center shadow-inner">
              <Shield className="w-8 h-8 text-cyan-400" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight text-white">Sentinel Vault</CardTitle>
            <CardDescription className="text-slate-400">Secure access to the organization's secrets.</CardDescription>
          </CardHeader>
          <form onSubmit={handleLogin}>
            <CardContent className="space-y-4">
              {error && (
                <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm p-3 rounded-md flex items-center gap-2">
                  <LockKeyhole className="w-4 h-4" />
                  {error}
                </div>
              )}
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Email Address</label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@sentinel.local"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Master Password</label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                />
              </div>
            </CardContent>
            <CardFooter className="pb-8">
              <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
                {isLoading ? "Decrypting Session..." : "Authorize Access"}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
