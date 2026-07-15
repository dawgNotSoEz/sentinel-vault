
import { NavLink } from "react-router-dom";
import { Shield, Key, FileText, Database, Settings } from "lucide-react";
import { clsx } from "clsx";
import { useAuth } from "../../contexts/AuthContext";

export function Sidebar() {
  const { user } = useAuth();
  
  const navItems = [
    { to: "/", icon: Database, label: "Vaults & Secrets" },
    { to: "/keys", icon: Key, label: "Key Management" },
    { to: "/audit", icon: FileText, label: "Audit Logs" },
  ];

  if (user?.is_active) {
    navItems.push({ to: "/settings", icon: Settings, label: "Settings" });
  }

  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-800 bg-slate-900/50 backdrop-blur-xl hidden md:flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <Shield className="w-6 h-6 text-cyan-400 mr-3" />
        <span className="text-lg font-bold text-white tracking-tight">Sentinel Vault</span>
      </div>

      <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              clsx(
                "flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-cyan-500/10 text-cyan-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              )
            }
          >
            <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="bg-slate-800/40 rounded-lg p-4 backdrop-blur-sm border border-slate-700/50">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">System Status</p>
          <div className="flex items-center">
            <div className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
            <span className="text-sm text-emerald-400 font-medium">Engine Active</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
