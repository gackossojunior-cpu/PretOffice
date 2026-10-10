import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleCheck, CircleX, Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { api, errorMessage } from "../api/auth";
import { formatDate } from "../api/dates";
import type {
  ApiSchemas,
  ApplicationStatus,
  Borrower,
  Installment,
  Loan,
  LoanApplication,
  LoanDecisionPayload,
  LoanStatus,
  Paginated,
  Repayment,
} from "../api/types";
import { AmountXAF, Button, Card, DataTable, EmptyState, ErrorState, Field, LoadingState, PaginationControls, StatusBadge } from "../components/ui";

function applicationStatus(status: ApplicationStatus) {
  return ({
    PENDING: "pending",
    APPROVED: "approved",
    REJECTED: "rejected",
  } as const)[status];
}

function applicationStatusFilter(value: string): ApplicationStatus | "" {
  return value === "PENDING" || value === "APPROVED" || value === "REJECTED" ? value : "";
}

function loanStatus(status: LoanStatus | undefined) {
  return ({
    ACTIVE: "active",
    PAID: "paid",
    OVERDUE: "overdue",
    CANCELLED: "cancelled",
  } as const)[status ?? "ACTIVE"];
}

function installmentStatus(status: Installment["status"]) {
  return ({
    PENDING: "upcoming",
    PARTIAL: "partial",
    PAID: "paid",
    OVERDUE: "overdue",
  } as const)[status];
}

function asRows<T>(data: T[] | Paginated<T>) {
  return Array.isArray(data) ? data : data.results;
}

const applicationSchema = z.object({
  borrower: z.coerce.number().int().positive("Sélectionnez un emprunteur."),
  amount_requested: z.string().regex(/^\d{1,10}(\.\d{1,2})?$/, "Saisissez un montant valide."),
  duration_months: z.coerce.number().int().min(1, "La durée doit être supérieure à zéro."),
  interest_rate: z.string().regex(/^\d{1,3}(\.\d{1,2})?$/, "Saisissez un taux valide."),
  purpose: z.string(),
});

type ApplicationFormValues = z.infer<typeof applicationSchema>;
type ApplicationFormInput = z.input<typeof applicationSchema>;

const decisionSchema = z.object({
  action: z.enum(["APPROVE", "REJECT"]),
  reason: z.string().min(1, "Saisissez un motif de décision."),
  amount_approved: z.string(),
  interest_rate: z.string(),
  duration_months: z.coerce.number().int().positive(),
  frequency: z.enum(["WEEKLY", "MONTHLY"]),
  interest_type: z.enum(["SIMPLE", "NONE"]),
  penalty_enabled: z.boolean(),
  penalty_type: z.enum(["RATE", "FIXED"]),
  penalty_rate: z.string(),
  penalty_amount: z.string(),
}).superRefine((values, context) => {
  if (values.action !== "APPROVE" || !values.penalty_enabled) return;

  const value = values.penalty_type === "RATE" ? values.penalty_rate : values.penalty_amount;
  if (!/^(?=.*[1-9])\d{1,10}(\.\d{1,2})?$/.test(value)) {
    context.addIssue({
      code: "custom",
      path: [values.penalty_type === "RATE" ? "penalty_rate" : "penalty_amount"],
      message: "Indiquez une pénalité supérieure à zéro.",
    });
  }
});

type DecisionValues = z.infer<typeof decisionSchema>;
type DecisionFormInput = z.input<typeof decisionSchema>;

