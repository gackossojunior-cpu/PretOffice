import { useState } from "react";
import {
  ArrowUpRight,
  HandCoins,
  LayoutDashboard,
  Menu,
  UserRound,
  UsersRound,
  WalletCards,
  X,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/ui";

const navigation = [
  { label: "Tableau de bord", to: "/tableau-de-bord", icon: LayoutDashboard },
  { label: "Emprunteurs", to: "/emprunteurs", icon: UsersRound },
  { label: "Invitations", to: "/invitations", icon: ArrowUpRight },
  { label: "Demandes de prêt", to: "/demandes", icon: HandCoins },
  { label: "Prêts et remboursements", to: "/prets", icon: WalletCards },
  { label: "Mon profil", to: "/profil", icon: UserRound },
];

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { profile, logout } = useAuth();

  const navigationLinks = (
    <>
      {navigation.map(({ label, to, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `sidebar-link${isActive ? " sidebar-link-active" : ""}`
          }
          onClick={() => setMenuOpen(false)}
        >
          <Icon size={19} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </>
  );

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Navigation principale">
        <NavLink className="brand" to="/tableau-de-bord">
          PrêtOffice
        </NavLink>
        <nav className="sidebar-nav">{navigationLinks}</nav>
        <div className="sidebar-footer">
          <span className="sidebar-avatar" aria-hidden="true">
            {profile?.first_name?.charAt(0) || profile?.username.charAt(0) || "P"}
          </span>
          <span className="sidebar-user">
            <strong>{profile?.business_name || profile?.first_name || "Prêteur"}</strong>
            <span>Espace privé</span>
          </span>
          <Button
            variant="ghost"
            className="logout-button"
            onClick={logout}
            aria-label="Se déconnecter"
          >
            <X size={17} aria-hidden="true" />
          </Button>
        </div>
      </aside>

      <div className="app-main">
        <header className="mobile-header">
          <NavLink className="brand" to="/tableau-de-bord">
            PrêtOffice
          </NavLink>
          <div className="mobile-header-actions">
            <button
              type="button"
              className="icon-button"
              aria-label={menuOpen ? "Fermer le menu" : "Ouvrir le menu"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? <X size={21} /> : <Menu size={21} />}
            </button>
          </div>
        </header>
        {menuOpen ? (
          <nav className="mobile-nav" aria-label="Navigation mobile">
            {navigationLinks}
            <Button variant="secondary" onClick={logout}>
              Se déconnecter
            </Button>
          </nav>
        ) : null}
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
