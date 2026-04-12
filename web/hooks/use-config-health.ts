"use client";
import { useQuery } from "@tanstack/react-query";
import { getConfigHealth } from "@/lib/api";

export function useConfigHealth() {
  return useQuery({
    queryKey: ["config-health"],
    queryFn: ({ signal }) => getConfigHealth(signal),
    refetchInterval: 30_000,
    retry: 1,
  });
}
