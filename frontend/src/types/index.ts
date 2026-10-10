export type ViewKey = "format" | "history" | "settings";

export type PresetId =
  | "classic"
  | "modern"
  | "corporate"
  | "minimal"
  | "editorial";

export interface HistoryItem {
  id: string;
  fileName: string;
  topic: string;
  preset: PresetId;
  date: string;
  size: number;
}
