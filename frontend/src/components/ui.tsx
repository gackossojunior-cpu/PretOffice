import type { PropsWithChildren, ReactNode } from "react";

import { Button as ShadcnButton } from "@/components/ui/button";

export function Card({
  children,
  className = "",
}: PropsWithChildren<{ className?: string }>) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: PropsWithChildren<
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "danger" | "ghost";
  }
>) {
  const shadcnVariant = {
    primary: "default",
    secondary: "outline",
    danger: "destructive",
    ghost: "ghost",
  } as const;
  return (
    <ShadcnButton
      variant={shadcnVariant[variant]}
      className={`button button-${variant} min-h-11 ${className}`}
      {...props}
    >
      {children}
    </ShadcnButton>
  );
}

type StatusKind =
  | "paid"
  | "upcoming"
  | "overdue"
  | "planned"
  | "pending"
  | "approved"
  | "rejected"
  | "active"
  | "cancelled"
  | "used"
  | "expired"
  | "revoked"
  | "partial";

const statusLabels: Record<StatusKind, string> = {
  paid: "Payé",
  upcoming: "À venir",
  overdue: "En retard",
  planned: "Prévu",
  pending: "En attente",
  approved: "Approuvée",
  rejected: "Refusée",
  active: "Actif",
  cancelled: "Annulé",
  used: "Utilisée",
  expired: "Expirée",
  revoked: "Révoquée",
  partial: "Partiellement payé",
};

export function StatusBadge({
  status,
  label,
}: {
  status: StatusKind;
  label?: string;
}) {
  return (
    <span className={`status-badge status-${status}`}>
      {label ?? statusLabels[status]}
    </span>
  );
}

const xafFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "XAF",
  maximumFractionDigits: 0,
});

export function AmountXAF({ value }: { value: string | number }) {
  return <>{xafFormatter.format(Number(value))}</>;
}

export function LoadingState({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="state-card" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="state-card state-error" role="alert">
      <strong>Une erreur est survenue</strong>
      <p>{message}</p>
      {action}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="state-card">
      <strong>{title}</strong>
      <p>{message}</p>
      {action}
    </div>
  );
}

export function DataTable({
  children,
  label,
}: PropsWithChildren<{ label: string }>) {
  return (
    <div className="table-scroll" role="region" aria-label={label} tabIndex={0}>
      <table>{children}</table>
    </div>
  );
}

export function PaginationControls({
  page,
  count,
  pageSize,
  onPageChange,
}: {
  page: number;
  count: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}) {
  const pageCount = Math.max(1, Math.ceil(count / pageSize));
  if (pageCount <= 1) return null;
  return (
    <nav className="pagination-controls" aria-label="Pagination">
      <span>Page {page} sur {pageCount} · {count} résultats</span>
      <div>
        <Button
          variant="secondary"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          Précédent
        </Button>
        <Button
          variant="secondary"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pageCount}
        >
          Suivant
        </Button>
      </div>
    </nav>
  );
}

export function Field({
  label,
  error,
  id,
  children,
}: PropsWithChildren<{ label: string; error?: string; id: string }>) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  );
}
