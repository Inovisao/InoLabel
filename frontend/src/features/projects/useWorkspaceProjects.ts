import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import type { ProjectEntry } from "../../shared/api/types";
import { useWorkspaceStore } from "../workspace/store";

/** Projetos do workspace atual; recarrega ao trocar de workspace. */
export function useWorkspaceProjects() {
  const workspace = useWorkspaceStore((s) => s.current);
  const path = workspace?.path ?? "";
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const reload = async () => {
    if (!path) return;
    setLoading(true);
    try {
      setProjects(await api.get<ProjectEntry[]>(`/workspace/projects?path=${encodeURIComponent(path)}`));
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
  }, [path]); // eslint-disable-line react-hooks/exhaustive-deps

  return { workspace, path, projects, loading, reload };
}
