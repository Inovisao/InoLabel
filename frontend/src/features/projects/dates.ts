import type { ProjectEntry } from "../../shared/api/types";

/** "há 5 min", "ontem", "há 3 dias" ou a data. */
export function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return "agora mesmo";
  if (mins < 60) return `há ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `há ${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "ontem";
  if (days < 30) return `há ${days} dias`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Agrupa por última modificação: hoje, últimos 7 dias e mais antigos. */
export function groupByPeriod(projects: ProjectEntry[]): { label: string; items: ProjectEntry[] }[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfWeek = new Date(startOfToday.getTime() - 6 * 24 * 60 * 60 * 1000);

  const toDate = (iso: string) => new Date(iso);

  const today = projects.filter((p) => toDate(p.last_modified) >= startOfToday);
  const thisWeek = projects.filter((p) => {
    const d = toDate(p.last_modified);
    return d >= startOfWeek && d < startOfToday;
  });
  const older = projects.filter((p) => toDate(p.last_modified) < startOfWeek);

  return [
    { label: "Hoje", items: today },
    { label: "Últimos 7 dias", items: thisWeek },
    { label: "Mais antigos", items: older },
  ].filter((g) => g.items.length > 0);
}
