import { useMemo, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../../../shared/api/client";
import type { ClassItem } from "../../../shared/api/types";
import { useSessionStore } from "../../../shared/session/store";
import ConfirmModal from "../../../shared/ui/ConfirmModal";
import Kbd from "../../../shared/ui/Kbd";
import { activeBinds, useKeybindStore } from "../../keybinds/store";
import { useAnnotationStore } from "../store";
import { parsePointNames, removalWarning } from "../store/classEdits";

/** Id do campo de busca de classes; o atalho "/" foca nele. */
export const CLASS_SEARCH_ID = "class-search";

interface Removal {
  cls: ClassItem;
  description: string;
}

/**
 * Classes da sessão com o atalho de cada uma (posição 1..N) e busca.
 * Na classificação, clicar classifica e avança; nos outros modos, escolhe a classe a desenhar.
 * Durante a anotação dá para adicionar classes e, fora da classificação (onde cada
 * classe é uma pasta com imagens), renomear e remover.
 */
export default function ClassList() {
  const {
    frame, classes, selectedClassId, setSelectedClass, classifyFrame, nextFrame, classKeyBuffer,
    addClass, renameClass, removeClass,
  } = useAnnotationStore();
  const mode = useSessionStore((s) => s.mode);
  const isClassification = mode === "classification";
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [removal, setRemoval] = useState<Removal | null>(null);
  const searchKey = useKeybindStore((s) => activeBinds(s.data).search_class.join(" / "));

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

  const askRemoval = async (cls: ClassItem) => {
    try {
      const usage = await api.get<{ annotations: number; frames: number }>(`/classes/${cls.id}/usage`);
      setRemoval({ cls, description: removalWarning(cls.name, usage.annotations, usage.frames) });
    } catch (e) {
      useAnnotationStore.setState({ error: (e as Error).message });
    }
  };

  return (
    <>
  <div className="sidebar-label" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
    <span>{isClassification ? "Classificar como" : "Classes"}</span>
    <button
      className="btn-icon-sm"
      onClick={() => setAdding(true)}
      title="Nova classe"
      aria-label="Nova classe"
    >
      <Plus size={14} />
    </button>
  </div>

  {adding && (
    <NewClassForm
      needsPoints={mode === "keypoint"}
      onCancel={() => setAdding(false)}
      onSubmit={async (name, points) => {
        if (await addClass(name, points)) setAdding(false);
      }}
    />
  )}

  {classes.length > 6 && (
    <div style={{ padding: "0 8px 6px" }}>
      <input
        id={CLASS_SEARCH_ID}
        className="input"
        placeholder={`Buscar classe (${searchKey})`}
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
      if (editingId === cls.id) {
        return (
          <NameInput
            key={cls.id}
            initial={cls.name}
            label={`Novo nome para ${cls.name}`}
            onCancel={() => setEditingId(null)}
            onSubmit={async (name) => {
              if (name === cls.name || (await renameClass(cls.id, name))) setEditingId(null);
            }}
          />
        );
      }
      return (
        <div key={cls.id} className="class-row">
        <button
          className={`nav-item ${active ? "nav-item-active" : ""}`}
          onClick={() => choose(cls)}
          onDoubleClick={() => !isClassification && setEditingId(cls.id)}
          title={isClassification ? `Classificar como ${cls.name} e avançar` : `Desenhar caixas de ${cls.name} (duplo clique renomeia)`}
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
        {!isClassification && (
          <div className="class-row-actions">
            <button className="btn-icon-sm" onClick={() => setEditingId(cls.id)} title={`Renomear ${cls.name}`} aria-label={`Renomear ${cls.name}`}>
              <Pencil size={13} />
            </button>
            <button
              className="btn-icon-sm"
              onClick={() => askRemoval(cls)}
              disabled={classes.length <= 1}
              title={classes.length <= 1 ? "O projeto precisa de ao menos uma classe" : `Remover ${cls.name}`}
              aria-label={`Remover ${cls.name}`}
            >
              <Trash2 size={13} />
            </button>
          </div>
        )}
        </div>
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

  <ConfirmModal
    open={removal !== null}
    title={removal ? `Remover a classe "${removal.cls.name}"?` : ""}
    description={removal?.description ?? ""}
    confirmLabel="Remover classe"
    danger
    onConfirm={async () => {
      if (removal) await removeClass(removal.cls.id);
      setRemoval(null);
    }}
    onCancel={() => setRemoval(null)}
  />
    </>
  );
}

/** Campo de nome: Enter confirma, Esc ou sair do campo cancela. */
function NameInput({ initial = "", label, onSubmit, onCancel }: {
  initial?: string;
  label: string;
  onSubmit: (name: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(initial);
  return (
    <input
      className="input"
      autoFocus
      aria-label={label}
      placeholder="Nome da classe"
      value={value}
      maxLength={100}
      onChange={(e) => setValue(e.target.value)}
      onFocus={(e) => e.target.select()}
      onKeyDown={(e) => {
        if (e.key === "Enter" && value.trim()) {
          e.preventDefault();
          onSubmit(value.trim());
        } else if (e.key === "Escape") {
          e.preventDefault();
          onCancel();
        }
      }}
      onBlur={onCancel}
      style={{ width: "100%", height: 34, fontSize: 13 }}
    />
  );
}

/** Nova classe; no modo keypoint pede também os pontos, separados por vírgula. */
function NewClassForm({ needsPoints, onSubmit, onCancel }: {
  needsPoints: boolean;
  onSubmit: (name: string, points: string[]) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [points, setPoints] = useState("");
  const ready = !!name.trim() && (!needsPoints || parsePointNames(points).length > 0);
  const submit = () => {
    if (ready) onSubmit(name.trim(), needsPoints ? parsePointNames(points) : []);
  };
  const keys = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  };
  return (
    <div
      style={{ padding: "0 8px 8px", display: "flex", flexDirection: "column", gap: 6 }}
      // Clicar fora sem ter digitado nada fecha o formulário.
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node) && !name.trim() && !points.trim()) onCancel();
      }}
    >
      <input
        className="input"
        autoFocus
        aria-label="Nome da nova classe"
        placeholder="Nome da nova classe"
        value={name}
        maxLength={100}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={keys}
        style={{ width: "100%", height: 34, fontSize: 13 }}
      />
      {needsPoints && (
        <input
          className="input"
          aria-label="Pontos da nova classe"
          placeholder="Pontos, separados por vírgula"
          value={points}
          onChange={(e) => setPoints(e.target.value)}
          onKeyDown={keys}
          style={{ width: "100%", height: 34, fontSize: 13 }}
        />
      )}
      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
        <button className="btn-secondary" style={{ padding: "4px 10px", fontSize: 12 }} onClick={onCancel}>Cancelar</button>
        <button className="btn-primary" style={{ padding: "4px 10px", fontSize: 12 }} onClick={submit} disabled={!ready}>Adicionar</button>
      </div>
    </div>
  );
}
