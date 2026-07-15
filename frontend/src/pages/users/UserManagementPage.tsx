import { Users, UserPlus, Filter, ShieldCheck, MoreVertical, Search } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";

export function UserManagementPage() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Users className="text-cyan-400 w-6 h-6" />
            User Management
          </h1>
          <p className="text-slate-400 mt-1">Manage vault access, assign roles, and configure user policies.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" className="text-slate-300 border-slate-700 hover:bg-slate-800">
            <Filter className="w-4 h-4 mr-2" />
            Filter
          </Button>
          <Button className="bg-cyan-600 hover:bg-cyan-500 text-white border-none shadow-lg shadow-cyan-500/20">
            <UserPlus className="w-4 h-4 mr-2" />
            Invite User
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="bg-slate-900/50 backdrop-blur border-slate-800 p-6">
          <h3 className="text-slate-400 text-sm font-medium mb-2">Total Users</h3>
          <p className="text-3xl font-bold text-cyan-400">1</p>
        </Card>
        <Card className="bg-slate-900/50 backdrop-blur border-slate-800 p-6">
          <h3 className="text-slate-400 text-sm font-medium mb-2">Active Administrators</h3>
          <p className="text-3xl font-bold text-indigo-400">1</p>
        </Card>
        <Card className="bg-slate-900/50 backdrop-blur border-slate-800 p-6">
          <h3 className="text-slate-400 text-sm font-medium mb-2">Locked Accounts</h3>
          <p className="text-3xl font-bold text-emerald-400">0</p>
        </Card>
      </div>

      <Card className="bg-slate-900/50 backdrop-blur border-slate-800 overflow-hidden">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Active Users</h2>
          <div className="relative w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-slate-500" />
            </div>
            <Input 
              placeholder="Search users..." 
              className="pl-10 bg-slate-950 border-slate-800 text-sm text-slate-300 focus:border-cyan-500/50 focus:ring-cyan-500/20"
            />
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800/50 text-slate-400 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4">User</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Last Login</th>
                <th className="px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              <tr className="hover:bg-slate-800/20 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <div className="h-8 w-8 rounded-full bg-cyan-900/50 flex items-center justify-center text-cyan-400 font-bold mr-3 border border-cyan-800">
                      A
                    </div>
                    <div>
                      <div className="font-medium text-slate-200">Admin User</div>
                      <div className="text-xs text-slate-500">admin@sentinel.internal</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    Administrator
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center text-emerald-400 text-xs">
                    <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                    Active
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-400">
                  Just now
                </td>
                <td className="px-6 py-4">
                  <Button variant="secondary" className="h-8 w-8 p-0 rounded-full border-slate-700 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50">
                    <MoreVertical className="w-4 h-4 mx-auto" />
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
