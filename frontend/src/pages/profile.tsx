import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { api, errorMessage } from "../api/auth";
import type { LenderProfile } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { Button, Card, ErrorState, Field, LoadingState } from "../components/ui";

const profileSchema = z.object({
  business_name: z.string(),
  phone: z.string(),
  address: z.string(),
  city: z.string(),
  country: z.string(),
});

type ProfileValues = z.infer<typeof profileSchema>;

export function ProfilePage() {
  const { profile, refreshProfile } = useAuth();
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      business_name: "",
      phone: "",
      address: "",
      city: "",
      country: "",
    },
  });

  useEffect(() => {
    if (!profile) return;
    form.reset({
      business_name: profile.business_name ?? "",
      phone: profile.phone ?? "",
      address: profile.address ?? "",
      city: profile.city ?? "",
      country: profile.country ?? "",
    });
  }, [form, profile]);

  const updateProfile = useMutation({
    mutationFn: async (values: ProfileValues) => {
      const { data } = await api.patch<LenderProfile>("/api/lenders/me/", values);
      return data;
    },
    onSuccess: async () => {
      await refreshProfile();
    },
    onError: (error) => form.setError("root", { message: errorMessage(error) }),
  });

  if (!profile) return <LoadingState label="Chargement du profil…" />;

  return (
    <div className="page-stack">
      <header className="page-heading">
        <p className="eyebrow">Compte prêteur</p>
        <h1>Mon profil</h1>
        <p>Consultez vos informations de compte et mettez à jour votre établissement.</p>
      </header>
      <Card className="profile-card">
        <div className="profile-identity">
          <div>
            <h2>{[profile.first_name, profile.last_name].filter(Boolean).join(" ") || profile.username}</h2>
            <p>{profile.email}</p>
          </div>
          <span className="profile-status">{profile.is_activate ? "Compte actif" : "Compte inactif"}</span>
        </div>
        <form
          className="form-stack"
          onSubmit={form.handleSubmit((values) => updateProfile.mutate(values))}
          noValidate
        >
          <Field label="Nom de l’établissement" id="business-name" error={form.formState.errors.business_name?.message}>
            <input id="business-name" {...form.register("business_name")} />
          </Field>
          <div className="form-grid">
            <Field label="Téléphone" id="profile-phone" error={form.formState.errors.phone?.message}>
              <input id="profile-phone" type="tel" {...form.register("phone")} />
            </Field>
            <Field label="Ville" id="profile-city" error={form.formState.errors.city?.message}>
              <input id="profile-city" {...form.register("city")} />
            </Field>
          </div>
          <Field label="Adresse" id="profile-address" error={form.formState.errors.address?.message}>
            <input id="profile-address" {...form.register("address")} />
          </Field>
          <Field label="Pays" id="profile-country" error={form.formState.errors.country?.message}>
            <input id="profile-country" {...form.register("country")} />
          </Field>
          {form.formState.errors.root?.message ? (
            <ErrorState message={form.formState.errors.root.message} />
          ) : null}
          {updateProfile.isSuccess ? (
            <p className="form-success" role="status">Votre profil a été mis à jour.</p>
          ) : null}
          <Button type="submit" disabled={updateProfile.isPending}>
            {updateProfile.isPending ? "Enregistrement…" : "Enregistrer les modifications"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
