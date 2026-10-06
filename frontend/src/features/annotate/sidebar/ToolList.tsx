import { useSessionStore } from "../../../shared/session/store";
import { useAnnotationStore } from "../store";
import ToolButton from "./ToolButton";
import { activeBinds, useKeybindStore } from "../../keybinds/store";

/** Ferramentas da anotação (clicáveis e com o atalho ao lado). */
export default function ToolList() {
  const { frame, tool, setTool, undo, undoStack, toggleReviewed, nextFrame } = useAnnotationStore();
  const mode = useSessionStore((s) => s.mode);
  const binds = useKeybindStore((s) => activeBinds(s.data));

  return (
    <>
      <div className="divider" />
      <div className="sidebar-label">Ferramentas</div>

      <div style={{ padding: "0 8px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
        {mode === "classification" ? (
          <ToolButton label="Pular frame" shortcut={binds.classification_skip.join(" / ")} onClick={() => nextFrame()} />
        ) : (
          <>
            <ToolButton
              label={mode === "keypoint" ? "Marcar pontos" : "Caixa delimitadora"}
              shortcut={binds.tool_box.join(" / ")}
              active={tool === "box"}
              onClick={() => setTool("box")}
            />
            <ToolButton label="Selecionar / mover" shortcut={binds.tool_select.join(" / ")} active={tool === "select"} onClick={() => setTool("select")} />
            <ToolButton
              label={frame?.reviewed ? "Frame revisado (desmarcar)" : "Frame sem objetos"}
              shortcut={binds.mark_negative.join(" / ")}
              active={!!frame?.reviewed}
              onClick={() => toggleReviewed()}
            />
          </>
        )}
        <ToolButton label="Desfazer" shortcut={binds.undo.join(" / ")} disabled={undoStack.length === 0} onClick={() => undo()} />
      </div>
    </>
  );
}
