import { Settings, Shield, Bell, Users, Database } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";

export function SettingsPage() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Settings className="text-slate-400 w-6 h-6" />
            Vault Settings
          </h1>
          <p className="text-slate-400 mt-1">Configure global vault parameters and security policies.</p>
        </div>
        <Button className="bg-cyan-600 hover:bg-cyan-500 text-white border-none shadow-lg shadow-cyan-500/20">
          Save Changes
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="md:col-span-1 space-y-2">
          <nav className="flex flex-col space-y-1">
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md bg-slate-800 text-cyan-400">
              <Shield className="w-4 h-4" />
              Security Policies
            </button>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md text-slate-400 hover:bg-slate-800/50 hover:text-slate-200">
              <Users className="w-4 h-4" />
              Access Control
            </button>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md text-slate-400 hover:bg-slate-800/50 hover:text-slate-200">
              <Bell className="w-4 h-4" />
              Notifications
            </button>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md text-slate-400 hover:bg-slate-800/50 hover:text-slate-200">
              <Database className="w-4 h-4" />
              Backup & Sync
            </button>
          </nav>
        </div>

        <div className="md:col-span-3 space-y-6">
          <Card className="bg-slate-900/50 backdrop-blur border-slate-800 overflow-hidden">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-lg font-semibold text-white">Password Policies</h2>
              <p className="text-sm text-slate-400 mt-1">Enforce strong authentication rules for all vault users.</p>
            </div>
            <div className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-slate-200">Require MFA</h4>
                  <p className="text-xs text-slate-400">Force all users to configure Multi-Factor Authentication.</p>
                </div>
                <div className="relative inline-block w-12 h-6 align-middle select-none transition duration-200 ease-in">
                  <input type="checkbox" name="toggle" id="mfa-toggle" className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 border-slate-700 appearance-none cursor-pointer translate-x-6 border-cyan-500" defaultChecked />
                  <label htmlFor="mfa-toggle" className="toggle-label block overflow-hidden h-6 rounded-full bg-cyan-500 cursor-pointer"></label>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-slate-200">Maximum Failed Login Attempts</h4>
                  <p className="text-xs text-slate-400">Lock account after X failures to prevent brute force.</p>
                </div>
                <div className="w-24">
                  <Input type="number" defaultValue={5} className="bg-slate-950 border-slate-800 text-white" />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-slate-200">Account Lockout Duration (Minutes)</h4>
                  <p className="text-xs text-slate-400">Time to lock the account for after max attempts reached.</p>
                </div>
                <div className="w-24">
                  <Input type="number" defaultValue={15} className="bg-slate-950 border-slate-800 text-white" />
                </div>
              </div>
            </div>
          </Card>

          <Card className="bg-slate-900/50 backdrop-blur border-slate-800 overflow-hidden">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-lg font-semibold text-white">API Security</h2>
              <p className="text-sm text-slate-400 mt-1">Configure global API rate limits and restrictions.</p>
            </div>
            <div className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-slate-200">Global Rate Limit (requests/min)</h4>
                  <p className="text-xs text-slate-400">Maximum allowed API requests per IP per minute.</p>
                </div>
                <div className="w-24">
                  <Input type="number" defaultValue={100} className="bg-slate-950 border-slate-800 text-white" />
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
