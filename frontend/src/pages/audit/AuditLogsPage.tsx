import { FileText, Download, Filter, ShieldAlert, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { useAuditLogs } from "../../hooks/useAuditLogs";

export function AuditLogsPage() {
  const { data: auditData, isLoading } = useAuditLogs();
  const logs = auditData?.items;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="text-amber-400 w-6 h-6" />
            Audit Trail
          </h1>
          <p className="text-slate-400 mt-1">Immutable record of all cryptographic operations and access events.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" className="text-slate-300 border-slate-700 hover:bg-slate-800">
            <Filter className="w-4 h-4 mr-2" />
            Filter
          </Button>
          <Button variant="secondary" className="text-slate-300 border-slate-700 hover:bg-slate-800">
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      <Card className="bg-slate-900/50 backdrop-blur border-slate-800 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-amber-500 animate-pulse">Loading audit trail...</div>
        ) : logs && logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/50 text-slate-400 uppercase text-xs font-semibold">
                <tr>
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Event Type</th>
                  <th className="px-6 py-4">Actor ID</th>
                  <th className="px-6 py-4">Action</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">
                      {log.user_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-slate-300">
                      {log.action}
                    </td>
                    <td className="px-6 py-4">
                      {log.status === "success" ? (
                        <div className="flex items-center text-emerald-400">
                          <CheckCircle2 className="w-4 h-4 mr-1.5" />
                          Success
                        </div>
                      ) : (
                        <div className="flex items-center text-rose-400">
                          <XCircle className="w-4 h-4 mr-1.5" />
                          Failure
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 font-mono">
                      {log.ip_address || "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800/50 mb-4">
              <ShieldAlert className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-slate-300 mb-2">No audit events found</h3>
            <p className="text-slate-500 max-w-sm mx-auto mb-6">
              There are no logs matching your current filters or the system is completely new.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
