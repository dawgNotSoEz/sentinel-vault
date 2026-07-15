import { useState } from "react";
import { X, Shield } from "lucide-react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { useCreateSecret } from "../../hooks/useSecrets";

interface CreateSecretModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateSecretModal({ isOpen, onClose }: CreateSecretModalProps) {
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { mutateAsync: createSecret, isPending } = useCreateSecret();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createSecret({ name, value, description });
      onClose();
      setName("");
      setValue("");
      setDescription("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create secret");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="flex justify-between items-center p-6 border-b border-slate-800">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-400" />
            Create Secret
          </h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 block">Name</label>
            <Input 
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. prod-db-password"
              required
              className="bg-slate-950 border-slate-800 text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-cyan-500/20"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 block">Secret Value</label>
            <Input 
              value={value}
              onChange={(e) => setValue(e.target.value)}
              type="password"
              placeholder="Super secret value..."
              required
              className="bg-slate-950 border-slate-800 text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-cyan-500/20"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 block">Description (Optional)</label>
            <Input 
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this used for?"
              className="bg-slate-950 border-slate-800 text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-cyan-500/20"
            />
          </div>

          <div className="pt-4 flex gap-3 justify-end">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Encrypting..." : "Create Secret"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
