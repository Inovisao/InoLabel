import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import type { ExportProgress } from "../../shared/api/types";
import type { ExportState } from "./types";

const POLL_MS = 500;

/** Dispara a exportação no servidor e acompanha o progresso até terminar. */
export function useExportJob(open: boolean) {
  const [state, setState] = useState<ExportState>("idle");
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [zipPath, setZipPath] = useState("");

  // Fechar o modal volta ao formulário na próxima vez.
  useEffect(() => {
    if (!open) {
      setState("idle");
      setProgress(0);
      setCurrentFile("");
      setErrorMsg("");
      setZipPath("");
    }
  }, [open]);

  const fail = (message: string) => {
    setState("error");
    setErrorMsg(message);
  };

  const start = async (body: object) => {
    setState("running");
    setProgress(0);
    setCurrentFile("");
    setZipPath("");
    try {
      const { export_id } = await api.post<{ export_id: string }>("/export", body);
      const poll = setInterval(async () => {
        try {
          const prog = await api.get<ExportProgress>(`/export/${export_id}/progress`);
          setProgress(prog.progress);
          if (prog.current_file) setCurrentFile(prog.current_file);
          if (prog.status === "done") {
            clearInterval(poll);
            setZipPath(prog.zip_path ?? "");
            setState("done");
          } else if (prog.status === "error") {
            clearInterval(poll);
            fail(prog.current_file || "Erro desconhecido");
          }
        } catch {
          clearInterval(poll);
          fail("Falha ao verificar progresso.");
        }
      }, POLL_MS);
    } catch (e) {
      fail((e as Error).message);
    }
  };

  return { state, progress, currentFile, errorMsg, zipPath, start };
}
