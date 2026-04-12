import Papa from "papaparse";
import type { ContactRow } from "./types";

export function parseContactsCsv(text: string): ContactRow[] {
  const { data } = Papa.parse<ContactRow>(text, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: false,
  });
  return (data || []).filter((r) => r && Object.keys(r).length > 0);
}
