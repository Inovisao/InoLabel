import { create } from "zustand";
import { api } from "../api/client";
import type { SessionStartRequest, SessionStatus, TaskMode } from "../api/types";

interface SessionState {
  active: boolean;
  sessionId: string | null;
  mode: TaskMode | null;
  classes: string[];
  totalFrames: number;
  currentIndex: number;
  loading: boolean;
  error: string | null;
  start: (req: SessionStartRequest) => Promise<void>;
  stop: () => Promise<void>;
  recover: () => Promise<void>;
}

export const useSessionStore = create<SessionState>((set) => ({
  active: false,
  sessionId: null,
  mode: null,
  classes: [],
  totalFrames: 0,
  currentIndex: 0,
  loading: false,
  error: null,

  start: async (req) => {
    set({ loading: true, error: null });
    try {
      // Garante que qualquer sessão anterior seja encerrada antes de iniciar
      await api.post("/session/stop").catch(() => {});
      const status = await api.post<SessionStatus>("/session/start", req);
      await api.get("/frames/init");
      set({
        active: status.active,
        sessionId: status.session_id ?? null,
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
    set({ active: false, sessionId: null, mode: null, classes: [], totalFrames: 0 });
  },

  recover: async () => {
    try {
      const status = await api.get<SessionStatus>("/session/status");
      if (status.active && status.session_id) {
        set({
          active: true,
          sessionId: status.session_id,
          mode: (status.mode ?? null) as TaskMode | null,
          classes: status.classes,
          totalFrames: status.total_frames,
          currentIndex: status.current_index,
        });
      }
    } catch {
      // no active session on server — nothing to recover
    }
  },
}));
