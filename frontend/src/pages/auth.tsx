import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useForm, type FieldPath } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { api, errorMessage } from "../api/auth";
import type { ApiSchemas, LoginPayload, RegisterPayload } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { Button, Card, Field } from "../components/ui";

const loginSchema = z.object({
  username: z.string().min(1, "Saisissez votre nom d’utilisateur."),
  password: z.string().min(1, "Saisissez votre mot de passe."),
});

const registerSchema = z
  .object({
    username: z.string().min(1, "Saisissez un nom d’utilisateur."),
    email: z.email("Saisissez une adresse email valide."),
    first_name: z.string(),
    last_name: z.string(),
    phone: z.string(),
    password: z.string().min(8, "Le mot de passe doit contenir au moins 8 caractères."),
    password_confirm: z.string().min(1, "Confirmez votre mot de passe."),
  })
  .refine((values) => values.password === values.password_confirm, {
    path: ["password_confirm"],
    message: "Les mots de passe ne correspondent pas.",
  });

type LoginValues = z.infer<typeof loginSchema>;
type RegisterValues = z.infer<typeof registerSchema>;
const registerFieldNames = [
  "username",
  "email",
  "first_name",
  "last_name",
  "phone",
  "password",
  "password_confirm",
] as const satisfies readonly FieldPath<RegisterValues>[];

export function LoginPage() {
  const { establishSession } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as { from?: string; registered?: boolean } | null;
  const from = locationState?.from ?? "/tableau-de-bord";
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });
  const login = useMutation({
    mutationFn: async (values: LoginPayload) => {
      const { data } = await api.post<Pick<ApiSchemas["TokenObtainPair"], "access" | "refresh">>(
        "/api/auth/login/",
        values,
      );
      return data;
    },
    onSuccess: async ({ access, refresh }) => {
      try {
        await establishSession(access, refresh);
        navigate(from, { replace: true });
      } catch (error) {
        form.setError("root", { message: errorMessage(error) });
      }
    },
    onError: (error) => form.setError("root", { message: errorMessage(error) }),
  });

  return (
    <main className="auth-page">
      <Card className="auth-card">
        <Link className="auth-brand" to="/">PrêtOffice</Link>
        <p className="eyebrow">Votre espace prêteur</p>
        <h1>Connexion</h1>
        <p className="auth-intro">Connectez-vous pour retrouver vos prêts et vos emprunteurs.</p>
        {locationState?.registered ? (
          <p className="form-success" role="status">Votre compte a été créé. Vous pouvez maintenant vous connecter.</p>
        ) : null}
        <form
          className="form-stack"
          onSubmit={form.handleSubmit((values) => login.mutate(values))}
          noValidate
        >
          <Field label="Nom d’utilisateur" id="username" error={form.formState.errors.username?.message}>
            <input id="username" autoComplete="username" {...form.register("username")} />
          </Field>
          <Field label="Mot de passe" id="password" error={form.formState.errors.password?.message}>
            <input id="password" type="password" autoComplete="current-password" {...form.register("password")} />
          </Field>
          {form.formState.errors.root?.message ? (
            <p className="form-error" role="alert">{form.formState.errors.root.message}</p>
          ) : null}
          <Button type="submit" disabled={login.isPending}>
            {login.isPending ? "Connexion…" : "Se connecter"}
          </Button>
        </form>
        <p className="auth-switch">
          Pas encore de compte ? <Link to="/inscription">Créer un compte prêteur</Link>
        </p>
      </Card>
    </main>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: "",
      email: "",
      first_name: "",
      last_name: "",
      phone: "",
      password: "",
      password_confirm: "",
    },
  });
  const registerAccount = useMutation({
    mutationFn: async (values: RegisterPayload) => {
      const { data } = await api.post("/api/auth/register/", values);
      return data;
    },
    onSuccess: () => navigate("/connexion", { replace: true, state: { registered: true } }),
    onError: (error) => {
      const responseData = axios.isAxiosError(error)
        ? error.response?.data as { errors?: Record<string, unknown> } | undefined
        : undefined;
      const fieldErrors = responseData?.errors;
      let hasFieldError = false;

      if (fieldErrors) {
        for (const fieldName of registerFieldNames) {
          const value = fieldErrors[fieldName];
          const message = Array.isArray(value)
            ? value.filter((item): item is string => typeof item === "string").join(" ")
            : typeof value === "string"
              ? value
              : "";

          if (message) {
            form.setError(fieldName, { type: "server", message });
            hasFieldError = true;
          }
        }
      }

      if (!hasFieldError) {
        form.setError("root", { message: errorMessage(error) });
      } else {
        form.clearErrors("root");
      }
    },
  });

  return (
    <main className="auth-page">
      <Card className="auth-card auth-card-wide">
        <Link className="auth-brand" to="/">PrêtOffice</Link>
        <p className="eyebrow">Commencez simplement</p>
        <h1>Créer un compte prêteur</h1>
        <p className="auth-intro">Votre profil prêteur sera créé automatiquement après l’inscription.</p>
        <form
          className="form-stack"
          onSubmit={form.handleSubmit((values) => registerAccount.mutate(values))}
          noValidate
        >
          <div className="form-grid">
            <Field label="Nom d’utilisateur" id="register-username" error={form.formState.errors.username?.message}>
              <input id="register-username" autoComplete="username" {...form.register("username")} />
            </Field>
            <Field label="Adresse email" id="register-email" error={form.formState.errors.email?.message}>
              <input id="register-email" type="email" autoComplete="email" {...form.register("email")} />
            </Field>
            <Field label="Prénom" id="first-name" error={form.formState.errors.first_name?.message}>
              <input id="first-name" autoComplete="given-name" {...form.register("first_name")} />
            </Field>
            <Field label="Nom" id="last-name" error={form.formState.errors.last_name?.message}>
              <input id="last-name" autoComplete="family-name" {...form.register("last_name")} />
            </Field>
          </div>
          <Field label="Téléphone" id="phone" error={form.formState.errors.phone?.message}>
            <input id="phone" type="tel" autoComplete="tel" {...form.register("phone")} />
          </Field>
          <div className="form-grid">
            <Field label="Mot de passe" id="register-password" error={form.formState.errors.password?.message}>
              <input id="register-password" type="password" autoComplete="new-password" {...form.register("password")} />
            </Field>
            <Field label="Confirmer le mot de passe" id="password-confirm" error={form.formState.errors.password_confirm?.message}>
              <input id="password-confirm" type="password" autoComplete="new-password" {...form.register("password_confirm")} />
            </Field>
          </div>
          {form.formState.errors.root?.message ? (
            <p className="form-error" role="alert">{form.formState.errors.root.message}</p>
          ) : null}
          <Button type="submit" disabled={registerAccount.isPending}>
            {registerAccount.isPending ? "Création du compte…" : "Créer mon compte"}
          </Button>
        </form>
        <p className="auth-switch">
          Vous avez déjà un compte ? <Link to="/connexion">Se connecter</Link>
        </p>
      </Card>
    </main>
  );
}
