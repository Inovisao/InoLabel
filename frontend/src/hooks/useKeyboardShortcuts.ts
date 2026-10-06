import { useEffect } from "react";
import { useAnnotationStore } from "../stores/annotation";
import { useSessionStore } from "../stores/session";
import { CLASS_SEARCH_ID } from "../components/layout/Sidebar";

interface Options {
  onSave?: () => void;
  onExport?: () => void;
  onSettings?: () => void;
}

export function useKeyboardShortcuts(options: Options = {}) {
  const mode = useSessionStore((s) => s.mode);
  const { onSave, onExport, onSettings } = options;

  useEffect(() => {
    // Estado lido na hora da tecla (getState) para não religar o listener a cada mudança.
    const store = useAnnotationStore.getState;

    const classifyAndAdvance = async (position: number) => {
      const { classes, classifyFrame, nextFrame } = store();
      const classItem = classes[position - 1];
      if (!classItem) return;
      const result = await classifyFrame(classItem.id);
      if (result) nextFrame();
    };

    /** Atalho numérico da classificação: 1..N; com mais de 9 classes, digita e confirma. */
    const handleClassDigit = (digit: string) => {
      const { classes, classKeyBuffer, setClassKeyBuffer } = store();
      const total = classes.length;
      if (total <= 9) {
        if (digit !== "0") classifyAndAdvance(Number(digit));
        return;
      }
      const typed = classKeyBuffer + digit;
      const value = Number(typed);
      if (value < 1 || value > total) {
        setClassKeyBuffer("");
        return;
      }
      // Confirma sozinho quando nenhum outro número pode começar assim (ex.: 7 de 12).
      if (value * 10 > total) {
        setClassKeyBuffer("");
        classifyAndAdvance(value);
      } else {
        setClassKeyBuffer(typed);
      }
    };

    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      const s = store();

      // Ctrl shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case "s":
            e.preventDefault();
            onSave?.();
            return;
          case "e":
            e.preventDefault();
            onExport?.();
            return;
          case "z":
            e.preventDefault();
            // Keypoint com instância em andamento: desfaz o último ponto, não a última ação.
            if (!s.kpUndoPoint()) s.undo();
            return;
          case ",":
            e.preventDefault();
            onSettings?.();
            return;
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

      if (mode === "classification") {
        if (/^[0-9]$/.test(e.key)) {
          e.preventDefault();
          handleClassDigit(e.key);
          return;
        }
        if (s.classKeyBuffer) {
          if (e.key === "Enter") {
            e.preventDefault();
            const value = Number(s.classKeyBuffer);
            s.setClassKeyBuffer("");
            classifyAndAdvance(value);
            return;
          }
          if (e.key === "Backspace") {
            e.preventDefault();
            s.setClassKeyBuffer(s.classKeyBuffer.slice(0, -1));
            return;
          }
          if (e.key === "Escape") {
            s.setClassKeyBuffer("");
            return;
          }
        }
        if (e.key === " ") {
          e.preventDefault();
          s.nextFrame();
          return;
        }
      } else {
        // Keypoint (atalhos da 1.0.0): X pula o ponto, C alterna visível/oculto,
        // F fecha a instância, Backspace desfaz o ponto, Esc cancela a instância.
        if (mode === "keypoint") {
          switch (e.key.toLowerCase()) {
            case "x":
              e.preventDefault();
              s.kpSkipPoint();
              return;
            case "c":
              e.preventDefault();
              s.kpToggleVisibility();
              return;
            case "f":
              e.preventDefault();
              s.kpFinish();
              return;
            case "backspace":
              e.preventDefault();
              s.kpUndoPoint();
              return;
            case "escape":
              if (s.kpWip) {
                s.kpCancel();
                return;
              }
              break;
          }
        }
        // OBB: Q/E giram a caixa selecionada (Shift = ajuste fino de 1°).
        if (mode === "obb" && s.selectedAnnotationId !== null && /^[qe]$/i.test(e.key)) {
          e.preventDefault();
          const step = e.shiftKey ? 1 : 5;
          s.rotateSelected({ delta: e.key.toLowerCase() === "q" ? -step : step });
          return;
        }
        switch (e.key) {
          case "b":
          case "B":
            s.setTool("box");
            return;
          case "v":
          case "V":
            s.setTool("select");
            return;
          case "n":
          case "N":
            e.preventDefault();
            s.toggleReviewed();
            return;
          case "Delete":
          case "Backspace":
            if (s.selectedAnnotationId !== null) {
              e.preventDefault();
              s.removeAnnotation(s.selectedAnnotationId);
            }
            return;
          case "Escape":
            s.selectAnnotation(null);
            return;
        }
      }

      // Navigation
      switch (e.key) {
        case "ArrowRight":
        case "d":
        case "D":
          e.preventDefault();
          s.setClassKeyBuffer("");
          s.nextFrame();
          break;
        case "ArrowLeft":
        case "a":
        case "A":
          e.preventDefault();
          s.setClassKeyBuffer("");
          s.prevFrame();
          break;
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, onSave, onExport, onSettings]);
}
