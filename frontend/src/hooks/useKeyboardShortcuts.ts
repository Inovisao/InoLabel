import { useEffect } from "react";
import { useAnnotationStore } from "../stores/annotation";

interface Options {
  onSave?: () => void;
  onExport?: () => void;
  onSettings?: () => void;
}

export function useKeyboardShortcuts(options: Options = {}) {
  const { nextFrame, prevFrame } = useAnnotationStore();
  const { onSave, onExport, onSettings } = options;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      // Ctrl shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "s":
            e.preventDefault();
            onSave?.();
            return;
          case "e":
            e.preventDefault();
            onExport?.();
            return;
          case ",":
            e.preventDefault();
            onSettings?.();
            return;
        }
      }

      // Navigation
      switch (e.key) {
        case "ArrowRight":
        case "d":
        case "D":
          e.preventDefault();
          nextFrame();
          break;
        case "ArrowLeft":
        case "a":
        case "A":
          e.preventDefault();
          prevFrame();
          break;
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [nextFrame, prevFrame, onSave, onExport, onSettings]);
}
