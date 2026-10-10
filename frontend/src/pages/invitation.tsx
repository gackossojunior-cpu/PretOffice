import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { z } from "zod";

import { api, errorMessage } from "../api/auth";
import type { ApiSchemas, PublicInvitation } from "../api/types";
import { Button, Card, ErrorState, Field, LoadingState } from "../components/ui";

const invitationFormSchema = z.object({
  first_name: z.string().min(1, "Saisissez le prénom."),
  last_name: z.string().min(1, "Saisissez le nom."),
  phone: z.string().min(1, "Saisissez le téléphone."),
  email: z.union([z.email("Saisissez une adresse email valide."), z.literal("")]),
  address: z.string(),
  national_id: z.string(),
  occupation: z.string(),
});

type InvitationFormValues = z.infer<typeof invitationFormSchema>;

export function PublicInvitationPage() {
  const { token = "" } = useParams();
  const invitationQuery = useQuery({
    queryKey: ["public-invitation", token],
    queryFn: async () => {
      const { data } = await api.get<PublicInvitation>(`/api/invitations/public/${encodeURIComponent(token)}/`);
      return data;
    },
    enabled: Boolean(token),
    retry: false,
  });
  const form = useForm<InvitationFormValues>({
    resolver: zodResolver(invitationFormSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      phone: "",
      email: "",
      address: "",
      national_id: "",
      occupation: "",
    },
  });
  const submit = useMutation({
    mutationFn: async (values: InvitationFormValues) => {
      const payload: ApiSchemas["PublicBorrowerApplication"] = {
        ...values,
        email: values.email || null,
        address: values.address || null,
        national_id: values.national_id || null,
        occupation: values.occupation || null,
      };
      const { data } = await api.post<{ detail: string; borrower_id: number }>(
        `/api/invitations/public/${encodeURIComponent(token)}/apply/`,
        payload,
      );
      return data;
    },
    onError: (error) => form.setError("root", { message: errorMessage(error) }),
  });

  if (invitationQuery.isPending) {
    return <main className="public-invitation"><LoadingState label="Vérification du lien…" /></main>;
  }

  if (invitationQuery.isError) {
    const status = axios.isAxiosError(invitationQuery.error)
      ? invitationQuery.error.response?.status
      : undefined;
    const isUnavailable = status === undefined;
    const message =
      status === 429
        ? "Trop de tentatives. Veuillez patienter avant de réessayer."
        : isUnavailable
          ? "Le service est momentanément indisponible. Réessayez dans quelques instants."
          : "Ce lien d’invitation n’est pas valide ou n’est plus disponible.";
    return (
      <main className="public-invitation">
        <Card className="invitation-card">
          <PublicBrand />
          <ErrorState message={message} />
        </Card>
      </main>
    );
  }

  if (submit.isSuccess) {
    return (
      <main className="public-invitation">
        <Card className="invitation-card invitation-confirmation">
          <PublicBrand />
          <span className="confirmation-mark" aria-hidden="true">✓</span>
          <h1>Demande envoyée</h1>
          <p>Vos informations ont été transmises à {invitationQuery.data.lender_name}.</p>
        </Card>
      </main>
    );
  }

  return (
    <main className="public-invitation">
      <Card className="invitation-card">
        <PublicBrand />
        <p className="eyebrow">Inscription emprunteur</p>
        <h1>Bienvenue</h1>
        <p className="auth-intro">
          {invitationQuery.data.lender_name} vous invite à compléter vos informations.
        </p>
        <form
          className="form-stack"
          onSubmit={form.handleSubmit((values) => submit.mutate(values))}
          noValidate
        >
          <Field label="Prénom" id="public-first-name" error={form.formState.errors.first_name?.message}>
            <input id="public-first-name" autoComplete="given-name" {...form.register("first_name")} />
          </Field>
          <Field label="Nom" id="public-last-name" error={form.formState.errors.last_name?.message}>
            <input id="public-last-name" autoComplete="family-name" {...form.register("last_name")} />
          </Field>
          <Field label="Téléphone" id="public-phone" error={form.formState.errors.phone?.message}>
            <input id="public-phone" type="tel" autoComplete="tel" {...form.register("phone")} />
          </Field>
          <Field label="Adresse email (facultatif)" id="public-email" error={form.formState.errors.email?.message}>
            <input id="public-email" type="email" autoComplete="email" {...form.register("email")} />
          </Field>
          <Field label="Adresse" id="public-address" error={form.formState.errors.address?.message}>
            <input id="public-address" autoComplete="street-address" {...form.register("address")} />
          </Field>
          <Field label="Numéro de pièce d’identité (facultatif)" id="public-national-id" error={form.formState.errors.national_id?.message}>
            <input id="public-national-id" {...form.register("national_id")} />
          </Field>
          <Field label="Profession (facultatif)" id="public-occupation" error={form.formState.errors.occupation?.message}>
            <input id="public-occupation" autoComplete="organization-title" {...form.register("occupation")} />
          </Field>
          {form.formState.errors.root?.message ? (
            <p className="form-error" role="alert">{form.formState.errors.root.message}</p>
          ) : null}
          <Button type="submit" disabled={submit.isPending}>
            {submit.isPending ? "Envoi en cours…" : "Envoyer mes informations"}
          </Button>
          <p className="invitation-privacy">Vos informations sont partagées uniquement avec ce prêteur.</p>
        </form>
      </Card>
    </main>
  );
}

function PublicBrand() {
  return <div className="auth-brand">PrêtOffice</div>;
}
