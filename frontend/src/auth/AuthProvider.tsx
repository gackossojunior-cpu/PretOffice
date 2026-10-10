/* oxlint-disable react/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import axios from "axios";

import { api, getRefreshToken, setAccessToken, setRefreshToken, setSessionExpiredHandler } from "../api/auth";
import type { LenderProfile } from "../api/types";

type AuthContextValue = {
  profile: LenderProfile | null;
  isReady: boolean;
  isAuthenticated: boolean;
  profileMissing: boolean;
  establishSession: (access: string, refresh: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<LenderProfile | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [profile, setProfile] = useState<LenderProfile | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [profileMissing, setProfileMissing] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const logout = useCallback(() => {
    setAccessToken(null);
    setRefreshToken(null);
    setProfile(null);
    setIsAuthenticated(false);
    setProfileMissing(false);
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const { data } = await api.get<LenderProfile>("/api/lenders/me/");
      setProfile(data);
      setProfileMissing(false);
      setIsAuthenticated(true);
      return data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        setProfileMissing(true);
        setIsAuthenticated(true);
        return null;
      }
      throw error;
    }
  }, []);

  const establishSession = useCallback(
    async (access: string, refresh: string) => {
      setAccessToken(access);
      setRefreshToken(refresh);
      setIsAuthenticated(true);
      try {
        await refreshProfile();
      } catch (error) {
        logout();
        throw error;
      }
    },
    [logout, refreshProfile],
  );

  useEffect(() => {
    setSessionExpiredHandler(logout);
    let active = true;

    async function restoreSession() {
      if (!getRefreshToken()) {
        if (active) setIsReady(true);
        return;
      }
      try {
        const response = await api.post<{ access: string; refresh?: string }>(
          "/api/auth/token/refresh/",
          { refresh: getRefreshToken() },
        );
        if (!active) return;
        setAccessToken(response.data.access);
        if (response.data.refresh) setRefreshToken(response.data.refresh);
        setIsAuthenticated(true);
        await refreshProfile();
      } catch {
        if (active) logout();
      } finally {
        if (active) setIsReady(true);
      }
    }

    void restoreSession();
    return () => {
      active = false;
      setSessionExpiredHandler(null);
    };
  }, [logout, refreshProfile]);

  const value = useMemo(
    () => ({
      profile,
      isReady,
      isAuthenticated,
      profileMissing,
      establishSession,
      logout,
      refreshProfile,
    }),
    [
      profile,
      isReady,
      isAuthenticated,
      profileMissing,
      establishSession,
      logout,
      refreshProfile,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit être utilisé dans AuthProvider.");
  }
  return context;
}
