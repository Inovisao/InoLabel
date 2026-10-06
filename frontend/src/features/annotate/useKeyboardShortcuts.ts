import { useEffect } from "react";
import { useSessionStore } from "../../shared/session/store";
import { CLASS_SEARCH_ID } from "./sidebar/ClassList";
import { handlersFor } from "./shortcuts";
import { useAnnotationStore } from "./store";

interface Options {
  onSave?: () => void;
  onExport?: () => void;
  onSettings?: () => void;
}

/** Atalhos de teclado da anotação. Campos de texto ficam de fora. */
export function useKeyboardShortcuts(options: Options = {}) {
  const mode = useSessionStore((s) => s.mode);
  const { onSave, onExport, onSettings } = options;

  useEffect(() => {
    const handlers = handlersFor(mode);

    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      // Estado lido na hora da tecla, para não religar o listener a cada mudança.
      const s = useAnnotationStore.getState();

      if (e.ctrlKey || e.metaKey) {
        const action: Record<string, (() => void) | undefined> = {
          s: onSave,
          e: onExport,
          ",": onSettings,
          // Keypoint com instância em andamento: desfaz o último ponto, não a última ação.
          z: () => {
            if (!s.kpUndoPoint()) s.undo();
          },
        };
        const key = e.key.toLowerCase();
        if (key in action) {
          e.preventDefault();
          action[key]?.();
        }
        return;
      }

      if (e.key === "/") {
        const search = document.getElementById(CLASS_SEARCH_ID);
        if (search) {
          e.preventDefault();
          search.focus();
        }
        return;
      }

      for (const handle of handlers) {
        if (handle(e, s)) return;
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, onSave, onExport, onSettings]);
}
