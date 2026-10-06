import { Folder } from "lucide-react";
import { api } from "../../../shared/api/client";

interface Props {
  destination: string;
  onDestination: (path: string) => void;
  name: string;
  onName: (name: string) => void;
  disabled: boolean;
}

/** Pasta de destino (com o seletor do sistema) e nome do dataset. */
export default function DestinationSection({ destination, onDestination, name, onName, disabled }: Props) {
  const browse = async () => {
    try {
      const res = await api.get<{ path: string }>("/browse/folder");
      if (res.path) onDestination(res.path);
    } catch {
      /* seletor cancelado */
    }
  };

  return (
    <>
      <div>
        <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
          Pasta de destino
        </label>
        <span className="text-helper" style={{ display: "block", marginBottom: 6 }}>
          Por padrão, a pasta exports/ dentro do projeto.
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            className="input"
            style={{ flex: 1 }}
            placeholder="/caminho/para/exportar"
            value={destination}
            disabled={disabled}
            onChange={(e) => onDestination(e.target.value)}
          />
          <button
            className="btn-icon"
            type="button"
            onClick={browse}
            disabled={disabled}
            title="Selecionar pasta"
            style={{ width: 40, height: 40, color: "var(--color-primary)" }}
          >
            <Folder size={17} strokeWidth={1.75} />
          </button>
        </div>
      </div>

      <div>
        <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
          Nome do dataset
        </label>
        <input
          className="input"
          placeholder="dataset_export"
          value={name}
          disabled={disabled}
          onChange={(e) => onName(e.target.value)}
        />
      </div>
    </>
  );
}
