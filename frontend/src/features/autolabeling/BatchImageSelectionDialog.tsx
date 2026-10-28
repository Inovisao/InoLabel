import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { api } from "../../shared/api/client";

interface FrameChoice {
  index: number;
  filename: string;
  relative_path: string;
}

interface FramePage {
  frames: FrameChoice[];
  total: number;
}

interface Props {
  open: boolean;
  selectedIndices: number[];
  onApply: (indices: number[]) => void;
  onClose: () => void;
}

const PAGE_SIZE = 100;

export default function BatchImageSelectionDialog({ open, selectedIndices, onApply, onClose }: Props) {
  const [frames, setFrames] = useState<FrameChoice[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set(selectedIndices));
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectingAll, setSelectingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setSelected(new Set(selectedIndices));
      setOffset(0);
      setQuery("");
      setError(null);
    }
  }, [open, selectedIndices]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ offset: String(offset), limit: String(PAGE_SIZE), query });
      setLoading(true);
      api.get<FramePage>(`/frames/list?${params}`).then((result) => {
        if (cancelled) return;
        setFrames(result.frames);
        setTotal(result.total);
        setError(null);
      }).catch((e) => {
        if (!cancelled) setError((e as Error).message);
      }).finally(() => {
        if (!cancelled) setLoading(false);
      });
    }, query ? 200 : 0);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [open, query, offset]);

  const selectAllMatches = async () => {
    if (!total || selectingAll) return;
    const search = query;
    setSelectingAll(true);
    try {
      const indices: number[] = [];
      for (let start = 0; start < total; start += 500) {
        const params = new URLSearchParams({ offset: String(start), limit: "500", query: search });
        const result = await api.get<FramePage>(`/frames/list?${params}`);
        indices.push(...result.frames.map((item) => item.index));
      }
      setSelected((current) => new Set([...current, ...indices]));
    } catch (e) {
      setError((e as Error).message);
    } finally { setSelectingAll(false); }
  };
  const toggleFrame = (index: number) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    return next;
  });

  return <Dialog.Root open={open} onOpenChange={(value) => !value && onClose()}>
    <Dialog.Portal>
      <Dialog.Overlay className="modal-overlay" />
      <Dialog.Content className="modal-content" style={{ width: "min(1000px, calc(100vw - 32px))", maxHeight: "90vh", display: "flex", flexDirection: "column" }}>
        <header style={{ padding: "22px 26px 16px", borderBottom: "1px solid var(--color-border)" }}>
          <Dialog.Title style={{ margin: 0, fontSize: 18, color: "var(--color-text)" }}>Selecionar imagens para o lote</Dialog.Title>
          <Dialog.Description className="text-helper" style={{ display: "block", marginTop: 6 }}>
            Escolha as imagens para gerar sugestões. Os arquivos originais não serão alterados.
          </Dialog.Description>
        </header>

        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "14px 26px", flexWrap: "wrap" }}>
          <input className="input" value={query} placeholder="Buscar por nome ou pasta" aria-label="Buscar imagens" disabled={selectingAll}
            onChange={(event) => { setQuery(event.target.value); setOffset(0); }} style={{ flex: "1 1 260px" }} />
          <button className="btn-secondary" disabled={!total || loading || selectingAll} onClick={selectAllMatches}>
            {selectingAll ? "Selecionando…" : `Selecionar todas encontradas (${total})`}
          </button>
          <span className="text-helper">{selected.size} selecionadas</span>
        </div>

        {error && <p role="alert" className="alert alert-error" style={{ margin: "0 26px 12px" }}>{error}</p>}
        <div aria-busy={loading} style={{ overflowY: "auto", padding: "0 26px 18px", minHeight: 180 }}>
          {!loading && !frames.length && !error && <p className="text-helper">Nenhuma imagem encontrada.</p>}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 12 }}>
            {frames.map((item) => {
              const checked = selected.has(item.index);
              return <button key={item.index} type="button" aria-pressed={checked}
                onClick={() => toggleFrame(item.index)}
                style={{ textAlign: "left", overflow: "hidden", padding: 0, borderRadius: 8,
                  border: `2px solid ${checked ? "var(--color-primary)" : "var(--color-border)"}`,
                  background: "var(--color-panel)", color: "var(--color-text)", cursor: "pointer" }}>
                <div style={{ height: 116, background: "var(--color-canvas-bg, #eef2f7)", display: "grid", placeItems: "center" }}>
                  <img loading="lazy" src={`/api/frames/${item.index}/thumbnail`} alt=""
                    style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                </div>
                <div style={{ padding: "8px 10px", display: "flex", gap: 8, alignItems: "flex-start" }}>
                  <span aria-hidden="true" style={{ width: 16, height: 16, flex: "0 0 16px", marginTop: 2,
                    borderRadius: 4, border: `1px solid ${checked ? "var(--color-primary)" : "var(--color-border)"}`,
                    background: checked ? "var(--color-primary)" : "transparent", color: "white", fontSize: 12,
                    lineHeight: "14px", textAlign: "center" }}>{checked ? "✓" : ""}</span>
                  <span style={{ minWidth: 0, overflowWrap: "anywhere", fontSize: 12 }}>
                    <strong>Imagem {item.index + 1}</strong><br />{item.relative_path || item.filename}
                  </span>
                </div>
              </button>;
            })}
          </div>
        </div>

        <footer style={{ padding: "14px 26px 20px", borderTop: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button className="btn-secondary" disabled={offset === 0 || loading || selectingAll} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Anterior</button>
            <span className="text-helper">{total ? offset + 1 : 0}–{Math.min(offset + PAGE_SIZE, total)} de {total}</span>
            <button className="btn-secondary" disabled={offset + PAGE_SIZE >= total || loading || selectingAll} onClick={() => setOffset(offset + PAGE_SIZE)}>Próxima</button>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-secondary" onClick={onClose}>Cancelar</button>
            <button className="btn-primary" disabled={selected.size === 0} onClick={() => { onApply([...selected].sort((a, b) => a - b)); onClose(); }}>
              Usar {selected.size} imagens
            </button>
          </div>
        </footer>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
