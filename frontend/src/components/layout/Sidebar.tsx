import { useEffect, useMemo, useState } from "react";
import { useAnnotationStore } from "../../stores/annotation";
import { useSessionStore } from "../../stores/session";
import type { ClassItem } from "../../api/types";

/** Id do campo de busca de classes; o atalho "/" foca nele. */
export const CLASS_SEARCH_ID = "class-search";

export default function Sidebar() {
  const {
    frame,
    classes,
    selectedClassId,
    setSelectedClass,
    classifyFrame,
    nextFrame,
    classKeyBuffer,
    tool,
    setTool,
    undo,
    undoStack,
    toggleReviewed,
  } = useAnnotationStore();
  const mode = useSessionStore((s) => s.mode);
  const isClassification = mode === "classification";
  const [query, setQuery] = useState("");

  // O atalho de cada classe é a posição dela na lista (1..N).
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return classes
      .map((cls, i) => ({ cls, shortcut: i + 1 }))
      .filter(({ cls, shortcut }) => !q || cls.name.toLowerCase().includes(q) || String(shortcut) === q);
  }, [classes, query]);

  const choose = async (cls: ClassItem) => {
    if (!isClassification) {
      setSelectedClass(cls.id);
      return;
    }
    const result = await classifyFrame(cls.id);
    if (result) {
      setQuery("");
      nextFrame();
    }
  };

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
      <div className="sidebar-label">
        {isClassification ? "Classificar como" : "Classes"}
      </div>

      {classes.length > 6 && (
        <div style={{ padding: "0 8px 6px" }}>
          <input
            id={CLASS_SEARCH_ID}
            className="input"
            placeholder="Buscar classe ( / )"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && filtered[0]) {
                e.preventDefault();
                choose(filtered[0].cls);
              } else if (e.key === "Escape") {
                setQuery("");
                (e.target as HTMLInputElement).blur();
              }
            }}
            style={{ width: "100%", height: 32, fontSize: 13 }}
          />
        </div>
      )}

      {isClassification && classKeyBuffer && (
        <div className="text-helper" style={{ padding: "0 18px 6px" }}>
          Digitando: <strong className="text-mono">{classKeyBuffer}</strong> · Enter confirma
        </div>
      )}

      <div
        style={{
          padding: "0 8px",
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        {filtered.map(({ cls, shortcut }) => {
          // Na classificação o destaque é a classe já atribuída ao frame.
          const active = isClassification
            ? frame?.classification_id === cls.id
            : selectedClassId === cls.id;
          return (
            <button
              key={cls.id}
              className={`nav-item ${active ? "nav-item-active" : ""}`}
              onClick={() => choose(cls)}
              title={isClassification ? `Classificar como ${cls.name} e avançar` : `Desenhar caixas de ${cls.name}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                minHeight: 36,
                padding: "7px 10px",
                border: "1px solid transparent",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                textAlign: "left",
                width: "100%",
                fontFamily: "var(--font-sans)",
              }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: cls.color ?? "var(--color-primary)",
                  flexShrink: 0,
                  boxShadow: active
                    ? `0 0 0 2px var(--color-panel), 0 0 0 3px ${cls.color ?? "var(--color-primary)"}`
                    : "none",
                  transition: "box-shadow 120ms",
                }}
              />
              <span
                style={{
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  color: active ? "var(--color-primary)" : "var(--color-sidebar-text)",
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {cls.name}
              </span>
              <Kbd>{String(shortcut)}</Kbd>
            </button>
          );
        })}

        {classes.length === 0 && (
          <p className="text-helper" style={{ padding: "8px 10px", fontStyle: "italic" }}>
            Nenhuma classe carregada.
          </p>
        )}
        {classes.length > 0 && filtered.length === 0 && (
          <p className="text-helper" style={{ padding: "8px 10px", fontStyle: "italic" }}>
            Nenhuma classe com “{query}”.
          </p>
        )}
      </div>

      {!isClassification && <SelectionPanel />}
      {mode === "tracking" && <TrackIdPanel />}

      <div className="divider" />
      <div className="sidebar-label">Ferramentas</div>

      <div style={{ padding: "0 8px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
        {isClassification ? (
          <ToolButton label="Pular frame" shortcut="Espaço" onClick={() => nextFrame()} />
        ) : (
          <>
            <ToolButton label="Caixa delimitadora" shortcut="B" active={tool === "box"} onClick={() => setTool("box")} />
            <ToolButton label="Selecionar / mover" shortcut="V" active={tool === "select"} onClick={() => setTool("select")} />
            <ToolButton
              label={frame?.reviewed ? "Frame revisado (desmarcar)" : "Frame sem objetos"}
              shortcut="N"
              active={!!frame?.reviewed}
              onClick={() => toggleReviewed()}
            />
          </>
        )}
        <ToolButton label="Desfazer" shortcut="Ctrl+Z" disabled={undoStack.length === 0} onClick={() => undo()} />
      </div>
    </aside>
  );
}

/** Edita a caixa selecionada: classe, ID (tracking) e remoção. */
function SelectionPanel() {
  const { frame, classes, selectedAnnotationId, updateAnnotation, removeAnnotation, fetchNextTrackId } =
    useAnnotationStore();
  const mode = useSessionStore((s) => s.mode);
  const ann = frame?.annotations.find((a) => a.id === selectedAnnotationId);
  const [idText, setIdText] = useState("");

  useEffect(() => {
    setIdText(ann?.track_id != null ? String(ann.track_id) : "");
  }, [ann?.id, ann?.track_id]);

  if (!ann) return null;

  const commitId = () => {
    const value = idText.trim() === "" ? null : Number(idText);
    if (value !== (ann.track_id ?? null)) updateAnnotation(ann.id, { track_id: value });
  };

  return (
    <>
      <div className="divider" />
      <div className="sidebar-label">Caixa selecionada</div>
      <div style={{ padding: "0 12px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
        <label className="text-helper" htmlFor="sel-class">Classe</label>
        <select
          id="sel-class"
          className="input"
          value={ann.category_id}
          onChange={(e) => updateAnnotation(ann.id, { category_id: Number(e.target.value) })}
          style={{ height: 32, fontSize: 13 }}
        >
          {classes.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        {mode === "tracking" && (
          <>
            <label className="text-helper" htmlFor="sel-track">ID do objeto</label>
            <div style={{ display: "flex", gap: 6 }}>
              <input
                id="sel-track"
                className="input text-mono"
                inputMode="numeric"
                value={idText}
                onChange={(e) => setIdText(e.target.value.replace(/\D/g, ""))}
                onBlur={commitId}
                onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
                style={{ flex: 1, height: 32, fontSize: 13 }}
              />
              <button
                className="btn-secondary"
                style={{ height: 32, fontSize: 12, whiteSpace: "nowrap" }}
                onClick={async () => {
                  const next = await fetchNextTrackId();
                  if (next !== null) updateAnnotation(ann.id, { track_id: next });
                }}
              >
                Novo ID
              </button>
            </div>
          </>
        )}

        <button
          className="btn-secondary"
          style={{ height: 32, fontSize: 12, color: "var(--color-danger)" }}
          onClick={() => removeAnnotation(ann.id)}
        >
          Remover caixa (Del)
        </button>
      </div>
    </>
  );
}

/** Qual ID as próximas caixas recebem: o próximo livre ou um ID fixado. */
function TrackIdPanel() {
  const { pinnedTrackId, setPinnedTrackId, fetchNextTrackId, frame } = useAnnotationStore();
  const [nextFree, setNextFree] = useState<number | null>(null);
  const [text, setText] = useState("");

  // Recalcula o próximo livre quando as caixas mudam.
  useEffect(() => {
    fetchNextTrackId().then(setNextFree);
  }, [frame?.index, frame?.annotations, fetchNextTrackId]);

  useEffect(() => {
    setText(pinnedTrackId != null ? String(pinnedTrackId) : "");
  }, [pinnedTrackId]);

  return (
    <>
      <div className="divider" />
      <div className="sidebar-label">ID das próximas caixas</div>
      <div style={{ padding: "0 12px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            className="input text-mono"
            inputMode="numeric"
            placeholder={nextFree != null ? `automático (${nextFree})` : "automático"}
            value={text}
            onChange={(e) => setText(e.target.value.replace(/\D/g, ""))}
            onBlur={() => setPinnedTrackId(text === "" ? null : Number(text))}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
            style={{ flex: 1, height: 32, fontSize: 13 }}
            aria-label="ID fixo para as próximas caixas"
          />
          {pinnedTrackId != null && (
            <button className="btn-secondary" style={{ height: 32, fontSize: 12 }} onClick={() => setPinnedTrackId(null)}>
              Automático
            </button>
          )}
        </div>
        <span className="text-helper">
          {pinnedTrackId != null
            ? `Fixado: toda caixa nova recebe o ID ${pinnedTrackId} (siga o mesmo objeto entre frames).`
            : "Vazio: cada caixa nova recebe o próximo ID livre."}
        </span>
      </div>
    </>
  );
}

function Kbd({ children }: { children: string }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontFamily: "var(--font-mono)",
        color: "var(--color-muted)",
        background: "var(--color-neutral)",
        border: "1px solid var(--color-border)",
        borderRadius: 4,
        padding: "1px 5px",
        flexShrink: 0,
      }}
    >
      {children}
    </span>
  );
}

function ToolButton({
  label,
  shortcut,
  onClick,
  active,
  disabled,
}: {
  label: string;
  shortcut: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      className={`nav-item ${active ? "nav-item-active" : ""}`}
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 10px",
        borderRadius: "var(--radius-md)",
        border: "1px solid transparent",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.5 : 1,
        fontSize: 13,
        width: "100%",
        fontFamily: "var(--font-sans)",
        textAlign: "left",
      }}
    >
      <span>{label}</span>
      <Kbd>{shortcut}</Kbd>
    </button>
  );
}
