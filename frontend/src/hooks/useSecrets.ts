import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SecretSummary, Category } from "../types/secret";

export function useSecrets() {
  return useQuery({
    queryKey: ["secrets"],
    queryFn: async () => {
      const { data } = await api.get<SecretSummary[]>("/secrets/");
      return data;
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
