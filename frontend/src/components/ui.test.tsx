import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/auth";
import { AmountXAF, StatusBadge } from "./ui";
import { AuthProvider } from "../auth/AuthProvider";
import { LoginPage, RegisterPage } from "../pages/auth";

function renderAuthPage(page: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>{page}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("composants partagés", () => {
  it("formate les montants en XAF sans décimales", () => {
    render(<AmountXAF value="1500.40" />);
    expect(screen.getByText((content) => content.replace(/\s/g, "").includes("1500FCFA"))).toBeInTheDocument();
  });

  it("affiche un libellé textuel pour les statuts", () => {
    render(<StatusBadge status="overdue" />);
    expect(screen.getByText("En retard")).toBeInTheDocument();
  });
});

describe("formulaires d’authentification", () => {
  it("affiche les validations locales à la soumission de connexion vide", async () => {
    renderAuthPage(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByText("Saisissez votre nom d’utilisateur.")).toBeInTheDocument();
    expect(screen.getByText("Saisissez votre mot de passe.")).toBeInTheDocument();
  });

  it("refuse les mots de passe de confirmation différents", async () => {
    renderAuthPage(<RegisterPage />);
    fireEvent.change(screen.getByLabelText("Nom d’utilisateur"), { target: { value: "preteur_test" } });
    fireEvent.change(screen.getByLabelText("Adresse email"), { target: { value: "test@example.invalid" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "MotDePasse-Temporaire-123!" } });
    fireEvent.change(screen.getByLabelText("Confirmer le mot de passe"), { target: { value: "Different-Password-123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));
    expect(await screen.findByText("Les mots de passe ne correspondent pas.")).toBeInTheDocument();
  });

  it("affiche une erreur 400 du backend sur le champ concerné", async () => {
    const post = vi.spyOn(api, "post").mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 400,
        data: {
          detail: "La requête n'a pas pu être traitée.",
          errors: { password: ["Ce mot de passe est trop courant."] },
        },
      },
    });
    renderAuthPage(<RegisterPage />);
    fireEvent.change(screen.getByLabelText("Nom d’utilisateur"), { target: { value: "preteur_universel" } });
    fireEvent.change(screen.getByLabelText("Adresse email"), { target: { value: "test@example.invalid" } });
    fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: "MotDePasse-Demo-9051!" } });
    fireEvent.change(screen.getByLabelText("Confirmer le mot de passe"), { target: { value: "MotDePasse-Demo-9051!" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));
    expect(await screen.findByText("Ce mot de passe est trop courant.")).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
  });
});
