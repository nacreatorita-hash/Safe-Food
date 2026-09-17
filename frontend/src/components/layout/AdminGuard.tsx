import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { LoadingSkeleton } from "@/components/food-alert/Primitives";
import type { AdminSession } from "@/types/api";

export default function AdminGuard({ children }: { children: ReactNode }) {
  const location = useLocation();
  const session = useQuery({
    queryKey: ["admin-session"],
    queryFn: () => apiGet<AdminSession>("/auth/me"),
    retry: false,
    staleTime: 60_000,
  });

  if (session.isLoading) return <LoadingSkeleton rows={4} testId="admin-auth-loading" />;
  if (session.isError || !session.data?.authenticated) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }
  return <>{children}</>;
}
