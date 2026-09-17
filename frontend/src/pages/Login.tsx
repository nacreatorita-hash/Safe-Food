import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { beginSession } from "@/lib/session";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { AdminSession } from "@/types/api";

function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/admin";
}

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const existingSession = useQuery({
    queryKey: ["admin-session"],
    queryFn: () => apiGet<AdminSession>("/auth/me"),
    retry: false,
    staleTime: 60_000,
  });

  const login = useMutation({
    mutationFn: () => apiPost<AdminSession>("/auth/login", { email, password }),
    onSuccess: () => {
      beginSession();
      navigate(next, { replace: true });
    },
  });

  useEffect(() => {
    if (existingSession.data?.authenticated) navigate(next, { replace: true });
  }, [existingSession.data?.authenticated, navigate, next]);

  const errorMessage = login.error instanceof ApiError && login.error.status === 401
    ? "Credenziali non corrette."
    : login.isError
      ? "Accesso non disponibile. Controlla la configurazione del server."
      : null;

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md items-center justify-center py-10">
      <section className="w-full space-y-6 rounded-3xl border border-slate-200 bg-card p-6 shadow-sm dark:border-slate-800">
        <header className="space-y-3 text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#091E3A] text-white">
            <ShieldAlert className="size-6" aria-hidden />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-700 dark:text-sky-400">Area riservata</p>
            <h1 className="mt-1 font-heading text-2xl font-extrabold tracking-tight">Accesso amministratore</h1>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Questa area è privata e consente di gestire le fonti e le sincronizzazioni.
          </p>
        </header>

        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            login.mutate();
          }}
        >
          <div>
            <Label htmlFor="admin-email">Email</Label>
            <Input
              id="admin-email"
              data-testid="admin-login-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@foodalertitalia.local"
              className="mt-1"
              required
            />
          </div>
          <div>
            <Label htmlFor="admin-password">Password</Label>
            <Input
              id="admin-password"
              data-testid="admin-login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1"
              required
            />
          </div>
          {errorMessage && (
            <p data-testid="admin-login-error" className="rounded-xl bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/30 dark:text-red-200">
              {errorMessage}
            </p>
          )}
          <Button type="submit" data-testid="admin-login-submit" className="w-full" disabled={login.isPending}>
            {login.isPending ? "Accesso in corso…" : "Accedi all’area amministrativa"}
          </Button>
        </form>
      </section>
    </div>
  );
}
