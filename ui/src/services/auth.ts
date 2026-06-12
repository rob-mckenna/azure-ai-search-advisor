import { InteractiveBrowserCredential } from "@azure/identity";

export type AuthMode = "local-browser" | "static-web-apps";

export interface StaticWebAppsPrincipal {
  userId: string;
  userDetails: string;
  identityProvider: string;
  userRoles: string[];
}

interface StaticWebAppsAuthEntry {
  access_token?: string;
  accessToken?: string;
  clientPrincipal?: StaticWebAppsPrincipal;
}

const TOKEN_SCOPE = "https://ai.azure.com/.default";

let browserCredential: InteractiveBrowserCredential | null = null;

export function getAuthMode(): AuthMode {
  if (import.meta.env.DEV) {
    return "local-browser";
  }

  return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "local-browser"
    : "static-web-apps";
}

function getBrowserCredential(): InteractiveBrowserCredential {
  if (browserCredential) {
    return browserCredential;
  }

  const clientId = import.meta.env.VITE_AZURE_CLIENT_ID;
  if (!clientId) {
    throw new Error("Missing VITE_AZURE_CLIENT_ID. Add it to ui/.env before starting the app locally.");
  }

  browserCredential = new InteractiveBrowserCredential({
    clientId,
    loginStyle: "popup",
    redirectUri: window.location.origin,
  });

  return browserCredential;
}

async function readStaticWebAppsSession(): Promise<StaticWebAppsAuthEntry[]> {
  const response = await fetch("/.auth/me", {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    return [];
  }

  const payload = (await response.json()) as StaticWebAppsAuthEntry[];
  return Array.isArray(payload) ? payload : [];
}

export async function getAccessToken(): Promise<string | null> {
  if (getAuthMode() !== "local-browser") {
    return null;
  }

  const token = await getBrowserCredential().getToken(TOKEN_SCOPE);
  if (!token?.token) {
    throw new Error("Unable to acquire an Azure access token for the Microsoft Foundry endpoint.");
  }

  return token.token;
}

export async function getCurrentPrincipal(): Promise<StaticWebAppsPrincipal | null> {
  if (getAuthMode() !== "static-web-apps") {
    return null;
  }

  const session = await readStaticWebAppsSession();
  return session.find((entry) => entry.clientPrincipal)?.clientPrincipal ?? null;
}

export async function ensureStaticWebAppsLogin(): Promise<void> {
  const principal = await getCurrentPrincipal();
  if (principal) {
    return;
  }

  signInToStaticWebApps();
  throw new Error("Redirecting to Azure Static Web Apps login.");
}

export function signInToStaticWebApps(): void {
  const redirect = encodeURIComponent(window.location.pathname || "/");
  window.location.assign(`/.auth/login/aad?post_login_redirect_uri=${redirect}`);
}

export function signOutFromStaticWebApps(): void {
  window.location.assign("/.auth/logout");
}
