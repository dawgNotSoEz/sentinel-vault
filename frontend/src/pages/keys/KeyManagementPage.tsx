import { useState } from "react";
import { Key, ShieldAlert, RefreshCw, ShieldCheck, AlertTriangle } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { useActiveKEK, useDEKs, useRotateKEK } from "../../hooks/useKeys";

export function KeyManagementPage() {
  const { data: kek, isLoading: kekLoading } = useActiveKEK();
  const { data: deks, isLoading: deksLoading } = useDEKs();
  const { mutateAsync: rotateKey, isPending: isRotating } = useRotateKEK();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleRotate = async () => {
    if (!confirm("Are you sure you want to rotate the Master Key? This will re-encrypt all DEKs.")) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      const res = await rotateKey();
      setSuccess(`Rotated to v${res.new_kek.version}. Re-encrypted ${res.deks_re_encrypted} DEKs.`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to rotate master key");
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Key className="text-indigo-400 w-6 h-6" />
            Key Management
          </h1>
          <p className="text-slate-400 mt-1">Manage master encryption keys and monitor cryptographic health.</p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="danger" 
            className="shadow-lg shadow-rose-500/20"
            onClick={handleRotate}
            disabled={isRotating}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isRotating ? "animate-spin" : ""}`} />
            {isRotating ? "Rotating..." : "Rotate Master Key"}
          </Button>
        </div>
      </div>

      {(error || success) && (
        <div className={`p-4 rounded-lg border ${error ? "bg-rose-500/10 border-rose-500/20 text-rose-400" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"} flex items-center gap-2`}>
          {error ? <AlertTriangle className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
          {error || success}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Card className="bg-slate-900/50 backdrop-blur border-slate-800 p-6 flex flex-col items-start relative overflow-hidden">
          <div className="absolute top-0 right-0 p-6 opacity-10">
            <ShieldCheck className="w-24 h-24 text-emerald-400" />
          </div>
          <h3 className="text-slate-400 text-sm font-medium mb-2">Master Key Status (KEK)</h3>
          {kekLoading ? (
             <p className="text-xl font-bold text-slate-500 animate-pulse">Loading...</p>
          ) : kek ? (
             <p className="text-3xl font-bold text-emerald-400 mb-4">v{kek.version} Active</p>
          ) : (
             <p className="text-xl font-bold text-rose-400 mb-4">Not Initialized</p>
          )}
          <div className="mt-auto pt-4 border-t border-slate-800/50 w-full">
            <p className="text-sm text-slate-400">Encryption engine is operating normally using AEAD AES-256-GCM.</p>
          </div>
        </Card>

        <Card className="bg-slate-900/50 backdrop-blur border-slate-800 p-6 flex flex-col items-start relative overflow-hidden">
          <div className="absolute top-0 right-0 p-6 opacity-10">
            <Key className="w-24 h-24 text-indigo-400" />
          </div>
          <h3 className="text-slate-400 text-sm font-medium mb-2">Active Data Encryption Keys (DEKs)</h3>
          {deksLoading ? (
            <p className="text-xl font-bold text-slate-500 animate-pulse">Loading...</p>
          ) : (
            <p className="text-3xl font-bold text-indigo-400 mb-4">{deks?.total || 0}</p>
          )}
          <div className="mt-auto pt-4 border-t border-slate-800/50 w-full">
            <p className="text-sm text-slate-400">Unique DEKs currently in rotation across all secrets.</p>
          </div>
        </Card>
      </div>

      <Card className="bg-slate-900/50 backdrop-blur border-slate-800 overflow-hidden">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-rose-500/5">
          <h2 className="text-lg font-semibold text-rose-400 flex items-center">
            <ShieldAlert className="w-5 h-5 mr-2" />
            Cryptographic Operations
          </h2>
        </div>
        <div className="p-8">
          <div className="max-w-3xl">
            <h3 className="text-md font-medium text-slate-200 mb-2">Master Key Rotation (Envelope Encryption)</h3>
            <p className="text-slate-400 mb-6 text-sm leading-relaxed">
              Rotating the Key Encryption Key (KEK) will immediately invalidate the current KEK and generate a new one. 
              The system will automatically decrypt all existing Data Encryption Keys (DEKs) using the old KEK, and re-encrypt them with the new KEK. 
              This is a zero-downtime operation, but it is highly sensitive.
            </p>
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 mb-6 flex items-start">
              <div className="w-2 h-2 rounded-full bg-rose-500 mt-2 mr-3 flex-shrink-0 animate-pulse" />
              <p className="text-sm text-slate-400">
                <strong className="text-slate-300">Warning:</strong> Only users with the <code className="bg-slate-800 px-1 py-0.5 rounded text-cyan-400">admin</code> role can perform cryptographic key rotation. All rotation events are immutably logged in the Audit trail.
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
