import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type AxiosResponse,
} from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  api,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./auth";

afterEach(() => {
  setAccessToken(null);
  setRefreshToken(null);
});

describe("session JWT", () => {
  it("renouvelle une fois un access expiré et rejoue la requête", async () => {
    const originalAdapter = api.defaults.adapter;
    const adapter: AxiosAdapter = async (config) => {
      if (config.headers.get("Authorization") !== "Bearer access-renouvelé") {
        const response: AxiosResponse = {
          data: { detail: "Jeton expiré." },
          status: 401,
          statusText: "Unauthorized",
          headers: new AxiosHeaders(),
          config,
        };
        throw new AxiosError("Unauthorized", "ERR_BAD_REQUEST", config, undefined, response);
      }
      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: new AxiosHeaders(),
        config,
      };
    };
    const refreshResponse: AxiosResponse = {
      data: { access: "access-renouvelé", refresh: "refresh-rotaté" },
      status: 200,
      statusText: "OK",
      headers: new AxiosHeaders(),
      config: { headers: new AxiosHeaders() },
    };
    const refreshSpy = vi.spyOn(axios, "post").mockResolvedValue(refreshResponse);
    api.defaults.adapter = adapter;
    setRefreshToken("refresh-initial");

    try {
      const response = await api.get<{ ok: boolean }>("/api/test-protected/");
      expect(response.data.ok).toBe(true);
      expect(refreshSpy).toHaveBeenCalledTimes(1);
      expect(getRefreshToken()).toBe("refresh-rotaté");
    } finally {
      api.defaults.adapter = originalAdapter;
      refreshSpy.mockRestore();
    }
  });

  it("ne tente pas un renouvellement récursif lorsque l’endpoint refresh renvoie 401", async () => {
    const originalAdapter = api.defaults.adapter;
    const adapter: AxiosAdapter = async (config) => {
      const response: AxiosResponse = {
        data: { detail: "Jeton invalide." },
        status: 401,
        statusText: "Unauthorized",
        headers: new AxiosHeaders(),
        config,
      };
      throw new AxiosError("Unauthorized", "ERR_BAD_REQUEST", config, undefined, response);
    };
    const refreshSpy = vi.spyOn(axios, "post");
    api.defaults.adapter = adapter;

    try {
      await expect(api.post("/api/auth/token/refresh/", { refresh: "expired" })).rejects.toBeInstanceOf(AxiosError);
      expect(refreshSpy).not.toHaveBeenCalled();
    } finally {
      api.defaults.adapter = originalAdapter;
      refreshSpy.mockRestore();
    }
  });
});
