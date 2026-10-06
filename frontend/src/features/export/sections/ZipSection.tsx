import CheckboxRow from "./CheckboxRow";

interface Props {
  enabled: boolean;
  onEnabled: (enabled: boolean) => void;
  datasetName: string;
  disabled: boolean;
}

/** Pacote .zip com imagens e anotações, depois de conferir as referências. */
export default function ZipSection({ enabled, onEnabled, datasetName, disabled }: Props) {
  return (
    <div>
      <CheckboxRow label="Gerar também um pacote .zip" checked={enabled} disabled={disabled} onChange={onEnabled} />
      <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 4, marginLeft: 22 }}>
        Imagens e anotações juntas em {datasetName || "dataset"}.zip, com as referências conferidas.
      </div>
    </div>
  );
}
