import { Plus, Filter, ShieldCheck, Key, Clock, MoreVertical } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { useSecrets } from "../../hooks/useSecrets";

export function DashboardPage() {
  const { data: secrets, isLoading } = useSecrets();

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="text-cyan-400 w-6 h-6" />
            Active Vaults
          </h1>
          <p className="text-slate-400 mt-1">Manage and monitor encrypted secrets across all environments.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" className="text-slate-300 border-slate-700 hover:bg-slate-800">
            <Filter className="w-4 h-4 mr-2" />
            Filter
          </Button>
          <Button className="bg-cyan-600 hover:bg-cyan-500 text-white border-none shadow-lg shadow-cyan-500/20">
            <Plus className="w-4 h-4 mr-2" />
            New Secret
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {[
          { label: "Total Secrets", value: isLoading ? "-" : (secrets?.length || 0), color: "text-cyan-400" },
          { label: "Active Categories", value: "0", color: "text-indigo-400" },
          { label: "Access Events (24h)", value: "0", color: "text-emerald-400" },
        ].map((stat, i) => (
          <Card key={i} className="bg-slate-900/50 backdrop-blur border-slate-800 p-6">
            <h3 className="text-slate-400 text-sm font-medium mb-2">{stat.label}</h3>
            <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
          </Card>
        ))}
      </div>

      <Card className="bg-slate-900/50 backdrop-blur border-slate-800 overflow-hidden">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Secret Registry</h2>
        </div>
        
        {isLoading ? (
          <div className="p-12 text-center text-cyan-500 animate-pulse">Loading secrets...</div>
        ) : secrets && secrets.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/50 text-slate-400 uppercase text-xs font-semibold">
                <tr>
                  <th className="px-6 py-4">Secret Name</th>
                  <th className="px-6 py-4">Category ID</th>
                  <th className="px-6 py-4">Created</th>
                  <th className="px-6 py-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {secrets.map((secret) => (
                  <tr key={secret.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <Key className="w-4 h-4 text-cyan-500 mr-3" />
                        <span className="font-medium text-slate-200">{secret.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {secret.category_id || "Uncategorized"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center text-slate-400">
                        <Clock className="w-4 h-4 mr-2 opacity-70" />
                        {new Date(secret.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Button variant="secondary" className="h-8 w-8 p-0 rounded-full border-slate-700 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50">
                        <MoreVertical className="w-4 h-4 mx-auto" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800/50 mb-4">
              <ShieldCheck className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-slate-300 mb-2">No secrets found</h3>
            <p className="text-slate-500 max-w-sm mx-auto mb-6">
              There are no encrypted secrets stored in the registry yet. Create your first secret to secure your infrastructure.
            </p>
            <Button variant="secondary" className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10">
              Create First Secret
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
