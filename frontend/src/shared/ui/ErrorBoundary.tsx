import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
}

/**
 * Erro ao desenhar uma tela: mostra a mensagem e um jeito de sair, em vez de a página
 * ficar em branco (sem isso o React desmonta o app inteiro). A anotação já está salva no
 * backend; recarregar retoma o projeto, e encerrar a sessão volta ao início.
 */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Só a mensagem e a pilha de componentes: nada de dados do projeto.
    console.error("InoLabel: erro ao desenhar a tela", error.message, info.componentStack);
  }

  private endSession = async () => {
    await fetch("/api/session/stop", { method: "POST" }).catch(() => {});
    window.location.reload();
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div
        role="alert"
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          background: "var(--color-bg, #fff)",
          color: "var(--color-text, #111)",
          fontFamily: "var(--font-sans, sans-serif)",
        }}
      >
        <div style={{ maxWidth: 520, display: "flex", flexDirection: "column", gap: 14 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Algo deu errado ao abrir esta tela</h1>
          <p style={{ fontSize: 14, color: "var(--color-muted, #555)" }}>
            Suas anotações já estão salvas. Recarregue para tentar de novo, ou encerre a sessão para voltar ao início.
            Se o erro continuar, envie a mensagem abaixo para quem mantém o InoLabel.
          </p>
          <pre
            style={{
              fontSize: 12,
              padding: 12,
              borderRadius: 8,
              background: "var(--color-neutral, #f3f3f3)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {error.message}
          </pre>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn-primary" onClick={() => window.location.reload()}>Recarregar</button>
            <button className="btn-secondary" onClick={this.endSession}>Encerrar sessão</button>
          </div>
        </div>
      </div>
    );
  }
}