export function LoanApplicationsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<LoanApplication | null>(null);
  const [formError, setFormError] = useState("");
  const [decisionAction, setDecisionAction] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [penaltyEnabled, setPenaltyEnabled] = useState(false);
  const [penaltyType, setPenaltyType] = useState<"RATE" | "FIXED">("RATE");
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("");
  const [borrowerFilter, setBorrowerFilter] = useState("");
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");
  const pageSize = 20;
  const borrowerQuery = useQuery({
    queryKey: ["borrowers"],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Borrower>>("/api/borrowers/", { params: { page_size: 100 } });
      return data.results;
    },
  });
  const applicationsQuery = useQuery({
    queryKey: ["loan-applications", page, statusFilter, borrowerFilter, createdAfter, createdBefore],
    queryFn: async () => {
      const { data } = await api.get<Paginated<LoanApplication>>("/api/loans/", {
        params: {
          page,
          page_size: pageSize,
          ordering: "-created_at",
          status: statusFilter || undefined,
          borrower: borrowerFilter || undefined,
          created_after: createdAfter || undefined,
          created_before: createdBefore || undefined,
        },
      });
      return data;
    },
  });
  const applicationForm = useForm<ApplicationFormInput, unknown, ApplicationFormValues>({
    resolver: zodResolver(applicationSchema),
    defaultValues: { borrower: 0, amount_requested: "", duration_months: 1, interest_rate: "0", purpose: "" },
  });
  const decisionForm = useForm<DecisionFormInput, unknown, DecisionValues>({
    resolver: zodResolver(decisionSchema),
    values: {
      action: "APPROVE",
      reason: "",
      amount_approved: selected?.amount_requested ?? "",
      interest_rate: selected?.interest_rate ?? "0",
      duration_months: selected?.duration_months ?? 1,
      frequency: "MONTHLY",
      interest_type: "SIMPLE",
      penalty_enabled: false,
      penalty_type: "RATE",
      penalty_rate: "0",
      penalty_amount: "0",
    },
  });
  const createApplication = useMutation({
    mutationFn: async (values: ApplicationFormValues) => {
      const payload: Pick<ApiSchemas["LoanApplication"], "borrower" | "amount_requested" | "duration_months" | "interest_rate" | "purpose"> = {
        ...values,
        purpose: values.purpose || null,
      };
      const { data } = await api.post<LoanApplication>("/api/loans/", payload);
      return data;
    },
    onSuccess: async () => {
      applicationForm.reset({ borrower: 0, amount_requested: "", duration_months: 1, interest_rate: "0", purpose: "" });
      await queryClient.invalidateQueries({ queryKey: ["loan-applications"] });
      setFormError("");
    },
    onError: (error) => setFormError(errorMessage(error)),
  });
  const decide = useMutation({
    mutationFn: async (values: DecisionValues) => {
      const payload: LoanDecisionPayload = values;
      const { data } = await api.post<ApiSchemas["LoanDecisionResponse"]>(
        `/api/loans/${selected?.id}/decision/`,
        payload,
      );
      return data;
    },
    onSuccess: async (data) => {
      setSelected(null);
      setDecisionAction("APPROVE");
      setPenaltyEnabled(false);
      setPenaltyType("RATE");
      decisionForm.reset();
      await queryClient.invalidateQueries({ queryKey: ["loan-applications"] });
      if (data.loan_id) navigate(`/prets/${data.loan_id}`);
    },
    onError: (error) => decisionForm.setError("root", { message: errorMessage(error) }),
  });

  return (
    <div className="page-stack">
      <header className="page-heading">
        <p className="eyebrow">Analyse et décision</p>
        <h1>Demandes de prêt</h1>
        <p>Créez une demande pour l’un de vos emprunteurs, puis suivez son traitement.</p>
      </header>
      <Card className="profile-card">
        <h2 className="section-title"><Plus size={19} aria-hidden="true" /> Nouvelle demande</h2>
        {borrowerQuery.isPending ? <LoadingState label="Chargement des emprunteurs…" /> : null}
        {borrowerQuery.isError ? <ErrorState message={errorMessage(borrowerQuery.error)} /> : null}
        {borrowerQuery.data?.length === 0 ? (
          <EmptyState title="Aucun emprunteur" message="Vous devez d’abord enregistrer un emprunteur avant de créer une demande." />
        ) : null}
        {borrowerQuery.data?.length ? (
          <form className="form-stack" onSubmit={applicationForm.handleSubmit((values) => createApplication.mutate(values))} noValidate>
            <div className="form-grid">
              <Field label="Emprunteur" id="application-borrower" error={applicationForm.formState.errors.borrower?.message}>
                <select id="application-borrower" {...applicationForm.register("borrower")}>
                  <option value={0}>Choisir un emprunteur</option>
                  {borrowerQuery.data.map((borrower) => (
                    <option value={borrower.id} key={borrower.id}>{borrower.first_name} {borrower.last_name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Montant demandé (XAF)" id="application-amount" error={applicationForm.formState.errors.amount_requested?.message}>
                <input id="application-amount" inputMode="decimal" placeholder="Ex. 150000" {...applicationForm.register("amount_requested")} />
              </Field>
            </div>
            <div className="form-grid">
              <Field label="Durée (mois)" id="application-duration" error={applicationForm.formState.errors.duration_months?.message}>
                <input id="application-duration" type="number" min="1" {...applicationForm.register("duration_months")} />
              </Field>
              <Field label="Taux annuel (%)" id="application-rate" error={applicationForm.formState.errors.interest_rate?.message}>
                <input id="application-rate" inputMode="decimal" {...applicationForm.register("interest_rate")} />
              </Field>
            </div>
            <Field label="Objet de la demande (facultatif)" id="application-purpose" error={applicationForm.formState.errors.purpose?.message}>
              <textarea id="application-purpose" rows={3} {...applicationForm.register("purpose")} />
            </Field>
            {formError ? <p className="form-error" role="alert">{formError}</p> : null}
            <Button type="submit" disabled={createApplication.isPending}>
              {createApplication.isPending ? "Création…" : "Créer la demande"}
            </Button>
          </form>
        ) : null}
      </Card>
      <section className="page-stack">
        <h2 className="section-title">Demandes enregistrées</h2>
        <div className="filter-toolbar">
          <Field label="Statut" id="application-status-filter">
            <select id="application-status-filter" value={statusFilter} onChange={(event) => { setStatusFilter(applicationStatusFilter(event.target.value)); setPage(1); }}>
              <option value="">Tous les statuts</option>
              <option value="PENDING">En attente</option>
              <option value="APPROVED">Approuvée</option>
              <option value="REJECTED">Rejetée</option>
            </select>
          </Field>
          <Field label="Emprunteur" id="application-borrower-filter">
            <select id="application-borrower-filter" value={borrowerFilter} onChange={(event) => { setBorrowerFilter(event.target.value); setPage(1); }}>
              <option value="">Tous les emprunteurs</option>
              {borrowerQuery.data?.map((borrower) => (
                <option value={borrower.id} key={borrower.id}>{borrower.first_name} {borrower.last_name}</option>
              ))}
            </select>
          </Field>
          <Field label="Créée depuis" id="application-created-after">
            <input id="application-created-after" type="date" value={createdAfter} onChange={(event) => { setCreatedAfter(event.target.value); setPage(1); }} />
          </Field>
          <Field label="Créée jusqu’au" id="application-created-before">
            <input id="application-created-before" type="date" value={createdBefore} onChange={(event) => { setCreatedBefore(event.target.value); setPage(1); }} />
          </Field>
        </div>
        {applicationsQuery.isPending ? <LoadingState label="Chargement des demandes…" /> : null}
        {applicationsQuery.isError ? <ErrorState message={errorMessage(applicationsQuery.error)} /> : null}
        {applicationsQuery.data?.results.length === 0 ? (
          <EmptyState title="Aucune demande" message="Les demandes de prêt créées apparaîtront ici." />
        ) : null}
        {applicationsQuery.data?.results.length ? (
          <Card className="table-card">
            <DataTable label="Demandes de prêt">
              <thead><tr><th>Emprunteur</th><th>Montant demandé</th><th>Durée</th><th>Statut</th><th>Créée le</th><th>Décision</th></tr></thead>
              <tbody>
                {applicationsQuery.data.results.map((application) => (
                  <tr key={application.id}>
                    <td>{application.borrower_name}</td>
                    <td><AmountXAF value={application.amount_requested} /></td>
                    <td>{application.duration_months} mois</td>
                    <td><StatusBadge status={applicationStatus(application.status)} /></td>
                    <td>{formatDate(application.created_at)}</td>
                    <td>
                      {application.status === "PENDING" ? (
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setSelected(application);
                            setDecisionAction("APPROVE");
                            setPenaltyEnabled(false);
                            setPenaltyType("RATE");
                          }}
                        >
                          Traiter
                        </Button>
                      ) : <span>{application.notes || "—"}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          </Card>
        ) : null}
        {applicationsQuery.data ? (
          <PaginationControls page={page} count={applicationsQuery.data.count} pageSize={pageSize} onPageChange={setPage} />
        ) : null}
      </section>
      {selected ? (
        <div className="modal-backdrop">
          <section className="decision-dialog" role="dialog" aria-modal="true" aria-labelledby="decision-title">
              <button type="button" className="modal-close" aria-label="Fermer" onClick={() => { setSelected(null); setDecisionAction("APPROVE"); setPenaltyEnabled(false); setPenaltyType("RATE"); }}>×</button>
            <p className="eyebrow">Demande #{selected.id}</p>
            <h2 id="decision-title">Décision de prêt</h2>
            <p className="decision-summary">
              {selected.borrower_name} · <AmountXAF value={selected.amount_requested} /> · {selected.duration_months} mois
            </p>
            <form className="form-stack" onSubmit={decisionForm.handleSubmit((values) => decide.mutate(values))} noValidate>
              <Field label="Décision" id="decision-action">
                <select
                  id="decision-action"
                  {...decisionForm.register("action")}
                  value={decisionAction}
                  onChange={(event) => {
                    const action = event.target.value === "REJECT" ? "REJECT" : "APPROVE";
                    setDecisionAction(action);
                    decisionForm.setValue("action", action);
                  }}
                >
                  <option value="APPROVE">Approuver</option>
                  <option value="REJECT">Refuser</option>
                </select>
              </Field>
              {decisionAction === "APPROVE" ? (
                <>
                  <div className="form-grid">
                    <Field label="Montant accordé (XAF)" id="approved-amount">
                      <input id="approved-amount" inputMode="decimal" {...decisionForm.register("amount_approved")} />
                    </Field>
                    <Field label="Taux d’intérêt annuel (%)" id="approved-rate">
                      <input id="approved-rate" inputMode="decimal" {...decisionForm.register("interest_rate")} />
                    </Field>
                  </div>
                  <div className="form-grid">
                    <Field label="Durée (mois)" id="approved-duration">
                      <input id="approved-duration" type="number" min="1" {...decisionForm.register("duration_months")} />
                    </Field>
                    <Field label="Périodicité" id="approved-frequency">
                      <select id="approved-frequency" {...decisionForm.register("frequency")}>
                        <option value="MONTHLY">Mensuelle</option>
                        <option value="WEEKLY">Hebdomadaire</option>
                      </select>
                    </Field>
                  </div>
                  <Field label="Type d’intérêt" id="interest-type">
                    <select id="interest-type" {...decisionForm.register("interest_type")}>
                      <option value="SIMPLE">Simple</option>
                      <option value="NONE">Sans intérêt</option>
                    </select>
                  </Field>
                  <label className="checkbox-field" htmlFor="penalty-enabled">
                    <input
                      id="penalty-enabled"
                      type="checkbox"
                      {...decisionForm.register("penalty_enabled")}
                      checked={penaltyEnabled}
                      onChange={(event) => {
                        const enabled = event.target.checked;
                        setPenaltyEnabled(enabled);
                        decisionForm.setValue("penalty_enabled", enabled);
                      }}
                    />
                    <span>Activer une pénalité de retard pour ce prêt</span>
                  </label>
                  {penaltyEnabled ? (
                    <>
                      <Field label="Type de pénalité" id="penalty-type">
                        <select
                          id="penalty-type"
                          {...decisionForm.register("penalty_type")}
                          value={penaltyType}
                          onChange={(event) => {
                            const type = event.target.value === "FIXED" ? "FIXED" : "RATE";
                            setPenaltyType(type);
                            decisionForm.setValue("penalty_type", type);
                          }}
                        >
                          <option value="RATE">Taux (%)</option>
                          <option value="FIXED">Montant fixe (XAF)</option>
                        </select>
                      </Field>
                      {penaltyType === "RATE" ? (
                        <Field label="Taux de pénalité (%)" id="penalty-rate" error={decisionForm.formState.errors.penalty_rate?.message}>
                          <input id="penalty-rate" inputMode="decimal" {...decisionForm.register("penalty_rate")} />
                        </Field>
                      ) : (
                        <Field label="Montant de la pénalité (XAF)" id="penalty-amount" error={decisionForm.formState.errors.penalty_amount?.message}>
                          <input id="penalty-amount" inputMode="decimal" {...decisionForm.register("penalty_amount")} />
                        </Field>
                      )}
                    </>
                  ) : null}
                </>
              ) : null}
              <Field label="Motif" id="decision-reason" error={decisionForm.formState.errors.reason?.message}>
                <textarea id="decision-reason" rows={3} {...decisionForm.register("reason")} />
              </Field>
              {decisionForm.formState.errors.root?.message ? (
                <p className="form-error" role="alert">{decisionForm.formState.errors.root.message}</p>
              ) : null}
              <div className="dialog-actions">
                <Button type="button" variant="secondary" onClick={() => setSelected(null)}>Annuler</Button>
                <Button type="submit" disabled={decide.isPending}>
                  {decisionAction === "APPROVE"
                    ? <><CircleCheck size={17} aria-hidden="true" /> Approuver</>
                    : <><CircleX size={17} aria-hidden="true" /> Refuser</>}
                </Button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  );
}

export function LoansPage() {
  return (
    <div className="page-stack">
      <header className="page-heading">
        <p className="eyebrow">Suivi des remboursements</p>
        <h1>Prêts</h1>
        <p>Consultez les prêts accordés et leurs échéanciers.</p>
      </header>
      <ErrorState message="L’API actuelle ne fournit pas de liste des prêts accordés. Vous pouvez ouvrir un prêt juste après son approbation depuis les demandes. Une liste durable nécessite un endpoint backend dédié." />
    </div>
  );
}

const repaymentSchema = z.object({
  amount: z.string().regex(/^\d{1,10}(\.\d{1,2})?$/, "Saisissez un montant valide."),
  payment_date: z.string().min(1, "Saisissez la date du paiement."),
  payment_method: z.enum(["CASH", "TRANSFER", "MOBILE_MONEY", "OTHER"]),
  note: z.string(),
});

type RepaymentFormValues = z.infer<typeof repaymentSchema>;

const cancelSchema = z.object({
  reason: z.string().min(1, "Indiquez le motif d’annulation."),
});

export function LoanDetailPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [today] = useState(() => new Date().toISOString().slice(0, 10));
  const [formError, setFormError] = useState("");
  const loanQuery = useQuery({
    queryKey: ["loan", id],
    queryFn: async () => {
      const { data } = await api.get<Loan>(`/api/loans/${encodeURIComponent(id)}/`);
      return data;
    },
  });
  const installmentsQuery = useQuery({
    queryKey: ["installments", id],
    queryFn: async () => {
      const { data } = await api.get<Installment[] | Paginated<Installment>>(
        `/api/loans/${encodeURIComponent(id)}/installments/`,
      );
      return asRows(data);
    },
  });
  const repaymentsQuery = useQuery({
    queryKey: ["repayments", id],
    queryFn: async () => {
      const { data } = await api.get<Repayment[] | Paginated<Repayment>>(
        `/api/loans/${encodeURIComponent(id)}/repayments/`,
      );
      return asRows(data);
    },
  });
  const repaymentForm = useForm<RepaymentFormValues>({
    resolver: zodResolver(repaymentSchema),
    defaultValues: {
      amount: "",
      payment_date: today,
      payment_method: "CASH",
      note: "",
    },
  });
  const cancelForm = useForm<{ reason: string }>({
    resolver: zodResolver(cancelSchema),
    defaultValues: { reason: "" },
  });
  const [showCancel, setShowCancel] = useState(false);
  const addRepayment = useMutation({
    mutationFn: async (values: RepaymentFormValues) => {
      const { data } = await api.post<Repayment>(`/api/loans/${encodeURIComponent(id)}/repayments/`, {
        ...values,
        note: values.note || "",
      });
      return data;
    },
    onSuccess: async () => {
      repaymentForm.reset({ amount: "", payment_date: today, payment_method: "CASH", note: "" });
      setFormError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["loan", id] }),
        queryClient.invalidateQueries({ queryKey: ["installments", id] }),
        queryClient.invalidateQueries({ queryKey: ["repayments", id] }),
      ]);
    },
    onError: (error) => setFormError(errorMessage(error)),
  });
  const cancelLoan = useMutation({
    mutationFn: async ({ reason }: { reason: string }) => {
      const { data } = await api.post<ApiSchemas["LoanCancellationResponse"]>(`/api/loans/${encodeURIComponent(id)}/cancel/`, { reason });
      return data;
    },
    onSuccess: async () => {
      setFormError("");
      setShowCancel(false);
      await queryClient.invalidateQueries({ queryKey: ["loan", id] });
    },
    onError: (error) => setFormError(errorMessage(error)),
  });

  if (loanQuery.isPending) return <LoadingState label="Chargement du prêt…" />;
  if (loanQuery.isError) return <ErrorState message={errorMessage(loanQuery.error)} />;
  const loan = loanQuery.data;

  return (
    <div className="page-stack">
      <Link className="back-link" to="/prets"><ArrowLeft size={17} aria-hidden="true" /> Retour aux prêts</Link>
      <header className="page-heading page-heading-row">
        <div>
          <p className="eyebrow">Prêt #{loan.id} · {loan.borrower_name}</p>
          <h1>Détail du prêt</h1>
        </div>
        <StatusBadge status={loanStatus(loan.status)} />
      </header>
      <section className="loan-metrics" aria-label="Résumé du prêt">
        <Card className="metric-card"><span>Montant accordé</span><strong><AmountXAF value={loan.principal_amount} /></strong></Card>
        <Card className="metric-card"><span>Total à rembourser</span><strong><AmountXAF value={loan.total_to_repay} /></strong></Card>
        <Card className="metric-card"><span>Total remboursé</span><strong><AmountXAF value={loan.total_paid} /></strong></Card>
        <Card className="metric-card"><span>Solde restant</span><strong><AmountXAF value={loan.balance_remaining} /></strong></Card>
      </section>
      <Card className="loan-summary">
        <div><span>Échéance suivante</span><strong>{formatDate(loan.next_due_date)}</strong></div>
        <div><span>Retard</span><strong>{loan.days_overdue} jour{loan.days_overdue > 1 ? "s" : ""}</strong></div>
        <div><span>Durée</span><strong>{loan.duration_months} mois · {loan.frequency === "WEEKLY" ? "Hebdomadaire" : "Mensuelle"}</strong></div>
        <div><span>Taux annuel</span><strong>{loan.interest_type === "NONE" ? "Sans intérêt" : `${loan.interest_rate ?? "0"} %`}</strong></div>
      </Card>
      {formError ? <ErrorState message={formError} /> : null}
      <section className="detail-grid">
        <Card className="profile-card">
          <h2 className="section-title">Échéancier</h2>
          {installmentsQuery.isPending ? <LoadingState label="Chargement des échéances…" /> : null}
          {installmentsQuery.isError ? <ErrorState message={errorMessage(installmentsQuery.error)} /> : null}
          {installmentsQuery.data?.length ? (
            <DataTable label="Échéancier du prêt">
              <thead><tr><th>#</th><th>Échéance</th><th>Dû</th><th>Payé</th><th>Statut</th></tr></thead>
              <tbody>{installmentsQuery.data.map((installment) => (
                <tr key={installment.id}>
                  <td>{installment.number}</td>
                  <td>{formatDate(installment.due_date)}</td>
                  <td><AmountXAF value={installment.total_due} /></td>
                  <td><AmountXAF value={installment.amount_paid} /></td>
                  <td><StatusBadge status={installmentStatus(installment.status)} /></td>
                </tr>
              ))}</tbody>
            </DataTable>
          ) : null}
          {installmentsQuery.data?.length === 0 ? <EmptyState title="Aucune échéance" message="Aucune échéance n’est disponible pour ce prêt." /> : null}
        </Card>
        <div className="page-stack">
          <Card className="profile-card">
            <h2 className="section-title">Enregistrer un remboursement</h2>
            {loan.status === "ACTIVE" || loan.status === "OVERDUE" ? (
              <form className="form-stack" onSubmit={repaymentForm.handleSubmit((values) => addRepayment.mutate(values))} noValidate>
                <Field label="Montant (XAF)" id="repayment-amount" error={repaymentForm.formState.errors.amount?.message}>
                  <input id="repayment-amount" inputMode="decimal" {...repaymentForm.register("amount")} />
                </Field>
                <Field label="Date du paiement" id="repayment-date" error={repaymentForm.formState.errors.payment_date?.message}>
                  <input id="repayment-date" type="date" {...repaymentForm.register("payment_date")} />
                </Field>
                <Field label="Mode de paiement" id="repayment-method">
                  <select id="repayment-method" {...repaymentForm.register("payment_method")}>
                    <option value="CASH">Espèces</option>
                    <option value="TRANSFER">Virement</option>
                    <option value="MOBILE_MONEY">Mobile money</option>
                    <option value="OTHER">Autre</option>
                  </select>
                </Field>
                <Field label="Note (facultatif)" id="repayment-note">
                  <textarea id="repayment-note" rows={2} {...repaymentForm.register("note")} />
                </Field>
                <Button type="submit" disabled={addRepayment.isPending}>
                  {addRepayment.isPending ? "Enregistrement…" : "Enregistrer le remboursement"}
                </Button>
              </form>
            ) : <p className="auth-intro">Ce prêt ne peut plus recevoir de remboursements.</p>}
          </Card>
          <Card className="profile-card">
            <h2 className="section-title">Historique des remboursements</h2>
            {repaymentsQuery.isPending ? <LoadingState label="Chargement de l’historique…" /> : null}
            {repaymentsQuery.isError ? <ErrorState message={errorMessage(repaymentsQuery.error)} /> : null}
            {repaymentsQuery.data?.length ? (
              <DataTable label="Historique des remboursements">
                <thead><tr><th>Date</th><th>Montant</th><th>Mode</th><th>Note</th></tr></thead>
                <tbody>{repaymentsQuery.data.map((repayment) => (
                  <tr key={repayment.id}>
                    <td>{formatDate(repayment.payment_date)}</td>
                    <td><AmountXAF value={repayment.amount} /></td>
                    <td>{paymentMethodLabel(repayment.payment_method)}</td>
                    <td>{repayment.note || "—"}</td>
                  </tr>
                ))}</tbody>
              </DataTable>
            ) : null}
            {repaymentsQuery.data?.length === 0 ? <EmptyState title="Aucun remboursement" message="Les remboursements apparaîtront ici après leur enregistrement." /> : null}
          </Card>
        </div>
      </section>
      {loan.status === "ACTIVE" || loan.status === "OVERDUE" ? (
        <Card className="cancel-card">
          <div>
            <strong>Annuler ce prêt</strong>
            <p>L’annulation est définitive et n’est possible que si aucun remboursement n’a été enregistré.</p>
          </div>
          <Button variant="danger" onClick={() => setShowCancel((visible) => !visible)}>
            {showCancel ? "Fermer" : "Annuler le prêt"}
          </Button>
          {showCancel ? (
            <form className="form-stack cancel-form" onSubmit={cancelForm.handleSubmit((values) => cancelLoan.mutate(values))} noValidate>
              <Field label="Motif d’annulation" id="cancel-reason" error={cancelForm.formState.errors.reason?.message}>
                <textarea id="cancel-reason" rows={3} {...cancelForm.register("reason")} />
              </Field>
              <Button type="submit" variant="danger" disabled={cancelLoan.isPending}>
                {cancelLoan.isPending ? "Annulation…" : "Confirmer l’annulation"}
              </Button>
            </form>
          ) : null}
        </Card>
      ) : null}
      <p className="pagination-note">L’annulation inversée d’un remboursement n’est pas disponible dans l’API. Aucun bouton d’annulation de paiement n’est affiché.</p>
    </div>
  );
}

function paymentMethodLabel(method: Repayment["payment_method"]) {
  return ({
    CASH: "Espèces",
    TRANSFER: "Virement",
    MOBILE_MONEY: "Mobile money",
    OTHER: "Autre",
  } as const)[method ?? "CASH"];
}
