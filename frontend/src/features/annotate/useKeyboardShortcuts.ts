import { useEffect } from "react";
import { useSessionStore } from "../../shared/session/store";
import { CLASS_SEARCH_ID } from "./sidebar/ClassList";
import { handlersFor } from "./shortcuts";
import { useAnnotationStore } from "./store";
import { activeBinds, useKeybindStore } from "../keybinds/store";
import { matches } from "../keybinds/keys";

interface Options {
  onSave?: () => void;
  onExport?: () => void;
  onSettings?: () => void;
}

/** Atalhos de teclado da anotação. Campos de texto ficam de fora. */
export function useKeyboardShortcuts(options: Options = {}) {
  const mode = useSessionStore((s) => s.mode);
  const binds = useKeybindStore((s) => activeBinds(s.data));
  const { onSave, onExport, onSettings } = options;

  useEffect(() => {
    const handlers = handlersFor(mode);

    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target as HTMLElement).isContentEditable) return;
      // Estado lido na hora da tecla, para não religar o listener a cada mudança.
      const s = useAnnotationStore.getState();

      if (matches(e, binds, "save")) { e.preventDefault(); onSave?.(); return; }
      if (matches(e, binds, "export")) { e.preventDefault(); onExport?.(); return; }
      if (matches(e, binds, "settings")) { e.preventDefault(); onSettings?.(); return; }
      if (matches(e, binds, "undo")) {
        e.preventDefault();
        if (!s.kpUndoPoint()) s.undo();
        return;
      }

      if (matches(e, binds, "search_class")) {
        const search = document.getElementById(CLASS_SEARCH_ID);
        if (search) {
          e.preventDefault();
          search.focus();
        }
        return;
      }

      for (const handle of handlers) {
        if (handle(e, s, binds)) return;
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, binds, onSave, onExport, onSettings]);
}
