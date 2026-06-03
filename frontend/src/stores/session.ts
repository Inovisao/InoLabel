import { create } from "zustand";
import { api } from "../api/client";
import type { SessionStartRequest, SessionStatus, TaskMode } from "../api/types";

interface SessionState {
  active: boolean;
  mode: TaskMode | null;
  classes: string[];
  totalFrames: number;
  currentIndex: number;
  loading: boolean;
  error: string | null;
  start: (req: SessionStartRequest) => Promise<void>;
  stop: () => Promise<void>;
}

export const useSessionStore = create<SessionState>((set) => ({
  active: false,
  mode: null,
  classes: [],
  totalFrames: 0,
  currentIndex: 0,
  loading: false,
  error: null,

  start: async (req) => {
    set({ loading: true, error: null });
    try {
      const status = await api.post<SessionStatus>("/session/start", req);
      await api.get("/frames/init");
      set({
        active: status.active,
        mode: status.mode ?? null,
        classes: status.classes,
        totalFrames: status.total_frames,
        currentIndex: status.current_index,
        loading: false,
      });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  stop: async () => {
    await api.post("/session/stop");
    set({ active: false, mode: null, classes: [], totalFrames: 0 });
  },
}));
