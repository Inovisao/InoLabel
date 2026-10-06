import { useEffect, useState } from "react";
import { Keyboard, Plus, Save, Trash2, RotateCcw, X } from "lucide-react";
import PageShell from "../../shared/layout/PageShell";
import { DEFAULT_PROFILES, freshDefaults, GROUPS, restoreDefaults, type Action, type Profiles } from "../keybinds/defaults";
import { conflict, keyForEvent, reserved, sameShortcut } from "../keybinds/keys";
import { useKeybindStore } from "../keybinds/store";

interface Props { activeNav: string; onNavigate: (id: string) => void }

export default function ShortcutsPage({ activeNav, onNavigate }: Props) {
  const { data, loaded, error: loadError, save } = useKeybindStore();
  const [draft, setDraft] = useState<Profiles>(DEFAULT_PROFILES);
  const [name, setName] = useState("");
  const [capturing, setCapturing] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (loaded) setDraft(structuredClone(data)); }, [data, loaded]);

  const current = draft.profiles[draft.active_profile] ?? freshDefaults();
  const editable = draft.active_profile !== "Padrão";
  const dirty = JSON.stringify(draft) !== JSON.stringify(data);

  function update(action: Action, keys: string[]) {
    setDraft((prev) => ({ ...prev, profiles: {
      ...prev.profiles,
      [prev.active_profile]: { ...prev.profiles[prev.active_profile], [action]: keys },
    } }));
    setMessage("");
  }

  function capture(event: React.KeyboardEvent<HTMLButtonElement>, action: Action, index: number) {
    event.preventDefault();
    event.stopPropagation();
    const key = keyForEvent(event.nativeEvent);
    if (!key) return;
    if (reserved(action, key)) {
      setMessage(`A tecla ${key} é reservada para digitar classes na classificação.`);
      return;
    }
    const existing = conflict(current, action, key);
    if (existing || current[action].some((value, i) => i !== index && sameShortcut(value, key))) {
      const label = GROUPS.flatMap((group) => group.actions).find((item) => item.id === existing)?.label ?? "esta ação";
      setMessage(`A tecla ${key} já está atribuída a ${label}.`);
      return;
    }
    const keys = [...current[action]];
    if (index === keys.length) keys.push(key);
    else keys[index] = key;
    update(action, keys);
    setCapturing(null);
  }

  function createProfile() {
    const next = name.trim();
    if (!next || next === "Padrão" || draft.profiles[next]) {
      setMessage("Informe um nome novo para o perfil.");
      return;
    }
    setDraft((prev) => ({ active_profile: next, profiles: { ...prev.profiles, [next]: structuredClone(current) } }));
    setName("");
    setMessage("");
  }

  async function persist() {
    setSaving(true);
    setMessage("");
    try {
      await save(draft);
      setMessage("Perfil salvo.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível salvar.");
    } finally {
      setSaving(false);
    }
  }

  if (!loaded) return <PageShell activeNav={activeNav} onNavigate={onNavigate} breadcrumb="Atalhos"><p className="text-helper">Carregando atalhos…</p></PageShell>;

  return (
    <PageShell activeNav={activeNav} onNavigate={(id) => {
      if (!dirty || window.confirm("Descartar alterações dos atalhos?")) onNavigate(id);
    }} breadcrumb="Atalhos">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <Keyboard size={24} color="var(--color-primary)" />
        <h1 className="text-display">Atalhos de teclado</h1>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 10, marginBottom: 18 }}>
        <label style={{ display: "grid", gap: 4, fontSize: 12, fontWeight: 600 }}>
          Perfil ativo
          <select className="input" value={draft.active_profile} onChange={(event) => { setDraft({ ...draft, active_profile: event.target.value }); setCapturing(null); setMessage(""); }}>
            {Object.keys(draft.profiles).map((profile) => <option key={profile}>{profile}</option>)}
          </select>
        </label>
        <label style={{ display: "grid", gap: 4, fontSize: 12, fontWeight: 600 }}>
          Novo perfil
          <input className="input" value={name} onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") createProfile(); }} maxLength={60} placeholder="Nome do perfil" />
        </label>
        <button className="btn-secondary" onClick={createProfile} title="Criar cópia do perfil ativo"><Plus size={16} /> Criar</button>
        {editable && <>
          <button className="btn-secondary" onClick={() => { setDraft({ ...draft, profiles: { ...draft.profiles, [draft.active_profile]: restoreDefaults(current, draft.profiles["Padrão"]) } }); setCapturing(null); setMessage(""); }} title="Restaurar teclas padrão deste perfil"><RotateCcw size={16} /> Restaurar</button>
          <button className="btn-secondary" onClick={() => { const profiles = { ...draft.profiles }; delete profiles[draft.active_profile]; setDraft({ active_profile: "Padrão", profiles }); setCapturing(null); }} title="Excluir perfil ativo"><Trash2 size={16} /> Excluir</button>
        </>}
        <button className="btn-primary" onClick={persist} disabled={!dirty || saving} title="Salvar perfis de atalhos"><Save size={16} /> {saving ? "Salvando" : "Salvar"}</button>
      </div>

      {(message || loadError) && <p role="status" style={{ color: message === "Perfil salvo." ? "var(--color-primary)" : "var(--color-error-text)", marginBottom: 12, fontSize: 13 }}>{message || `Não foi possível carregar os perfis: ${loadError}`}</p>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: "18px 30px" }}>
        {GROUPS.map((group) => <section key={group.title}>
          <h2 style={{ fontSize: 14, fontWeight: 700, paddingBottom: 8, borderBottom: "1px solid var(--color-border)" }}>{group.title}</h2>
          {group.actions.map(({ id, label }) => <div key={id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, minHeight: 46, borderBottom: "1px solid var(--color-border)", fontSize: 13 }}>
            <span style={{ minWidth: 0 }}>{label}</span>
            <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap", justifyContent: "end" }}>
              {current[id].map((key, index) => <span key={`${id}-${index}`} style={{ display: "inline-flex", alignItems: "center" }}>
                <button className="btn-secondary" style={{ minWidth: 42, padding: "4px 7px", fontFamily: "var(--font-mono)", fontSize: 11 }} disabled={!editable} onClick={() => { setCapturing(`${id}-${index}`); setMessage(""); }} onKeyDown={(event) => { if (capturing === `${id}-${index}`) capture(event, id, index); }} title={editable ? `Alterar atalho de ${label}` : "Crie um perfil para editar"}>{capturing === `${id}-${index}` ? "…" : key}</button>
                {editable && current[id].length > 1 && <button className="btn-icon" onClick={() => update(id, current[id].filter((_, i) => i !== index))} title={`Remover ${key}`} aria-label={`Remover ${key}`}><X size={13} /></button>}
              </span>)}
              {editable && current[id].length < 2 && <button className="btn-icon" onClick={() => { setCapturing(`${id}-${current[id].length}`); setMessage(""); }} onKeyDown={(event) => { if (capturing === `${id}-${current[id].length}`) capture(event, id, current[id].length); }} title={`Adicionar atalho para ${label}`} aria-label={`Adicionar atalho para ${label}`}><Plus size={15} /></button>}
            </div>
          </div>)}
        </section>)}
      </div>
      <p className="text-helper" style={{ marginTop: 20 }}>Na classificação, as teclas 1–9 escolhem a classe pela posição. Atalhos ficam inativos em campos de texto.</p>
    </PageShell>
  );
}
