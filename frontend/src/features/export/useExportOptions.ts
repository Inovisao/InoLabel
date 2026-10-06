import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import type { AugmentationOption, TaskMode } from "../../shared/api/types";
import { DEFAULT_SPLIT, isSplitValid, rebalance, toRatios } from "./split";
import type { CocoLayout, ExportFormat, SplitValues } from "./types";

/** Keypoint: espelhar não troca os nomes dos pontos (esquerda vira direita), então fica fora do padrão. */
const defaultAugmentations = (mode: TaskMode | null) =>
  mode === "keypoint" ? ["brightness", "contrast"] : ["flip_h", "brightness", "contrast"];

const toggle = <T,>(list: T[], item: T) => (list.includes(item) ? list.filter((x) => x !== item) : [...list, item]);

/** Opções do formulário de exportação e as regras entre elas. */
export function useExportOptions(open: boolean, mode: TaskMode | null, outputPath: string | null) {
  const [formats, setFormats] = useState<ExportFormat[]>(["yolo", "coco"]);
  const [cocoLayout, setCocoLayout] = useState<CocoLayout>("roboflow");
  const [destination, setDestination] = useState("");
  const [name, setName] = useState("dataset_export");
  const [useSplit, setUseSplitState] = useState(false);
  const [split, setSplit] = useState<SplitValues>(DEFAULT_SPLIT);
  const [augment, setAugmentState] = useState(false);
  const [augCatalog, setAugCatalog] = useState<AugmentationOption[]>([]);
  const [augKeys, setAugKeys] = useState<string[]>(defaultAugmentations(mode));
  const [augCopies, setAugCopies] = useState(1);
  const [zipOutput, setZipOutput] = useState(true);

  // Destino padrão: <pasta do projeto>/exports.
  useEffect(() => {
    if (open && !destination && outputPath) {
      setDestination(`${outputPath.replace(/[\\/]+$/, "")}/exports`);
    }
  }, [open, outputPath]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open || augCatalog.length) return;
    api.get<AugmentationOption[]>("/export/augmentations").then(setAugCatalog).catch(() => setAugCatalog([]));
  }, [open, augCatalog.length]);

  /** Sem divisão não há treino, e as cópias aumentadas só entram no treino. */
  const setUseSplit = (value: boolean) => {
    setUseSplitState(value);
    if (!value) setAugmentState(false);
  };
  const setAugment = (value: boolean) => {
    setAugmentState(value);
    if (value) setUseSplitState(true);
  };

  const isValid =
    !!destination.trim() &&
    !!name.trim() &&
    formats.length > 0 &&
    (!augment || augKeys.length > 0) &&
    (!useSplit || isSplitValid(split));

  /** Corpo do POST /api/export (sem o session_id). */
  const requestBody = () => ({
    destination,
    name,
    formats,
    use_split: useSplit,
    split: toRatios(useSplit, split),
    zip: zipOutput,
    coco_layout: cocoLayout,
    augmentation: augment,
    augmentations: augment ? augKeys : [],
    augmentation_copies: augCopies,
  });

  return {
    formats,
    toggleFormat: (f: ExportFormat) => setFormats((prev) => toggle(prev, f)),
    cocoLayout,
    setCocoLayout,
    destination,
    setDestination,
    name,
    setName,
    useSplit,
    setUseSplit,
    split,
    adjustSplit: (key: keyof SplitValues, value: number) => setSplit((prev) => rebalance(prev, key, value)),
    augment,
    setAugment,
    augCatalog,
    augKeys,
    toggleAug: (key: string) => setAugKeys((prev) => toggle(prev, key)),
    augCopies,
    setAugCopies,
    zipOutput,
    setZipOutput,
    isValid,
    requestBody,
  };
}

export type ExportOptions = ReturnType<typeof useExportOptions>;
