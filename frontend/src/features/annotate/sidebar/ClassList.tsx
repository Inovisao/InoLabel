import { useMemo, useState } from "react";
import type { ClassItem } from "../../../shared/api/types";
import { useSessionStore } from "../../../shared/session/store";
import Kbd from "../../../shared/ui/Kbd";
import { useAnnotationStore } from "../store";

/** Id do campo de busca de classes; o atalho "/" foca nele. */
export const CLASS_SEARCH_ID = "class-search";

/**
 * Classes da sessão com o atalho de cada uma (posição 1..N) e busca.
 * Na classificação, clicar classifica e avança; nos outros modos, escolhe a classe a desenhar.
 */
export default function ClassList() {
  const { frame, classes, selectedClassId, setSelectedClass, classifyFrame, nextFrame, classKeyBuffer } =
    useAnnotationStore();
  const isClassification = useSessionStore((s) => s.mode) === "classification";
  const [query, setQuery] = useState("");

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
    <>
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
    </>
  );
}
