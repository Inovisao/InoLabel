export type ExportFormat = "yolo" | "coco";
export type ExportState = "idle" | "running" | "done" | "error";
export type CocoLayout = "roboflow" | "images_dir";

/** Percentuais de train/val/test (somam 100). */
export interface SplitValues {
  train: number;
  val: number;
  test: number;
}
