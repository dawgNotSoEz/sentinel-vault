import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SecretSummary, Category } from "../types/secret";

export interface SecretListResponse {
  items: SecretSummary[];
  total: number;
  page: number;
  page_size: number;
}

export function useSecrets() {
  return useQuery({
    queryKey: ["secrets"],
    queryFn: async () => {
      const { data } = await api.get<SecretListResponse>("/secrets/");
      return data;
    },
  });
}

export function useCreateSecret() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: { name: string; value: string; description?: string }) => {
      const { data } = await api.post<SecretSummary>("/secrets/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["secrets"] });
    },
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: async () => {
      const { data } = await api.get<Category[]>("/secrets/categories/");
      return data;
    },
  });
}
