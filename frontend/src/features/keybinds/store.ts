import { create } from "zustand";
import { api } from "../../shared/api/client";
import { DEFAULT_PROFILES, type Binds, type Profiles } from "./defaults";

interface KeybindState {
  data: Profiles;
  loaded: boolean;
  error: string | null;
  load: () => Promise<void>;
  save: (data: Profiles) => Promise<void>;
}

export const useKeybindStore = create<KeybindState>((set) => ({
  data: DEFAULT_PROFILES(), loaded: false, error: null,
  load: async () => {
    try {
      const data = await api.get<Profiles>("/keybinds/profiles");
      set({ data, loaded: true, error: null });
    } catch (error) {
      set({ loaded: true, error: error instanceof Error ? error.message : String(error) });
    }
  },
  save: async (data) => {
    const saved = await api.put<Profiles>("/keybinds/profiles", data);
    set({ data: saved, error: null });
  },
}));

export const activeBinds = (data: Profiles): Binds => data.profiles[data.active_profile] ?? data.profiles["Padrão"];
