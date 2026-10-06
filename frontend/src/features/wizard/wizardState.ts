import type { TaskMode } from "../../shared/api/types";

export interface WizardState {
  mode: TaskMode;
  dataRoot: string;
  /** Pasta do projeto. Vazia em projeto novo: é criada no workspace a partir de projectName. */
  outputDir: string;
  projectName: string;
  classes: string[];
  weightsPath: string;
  confidence: number;
  resumeExisting: boolean;
  /** Modo keypoint: nomes dos pontos por classe, separados por vírgula. */
  keypointNames: Record<string, string>;
}

/** Mesmo padrão da 1.0.0 para uma classe nova. */
export const DEFAULT_KEYPOINTS = "top_left, top_right, bottom_right, bottom_left";

/** "a, b, a ,c" → ["a", "b", "c"] (sem vazios nem repetidos). */
export function parseKeypointNames(raw: string | undefined): string[] {
  const seen = new Set<string>();
  return (raw ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s && !seen.has(s) && (seen.add(s), true));
}

export const INITIAL_WIZARD_STATE: WizardState = {
  mode: "detection",
  dataRoot: "",
  outputDir: "",
  projectName: "",
  classes: [],
  weightsPath: "",
  confidence: 0.4,
  resumeExisting: false,
  keypointNames: {},
};
