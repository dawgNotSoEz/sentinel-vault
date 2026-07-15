import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface AuditEvent {
  id: string;
  event_type: string;
  user_id: string;
  resource_id?: string;
  resource_type?: string;
  action: string;
  status: "success" | "failure";
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface AuditListResponse {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export function useAuditLogs() {
  return useQuery({
    queryKey: ["audit_logs"],
    queryFn: async () => {
      const { data } = await api.get<AuditListResponse>("/audit/");
      return data;
    },
  });
}
