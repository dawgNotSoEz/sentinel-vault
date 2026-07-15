import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface KEKResponse {
  id: string;
  version: number;
  status: "ACTIVE" | "RETIRED" | "COMPROMISED";
  provider: string;
  created_at: string;
  rotated_at: string | null;
}

export interface RotateKEKResponse {
  new_kek: KEKResponse;
  deks_re_encrypted: number;
}

export interface DEKListResponse {
  items: any[];
  total: number;
}

export function useActiveKEK() {
  return useQuery({
    queryKey: ["active_kek"],
    queryFn: async () => {
      const { data } = await api.get<KEKResponse>("/keys/kek/active");
      return data;
    },
    retry: false, // In case it's not bootstrapped yet
  });
}

export function useDEKs() {
  return useQuery({
    queryKey: ["deks"],
    queryFn: async () => {
      const { data } = await api.get<DEKListResponse>("/keys/dek");
      return data;
    },
  });
}

export function useRotateKEK() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<RotateKEKResponse>("/keys/kek/rotate");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active_kek"] });
      queryClient.invalidateQueries({ queryKey: ["deks"] });
    },
  });
}
