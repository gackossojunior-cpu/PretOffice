import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { api, errorMessage } from "../api/auth";
import { formatDate } from "../api/dates";
import type { Borrower, Paginated } from "../api/types";
import { Button, Card, DataTable, EmptyState, ErrorState, Field, LoadingState, PaginationControls } from "../components/ui";

function borrowerName(borrower: Borrower) {
  return `${borrower.first_name} ${borrower.last_name}`.trim();
}

export function BorrowersPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");
  const pageSize = 20;
  const borrowersQuery = useQuery({
    queryKey: ["borrowers", page, createdAfter, createdBefore],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Borrower>>("/api/borrowers/", {
        params: {
          page,
          page_size: pageSize,
          ordering: "-created_at",
          created_after: createdAfter || undefined,
          created_before: createdBefore || undefined,
        },
      });
      return data;
    },
  });
  const borrowers = useMemo(() => {
    const rows = borrowersQuery.data?.results ?? [];
    const normalized = search.trim().toLocaleLowerCase("fr");
    if (!normalized) return rows;
    return rows.filter((borrower) =>
      [borrower.first_name, borrower.last_name, borrower.email ?? "", borrower.phone]
        .join(" ")
        .toLocaleLowerCase("fr")
        .includes(normalized),
    );
  }, [borrowersQuery.data, search]);

  return (
    <div className="page-stack">
      <header className="page-heading page-heading-row">
        <div>
          <p className="eyebrow">Votre portefeuille</p>
          <h1>Emprunteurs</h1>
          <p>Consultez les personnes rattachées à votre espace.</p>
        </div>
        <label className="search-field">
          <Search size={18} aria-hidden="true" />
          <span className="sr-only">Rechercher sur la page affichée</span>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher sur cette page…" />
        </label>
      </header>
      <div className="filter-toolbar">
        <Field label="Ajouté depuis" id="borrower-created-after">
          <input
            id="borrower-created-after"
            type="date"
            value={createdAfter}
            onChange={(event) => { setCreatedAfter(event.target.value); setPage(1); }}
          />
        </Field>
        <Field label="Ajouté jusqu’au" id="borrower-created-before">
          <input
            id="borrower-created-before"
            type="date"
            value={createdBefore}
            onChange={(event) => { setCreatedBefore(event.target.value); setPage(1); }}
          />
        </Field>
      </div>
      {borrowersQuery.isPending ? <LoadingState label="Chargement des emprunteurs…" /> : null}
      {borrowersQuery.isError ? <ErrorState message={errorMessage(borrowersQuery.error)} /> : null}
      {borrowersQuery.data && borrowers.length === 0 ? (
        <EmptyState
          title={search ? "Aucun résultat" : "Aucun emprunteur pour le moment"}
          message={search ? "Essayez avec un autre nom ou numéro." : "Les emprunteurs qui répondent à vos invitations apparaîtront ici."}
        />
      ) : null}
      {borrowers.length ? (
        <Card className="table-card">
          <DataTable label="Liste des emprunteurs">
            <thead>
              <tr><th>Nom</th><th>Téléphone</th><th>Email</th><th>Profession</th><th>Ajouté le</th><th /></tr>
            </thead>
            <tbody>
              {borrowers.map((borrower) => (
                <tr key={borrower.id}>
                  <td><Link className="table-primary-link" to={`/emprunteurs/${borrower.id}`}>{borrowerName(borrower)}</Link></td>
                  <td>{borrower.phone}</td>
                  <td>{borrower.email || "—"}</td>
                  <td>{borrower.occupation || "—"}</td>
                  <td>{formatDate(borrower.created_at)}</td>
                  <td><Link className="table-action" to={`/emprunteurs/${borrower.id}`}>Voir la fiche</Link></td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </Card>
      ) : null}
      {borrowersQuery.data ? (
        <PaginationControls page={page} count={borrowersQuery.data.count} pageSize={pageSize} onPageChange={setPage} />
      ) : null}
    </div>
  );
}

const borrowerSchema = z.object({
  first_name: z.string().min(1, "Le prénom est obligatoire."),
  last_name: z.string().min(1, "Le nom est obligatoire."),
  phone: z.string().min(1, "Le téléphone est obligatoire."),
  email: z.union([z.email("Adresse email invalide."), z.literal("")]),
  address: z.string(),
  national_id: z.string(),
  occupation: z.string(),
});

type BorrowerForm = z.infer<typeof borrowerSchema>;

export function BorrowerDetailPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const borrowerQuery = useQuery({
    queryKey: ["borrower", id],
    queryFn: async () => {
      const { data } = await api.get<Borrower>(`/api/borrowers/${encodeURIComponent(id)}/`);
      return data;
    },
  });
  const form = useForm<BorrowerForm>({
    resolver: zodResolver(borrowerSchema),
    values: {
      first_name: borrowerQuery.data?.first_name ?? "",
      last_name: borrowerQuery.data?.last_name ?? "",
      phone: borrowerQuery.data?.phone ?? "",
      email: borrowerQuery.data?.email ?? "",
      address: borrowerQuery.data?.address ?? "",
      national_id: borrowerQuery.data?.national_id ?? "",
      occupation: borrowerQuery.data?.occupation ?? "",
    },
  });
  const updateBorrower = useMutation({
    mutationFn: async (values: BorrowerForm) => {
      const { data } = await api.patch<Borrower>(`/api/borrowers/${encodeURIComponent(id)}/`, {
        ...values,
        email: values.email || null,
        address: values.address || null,
        national_id: values.national_id || null,
        occupation: values.occupation || null,
      });
      return data;
    },
    onSuccess: async (borrower) => {
      queryClient.setQueryData(["borrower", id], borrower);
      await queryClient.invalidateQueries({ queryKey: ["borrowers"] });
    },
    onError: (error) => form.setError("root", { message: errorMessage(error) }),
  });

  if (borrowerQuery.isPending) return <LoadingState label="Chargement de la fiche…" />;
  if (borrowerQuery.isError) return <ErrorState message={errorMessage(borrowerQuery.error)} />;
  const borrower = borrowerQuery.data;

  return (
    <div className="page-stack">
      <Link className="back-link" to="/emprunteurs"><ArrowLeft size={17} aria-hidden="true" /> Retour aux emprunteurs</Link>
      <header className="page-heading">
        <p className="eyebrow">Fiche emprunteur</p>
        <h1>{borrowerName(borrower)}</h1>
        <p>Informations personnelles reçues par invitation.</p>
      </header>
      <Card className="profile-card">
        <form className="form-stack" onSubmit={form.handleSubmit((values) => updateBorrower.mutate(values))} noValidate>
          <div className="form-grid">
            <Field label="Prénom" id="borrower-first-name" error={form.formState.errors.first_name?.message}>
              <input id="borrower-first-name" {...form.register("first_name")} />
            </Field>
            <Field label="Nom" id="borrower-last-name" error={form.formState.errors.last_name?.message}>
              <input id="borrower-last-name" {...form.register("last_name")} />
            </Field>
          </div>
          <div className="form-grid">
            <Field label="Téléphone" id="borrower-phone" error={form.formState.errors.phone?.message}>
              <input id="borrower-phone" type="tel" {...form.register("phone")} />
            </Field>
            <Field label="Adresse email" id="borrower-email" error={form.formState.errors.email?.message}>
              <input id="borrower-email" type="email" {...form.register("email")} />
            </Field>
          </div>
          <Field label="Adresse" id="borrower-address" error={form.formState.errors.address?.message}>
            <input id="borrower-address" {...form.register("address")} />
          </Field>
          <div className="form-grid">
            <Field label="Pièce d’identité" id="borrower-national-id" error={form.formState.errors.national_id?.message}>
              <input id="borrower-national-id" {...form.register("national_id")} />
            </Field>
            <Field label="Profession" id="borrower-occupation" error={form.formState.errors.occupation?.message}>
              <input id="borrower-occupation" {...form.register("occupation")} />
            </Field>
          </div>
          {form.formState.errors.root?.message ? <p className="form-error" role="alert">{form.formState.errors.root.message}</p> : null}
          {updateBorrower.isSuccess ? <p className="form-success" role="status">Les informations ont été mises à jour.</p> : null}
          <Button type="submit" disabled={updateBorrower.isPending}>
            {updateBorrower.isPending ? "Enregistrement…" : "Enregistrer"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
