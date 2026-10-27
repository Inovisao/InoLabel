import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";

interface RuntimeInfo {
  python_version: string;
  executable: string;
  project_python: string;
  missing: string[];
  packages: Record<string, string | null>;
}

export default function RuntimeDiagnostics() {
  const [info, setInfo] = useState<RuntimeInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    api.get<RuntimeInfo>("/autolabeling/runtime")
      .then((result) => { if (!cancelled) setInfo(result); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="text-helper">Não foi possível verificar o ambiente: {error}</p>;
  if (!info) return null;
  return <details open={info.missing.length > 0}>
    <summary>Ambiente de inferência · Python {info.python_version}</summary>
    <div style={{ display: "grid", gap: 8, marginTop: 8, overflowWrap: "anywhere" }}>
      {info.missing.length > 0 && <div role="alert" className="alert alert-error">
        Dependências ausentes neste Python: {info.missing.join(", ")}.
        <p>Inicie o aplicativo no ambiente Python {info.project_python} do projeto, com as dependências instaladas.</p>
        <code>python -m pip install -r requirements.txt</code>
      </div>}
      <span className="text-helper">Interpretador: {info.executable}</span>
      {Object.entries(info.packages).map(([name, installed]) => <span key={name} className="text-helper">{name}: {installed ?? "não instalado"}</span>)}
    </div>
  </details>;
}
