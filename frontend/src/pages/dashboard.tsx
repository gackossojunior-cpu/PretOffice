import { useQueries } from "@tanstack/react-query";
import { ArrowRight, HandCoins, UsersRound, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";

import { api, errorMessage } from "../api/auth";
import { formatDate } from "../api/dates";
import type { Borrower, Invitation, LoanApplication, Paginated } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { AmountXAF, Card, DataTable, EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/ui";

export function DashboardPage() {
  const { profile } = useAuth();
  const [borrowersQuery, invitationsQuery, applicationsQuery] = useQueries({
    queries: [
      {
        queryKey: ["dashboard", "borrowers"],
        queryFn: async () => {
          const { data } = await api.get<Paginated<Borrower>>("/api/borrowers/", { params: { page_size: 1 } });
          return data;
        },
      },
      {
        queryKey: ["dashboard", "invitations"],
        queryFn: async () => {
          const { data } = await api.get<Paginated<Invitation>>("/api/invitations/", {
            params: { page_size: 5, status: "PENDING", ordering: "-created_at" },
          });
          return data;
        },
      },
      {
        queryKey: ["dashboard", "applications"],
        queryFn: async () => {
          const { data } = await api.get<Paginated<LoanApplication>>("/api/loans/", {
            params: { page_size: 5, status: "PENDING", ordering: "-created_at" },
          });
          return data;
        },
      },
    ],
  });
  const isPending = borrowersQuery.isPending || invitationsQuery.isPending || applicationsQuery.isPending;
  const firstError = [borrowersQuery.error, invitationsQuery.error, applicationsQuery.error].find(Boolean);

  return (
    <div className="page-stack">
      <header className="page-heading">
        <p className="eyebrow">Vue d’ensemble</p>
        <h1>Bonjour{profile?.first_name ? ` ${profile.first_name}` : ""}</h1>
        <p>Retrouvez rapidement les éléments à suivre dans votre espace prêteur.</p>
      </header>
      {isPending ? <LoadingState label="Chargement du tableau de bord…" /> : null}
      {firstError ? <ErrorState message={errorMessage(firstError)} /> : null}
      {borrowersQuery.data && invitationsQuery.data && applicationsQuery.data ? (
        <>
          <section className="dashboard-cards" aria-label="Indicateurs d’activité">
            <Link className="dashboard-card-link" to="/emprunteurs">
              <Card className="dashboard-card">
                <span className="dashboard-icon"><UsersRound size={19} aria-hidden="true" /></span>
                <span>Emprunteurs</span>
                <strong>{borrowersQuery.data.count}</strong>
                <span className="dashboard-card-link-label">Voir les emprunteurs <ArrowRight size={15} aria-hidden="true" /></span>
              </Card>
            </Link>
            <Link className="dashboard-card-link" to="/invitations">
              <Card className="dashboard-card">
                <span className="dashboard-icon"><WalletCards size={19} aria-hidden="true" /></span>
                <span>Invitations en attente</span>
                <strong>{invitationsQuery.data.count}</strong>
                <span className="dashboard-card-link-label">Gérer les invitations <ArrowRight size={15} aria-hidden="true" /></span>
              </Card>
            </Link>
            <Link className="dashboard-card-link" to="/demandes">
              <Card className="dashboard-card">
                <span className="dashboard-icon"><HandCoins size={19} aria-hidden="true" /></span>
                <span>Demandes à traiter</span>
                <strong>{applicationsQuery.data.count}</strong>
                <span className="dashboard-card-link-label">Traiter les demandes <ArrowRight size={15} aria-hidden="true" /></span>
              </Card>
            </Link>
          </section>
          <section className="dashboard-lists">
            <Card className="dashboard-panel">
              <div className="panel-heading">
                <div><h2>Demandes à traiter</h2><p>Les demandes récentes en attente de décision</p></div>
                <Link to="/demandes">Tout voir</Link>
              </div>
              {applicationsQuery.data.results.length ? (
                <DataTable label="Demandes récentes à traiter">
                  <thead><tr><th>Emprunteur</th><th>Montant demandé</th><th>Créée le</th><th>Statut</th></tr></thead>
                  <tbody>{applicationsQuery.data.results.map((application) => (
                    <tr key={application.id}>
                      <td>{application.borrower_name}</td>
                      <td><AmountXAF value={application.amount_requested} /></td>
                      <td>{formatDate(application.created_at)}</td>
                      <td><StatusBadge status="pending" /></td>
                    </tr>
                  ))}</tbody>
                </DataTable>
              ) : <EmptyState title="Aucune demande en attente" message="Les nouvelles demandes apparaîtront ici." />}
            </Card>
            <Card className="dashboard-panel">
              <div className="panel-heading">
                <div><h2>Invitations en attente</h2><p>Liens encore disponibles</p></div>
                <Link to="/invitations">Tout voir</Link>
              </div>
              {invitationsQuery.data.results.length ? (
                <DataTable label="Invitations récentes en attente">
                  <thead><tr><th>Créée le</th><th>Expire le</th><th>Statut</th></tr></thead>
                  <tbody>{invitationsQuery.data.results.map((invitation) => (
                    <tr key={invitation.id}>
                      <td>{formatDate(invitation.created_at)}</td>
                      <td>{formatDate(invitation.expires_at)}</td>
                      <td><StatusBadge status="pending" /></td>
                    </tr>
                  ))}</tbody>
                </DataTable>
              ) : <EmptyState title="Aucune invitation active" message="Créez une invitation pour accueillir un nouvel emprunteur." />}
            </Card>
          </section>
          <p className="dashboard-gap-note">
            Les indicateurs de montants, de remboursements, de soldes, de retards et les prochaines échéances ne sont pas fournis par l’API. Ils ne sont pas calculés dans le navigateur.
          </p>
        </>
      ) : null}
    </div>
  );
}
