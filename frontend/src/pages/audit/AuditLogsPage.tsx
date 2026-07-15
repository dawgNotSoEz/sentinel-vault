import { FileText, Download, Filter } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";

export function AuditLogsPage() {
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
        <div className="p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800/50 mb-4">
            <FileText className="w-8 h-8 text-slate-500" />
          </div>
          <h3 className="text-lg font-medium text-slate-300 mb-2">Loading Audit Logs...</h3>
          <p className="text-slate-500 max-w-sm mx-auto mb-6">
            The audit trail is being fetched from the secure storage.
          </p>
        </div>
      </Card>
    </div>
  );
}
