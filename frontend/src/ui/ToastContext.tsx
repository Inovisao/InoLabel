import { createContext, useCallback, useContext, useRef, useState } from "react";
import { CheckCircle, XCircle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const dismiss = (id: number) =>
    setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Toast container */}
      <div
        style={{
          position: "fixed",
          bottom: 56,
          right: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          zIndex: 9999,
          pointerEvents: "none",
        }}
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} item={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const ICONS: Record<ToastType, React.ElementType> = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
};

const COLORS: Record<ToastType, { bg: string; icon: string; border: string }> = {
  success: { bg: "#F0FDF4", icon: "#22C55E", border: "#BBF7D0" },
  error:   { bg: "#FEF2F2", icon: "#EF4444", border: "#FECACA" },
  info:    { bg: "#EFF6FF", icon: "#3B82F6", border: "#BFDBFE" },
};

function ToastItem({
  item,
  onDismiss,
}: {
  item: ToastItem;
  onDismiss: (id: number) => void;
}) {
  const Icon = ICONS[item.type];
  const clr = COLORS[item.type];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        minWidth: 280,
        maxWidth: 400,
        padding: "12px 14px",
        background: clr.bg,
        border: `1px solid ${clr.border}`,
        borderRadius: "var(--radius-lg)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
        pointerEvents: "all",
        fontFamily: "var(--font-sans)",
      }}
    >
      <Icon size={18} color={clr.icon} style={{ flexShrink: 0 }} />
      <span style={{ flex: 1, fontSize: 14, color: "var(--color-text)", lineHeight: 1.4 }}>
        {item.message}
      </span>
      <button
        onClick={() => onDismiss(item.id)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--color-muted)",
          display: "flex",
          padding: 2,
          flexShrink: 0,
        }}
      >
        <X size={14} />
      </button>
    </div>
  );
}
