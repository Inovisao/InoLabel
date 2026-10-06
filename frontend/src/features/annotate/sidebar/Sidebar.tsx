import { useSessionStore } from "../../../shared/session/store";
import ClassList from "./ClassList";
import SelectionPanel from "./SelectionPanel";
import ToolList from "./ToolList";
import TrackIdPanel from "./TrackIdPanel";

/** Painel lateral da anotação: classes, anotação selecionada, ID do rastreamento e ferramentas. */
export default function Sidebar() {
  const mode = useSessionStore((s) => s.mode);

  return (
    <aside
      style={{
        width: 320,
        minWidth: 280,
        maxWidth: 360,
        flexShrink: 0,
        background: "var(--color-panel)",
        borderRight: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <ClassList />
      {mode !== "classification" && <SelectionPanel />}
      {mode === "tracking" && <TrackIdPanel />}
      <ToolList />
    </aside>
  );
}
