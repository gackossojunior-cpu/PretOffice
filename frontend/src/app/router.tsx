/* oxlint-disable react/only-export-components */
import {
  createBrowserRouter,
  Navigate,
  useLocation,
} from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { ErrorState, LoadingState } from "../components/ui";
import { AppLayout } from "./shell";

function ProtectedLayout() {
  const { isAuthenticated, isReady, profileMissing } = useAuth();
  const location = useLocation();

  if (!isReady) return <LoadingState label="Vérification de la session…" />;
  if (!isAuthenticated) {
    return (
      <Navigate to="/connexion" replace state={{ from: location.pathname }} />
    );
  }
  if (profileMissing) {
    return (
      <main className="standalone-page">
        <ErrorState message="Aucun profil prêteur n'est associé à ce compte. Contactez l'assistance." />
      </main>
    );
  }
  return <AppLayout />;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/tableau-de-bord" replace />,
  },
  {
    path: "/connexion",
    HydrateFallback: LoadingState,
    lazy: async () => {
      const module = await import("../pages/auth");
      return { Component: module.LoginPage };
    },
  },
  {
    path: "/inscription",
    HydrateFallback: LoadingState,
    lazy: async () => {
      const module = await import("../pages/auth");
      return { Component: module.RegisterPage };
    },
  },
  {
    path: "/invitation/:token",
    HydrateFallback: LoadingState,
    lazy: async () => {
      const module = await import("../pages/invitation");
      return { Component: module.PublicInvitationPage };
    },
  },
  {
    element: <ProtectedLayout />,
    HydrateFallback: LoadingState,
    children: [
      {
        path: "tableau-de-bord",
        lazy: async () => {
          const module = await import("../pages/dashboard");
          return { Component: module.DashboardPage };
        },
      },
      {
        path: "emprunteurs",
        lazy: async () => {
          const module = await import("../pages/borrowers");
          return { Component: module.BorrowersPage };
        },
      },
      {
        path: "emprunteurs/:id",
        lazy: async () => {
          const module = await import("../pages/borrowers");
          return { Component: module.BorrowerDetailPage };
        },
      },
      {
        path: "invitations",
        lazy: async () => {
          const module = await import("../pages/invitations");
          return { Component: module.InvitationsPage };
        },
      },
      {
        path: "demandes",
        lazy: async () => {
          const module = await import("../pages/loans");
          return { Component: module.LoanApplicationsPage };
        },
      },
      {
        path: "prets",
        lazy: async () => {
          const module = await import("../pages/loans");
          return { Component: module.LoansPage };
        },
      },
      {
        path: "prets/:id",
        lazy: async () => {
          const module = await import("../pages/loans");
          return { Component: module.LoanDetailPage };
        },
      },
      {
        path: "profil",
        HydrateFallback: LoadingState,
        lazy: async () => {
          const module = await import("../pages/profile");
          return { Component: module.ProfilePage };
        },
      },
    ],
  },
]);
