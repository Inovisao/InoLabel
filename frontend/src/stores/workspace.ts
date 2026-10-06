import { create } from "zustand";
import { api } from "../api/client";
import type { WorkspaceInfo, WorkspaceOverview, WorkspaceRecent } from "../api/types";

/** Workspace de projetos (modelo Obsidian): a pasta onde ficam todos os projetos. */
interface WorkspaceState {
  current: WorkspaceInfo | null;
  recent: WorkspaceRecent[];
  loaded: boolean;
  error: string | null;
  load: () => Promise<void>;
  open: (path: string, name?: string) => Promise<boolean>;
  /** Volta para a tela de escolha de workspace. */
  chooseAnother: () => void;
  createProject: (body: {
    name: string;
    mode: string;
    data_path: string;
    classes: string[];
  }) => Promise<string | null>;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  current: null,
  recent: [],
  loaded: false,
  error: null,

  load: async () => {
    try {
      const overview = await api.get<WorkspaceOverview>("/workspace");
      set({ current: overview.current, recent: overview.recent, loaded: true, error: null });
    } catch (e) {
      set({ loaded: true, error: (e as Error).message });
    }
  },

  open: async (path, name) => {
    try {
      await api.post<WorkspaceInfo>("/workspace", { path, name });
      await get().load();
      return true;
    } catch (e) {
      set({ error: (e as Error).message });
      return false;
    }
  },

  chooseAnother: () => set({ current: null, error: null }),

  /** Cria a pasta do projeto no workspace atual; devolve o caminho absoluto de saída. */
  createProject: async (body) => {
    const current = get().current;
    if (!current) {
      set({ error: "Escolha um workspace antes de criar o projeto." });
      return null;
    }
    try {
      const created = await api.post<{ folder: string; output_path: string }>("/workspace/projects", {
        workspace: current.path,
        ...body,
      });
      await get().load();
      return created.output_path;
    } catch (e) {
      set({ error: (e as Error).message });
      return null;
    }
  },
}));
