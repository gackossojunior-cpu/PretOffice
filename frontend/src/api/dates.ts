import { format, parseISO } from "date-fns";
import { fr } from "date-fns/locale";

export function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return format(parseISO(value), "d MMM yyyy", { locale: fr });
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return format(parseISO(value), "d MMM yyyy 'à' HH:mm", { locale: fr });
}
