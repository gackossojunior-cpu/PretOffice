import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Plus, X } from "lucide-react";
import { useState } from "react";

import { api, errorMessage } from "../api/auth";
import { formatDate } from "../api/dates";
import type { Invitation, InvitationStatus, Paginated } from "../api/types";
import { Button, Card, DataTable, EmptyState, ErrorState, Field, LoadingState, PaginationControls, StatusBadge } from "../components/ui";

function statusKind(status: InvitationStatus) {
  return ({
    PENDING: "pending",
    USED: "used",
    EXPIRED: "expired",
    REVOKED: "revoked",
  } as const)[status];
}

function invitationStatusFilter(value: string): InvitationStatus | "" {
  return value === "PENDING" || value === "USED" || value === "EXPIRED" || value === "REVOKED"
    ? value
    : "";
}

function shareUrl(invitation: Invitation) {
  return `${window.location.origin}/invitation/${encodeURIComponent(invitation.token)}`;
}

export function InvitationsPage() {
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<InvitationStatus | "">("");
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");
  const pageSize = 20;
  const invitationsQuery = useQuery({
    queryKey: ["invitations", page, statusFilter, createdAfter, createdBefore],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Invitation>>("/api/invitations/", {
        params: {
          page,
          page_size: pageSize,
          ordering: "-created_at",
          status: statusFilter || undefined,
          created_after: createdAfter || undefined,
          created_before: createdBefore || undefined,
        },
      });
      return data;
    },
  });
  const createInvitation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<Invitation>("/api/invitations/", {});
      return data;
    },
    onSuccess: async () => {
      setActionError("");
      await queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
    onError: (error) => setActionError(errorMessage(error)),
  });
  const revokeInvitation = useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<{ detail: string }>(`/api/invitations/${id}/revoke/`);
      return data;
    },
    onSuccess: async () => {
      setActionError("");
      await queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
    onError: (error) => setActionError(errorMessage(error)),
  });

  async function copyInvitation(invitation: Invitation) {
    try {
      await navigator.clipboard.writeText(shareUrl(invitation));
      setCopiedId(invitation.id);
      setActionError("");
      window.setTimeout(() => setCopiedId((current) => current === invitation.id ? null : current), 1800);
    } catch {
      setActionError("Impossible de copier le lien. Sélectionnez-le et copiez-le manuellement.");
    }
  }

  return (
    <div className="page-stack">
      <header className="page-heading page-heading-row">
        <div>
          <p className="eyebrow">Intégration des emprunteurs</p>
          <h1>Invitations</h1>
          <p>Créez un lien sécurisé à transmettre à un nouvel emprunteur.</p>
        </div>
        <Button onClick={() => createInvitation.mutate()} disabled={createInvitation.isPending}>
          <Plus size={18} aria-hidden="true" />
          {createInvitation.isPending ? "Création…" : "Nouvelle invitation"}
        </Button>
      </header>
      <div className="filter-toolbar">
        <Field label="Statut" id="invitation-status">
          <select
            id="invitation-status"
            value={statusFilter}
            onChange={(event) => { setStatusFilter(invitationStatusFilter(event.target.value)); setPage(1); }}
          >
            <option value="">Tous les statuts</option>
            <option value="PENDING">En attente</option>
            <option value="USED">Utilisée</option>
            <option value="EXPIRED">Expirée</option>
            <option value="REVOKED">Révoquée</option>
          </select>
        </Field>
        <Field label="Créée depuis" id="invitation-created-after">
          <input id="invitation-created-after" type="date" value={createdAfter} onChange={(event) => { setCreatedAfter(event.target.value); setPage(1); }} />
        </Field>
        <Field label="Créée jusqu’au" id="invitation-created-before">
          <input id="invitation-created-before" type="date" value={createdBefore} onChange={(event) => { setCreatedBefore(event.target.value); setPage(1); }} />
        </Field>
      </div>
      {actionError ? <ErrorState message={actionError} /> : null}
      {invitationsQuery.isPending ? <LoadingState label="Chargement des invitations…" /> : null}
      {invitationsQuery.isError ? <ErrorState message={errorMessage(invitationsQuery.error)} /> : null}
      {invitationsQuery.data?.results.length === 0 ? (
        <EmptyState
          title="Aucune invitation"
          message="Créez un lien pour inviter votre premier emprunteur."
          action={<Button onClick={() => createInvitation.mutate()}><Plus size={17} aria-hidden="true" /> Créer une invitation</Button>}
        />
      ) : null}
      {invitationsQuery.data?.results.length ? (
        <Card className="table-card">
          <DataTable label="Liste des invitations">
            <thead>
              <tr><th>Créée le</th><th>Expire le</th><th>Statut</th><th>Lien de partage</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {invitationsQuery.data.results.map((invitation) => (
                <tr key={invitation.id}>
                  <td>{formatDate(invitation.created_at)}</td>
                  <td>{formatDate(invitation.expires_at)}</td>
                  <td><StatusBadge status={statusKind(invitation.status)} /></td>
                  <td>
                    <code className="invitation-url">{shareUrl(invitation)}</code>
                  </td>
                  <td className="table-actions">
                    <Button variant="secondary" onClick={() => void copyInvitation(invitation)}>
                      {copiedId === invitation.id ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
                      {copiedId === invitation.id ? "Copié" : "Copier"}
                    </Button>
                    {invitation.status === "PENDING" ? (
                      <Button
                        variant="danger"
                        onClick={() => revokeInvitation.mutate(invitation.id)}
                        disabled={revokeInvitation.isPending}
                      >
                        <X size={16} aria-hidden="true" /> Révoquer
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </Card>
      ) : null}
      {invitationsQuery.data ? (
        <PaginationControls page={page} count={invitationsQuery.data.count} pageSize={pageSize} onPageChange={setPage} />
      ) : null}
    </div>
  );
}
