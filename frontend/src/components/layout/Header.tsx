
import { Bell, LogOut, Search } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { Input } from "../ui/Input";

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b border-slate-800 bg-slate-900/30 backdrop-blur-md">
      <div className="flex-1 flex items-center">
        <div className="max-w-md w-full relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
          </div>
          <Input 
            className="pl-10 bg-slate-900/50 border-slate-700 focus:border-cyan-500/50 focus:ring-cyan-500/20 w-full" 
            placeholder="Search secrets, categories, or IDs... (Press '/')"
          />
        </div>
      </div>
      
      <div className="flex items-center space-x-6 ml-4">
        <button className="text-slate-400 hover:text-slate-200 transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-0 right-0 block h-2 w-2 rounded-full bg-cyan-500 ring-2 ring-slate-900" />
        </button>
        
        <div className="h-8 w-px bg-slate-800" />
        
        <div className="flex items-center space-x-3">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-slate-200">{user?.full_name}</span>
            <span className="text-xs text-slate-500">Authorized Operator</span>
          </div>
          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-cyan-500/20 border border-slate-700">
            {user?.full_name.charAt(0).toUpperCase()}
          </div>
        </div>

        <button 
          onClick={logout}
          className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors ml-2"
          title="Terminate Session"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
