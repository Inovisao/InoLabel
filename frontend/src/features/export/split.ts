import type { SplitValues } from "./types";

export const DEFAULT_SPLIT: SplitValues = { train: 70, val: 20, test: 10 };
const KEYS: (keyof SplitValues)[] = ["train", "val", "test"];

export const splitTotal = (split: SplitValues) => split.train + split.val + split.test;

/** Aceita até 1 ponto de arredondamento. */
export const isSplitValid = (split: SplitValues) => Math.abs(splitTotal(split) - 100) <= 1;

/**
 * Muda uma fatia e redistribui o resto entre as outras duas, na proporção que elas
 * tinham (ou meio a meio, se as duas estavam em zero). O total continua 100.
 */
export function rebalance(prev: SplitValues, key: keyof SplitValues, value: number): SplitValues {
  const next = { ...prev, [key]: value };
  const others = KEYS.filter((k) => k !== key);
  const remaining = 100 - value;
  const othersTotal = others.reduce((s, k) => s + prev[k], 0);
  if (othersTotal === 0) {
    const each = Math.round(remaining / 2);
    others.forEach((k, i) => {
      next[k] = i === 0 ? each : remaining - each;
    });
    return next;
  }
  others.forEach((k) => {
    next[k] = Math.round((prev[k] / othersTotal) * remaining);
  });
  next[others[0]] += 100 - splitTotal(next);
  return next;
}

/** Frações enviadas à API; sem divisão, tudo vai para treino. */
export const toRatios = (useSplit: boolean, split: SplitValues) =>
  useSplit
    ? { train: split.train / 100, val: split.val / 100, test: split.test / 100 }
    : { train: 1.0, val: 0.0, test: 0.0 };
