import { AlertCircle, CheckCircle } from "lucide-react";
import type { ExportState } from "../types";

interface Props {
  state: ExportState;
  progress: number;
  currentFile: string;
  errorMsg: string;
  savedAt: string;
  zipPath: string;
}

/** Resultado (sucesso/erro) ou barra de progresso da exportação. */
export default function ExportStatus({ state, progress, currentFile, errorMsg, savedAt, zipPath }: Props) {
  if (state === "done") {
    return (
      <div className="alert alert-success">
        <CheckCircle size={20} color="var(--alert-icon)" style={{ flexShrink: 0 }} />
        <div>
          <div className="alert-title">Dataset exportado com sucesso!</div>
          <div className="alert-text">Salvo em: {savedAt}</div>
          {zipPath && <div className="alert-text">Pacote zipado: {zipPath}</div>}
        </div>
      </div>
    );
  }
  if (state === "error") {
    return (
      <div className="alert alert-error">
        <AlertCircle size={20} color="var(--alert-icon)" style={{ flexShrink: 0 }} />
        <div>
          <div className="alert-title">Erro na exportação</div>
          <div className="alert-text">{errorMsg}</div>
        </div>
      </div>
    );
  }
  if (state !== "running") return null;
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--color-muted)", marginBottom: 6 }}>
        <span>{currentFile || "Exportando…"}</span>
        <span>{Math.round(progress * 100)}%</span>
      </div>
      <div style={{ height: 6, background: "var(--color-border)", borderRadius: 999, overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${progress * 100}%`,
            background: "var(--color-primary)",
            borderRadius: 999,
            transition: "width var(--motion-slow)",
          }}
        />
      </div>
    </div>
  );
}
