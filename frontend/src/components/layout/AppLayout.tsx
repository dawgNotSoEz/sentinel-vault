
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden text-slate-300">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-auto p-6 lg:p-8 bg-slate-950/50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
