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

export type AiEmphasis = "ninguno" | "ligero" | "medio";

export interface AiOptions {
  document_type: string;
  detect_titles: boolean;
  detect_lists: boolean;
  detect_tables: boolean;
  emphasis: AiEmphasis;
  accepted_disclaimer?: boolean;
}

