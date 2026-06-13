import { useEffect, useMemo, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import {
  getAuthMode,
  getCurrentPrincipal,
  signInToStaticWebApps,
  signOutFromStaticWebApps,
  type StaticWebAppsPrincipal,
} from "./services/auth";
import { getAdvisorConnectionMode, sendChatMessage } from "./services/foundryClient";
import type { ChatMessage, QuickAction, Recommendation } from "./types";

const createMessage = (role: ChatMessage["role"], content: string): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
  timestamp: new Date().toISOString(),
});

function createInitialMessages(connectionMode: "local" | "foundry"): ChatMessage[] {
  return [
    createMessage(
      "assistant",
      connectionMode === "local"
        ? "Hi — I’m connected to the local FastAPI backend. Use a quick action or ask for analysis, recommendations, simulations, or health."
        : "Hi — I’m the Azure AI Search Advisor prototype. Ask about cost, scale, features, or optimization trade-offs.",
    ),
  ];
}

export default function App() {
  const authMode = useMemo(() => getAuthMode(), []);
  const advisorMode = useMemo(() => getAdvisorConnectionMode(), []);
  const [messages, setMessages] = useState<ChatMessage[]>(() => createInitialMessages(advisorMode));
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [principal, setPrincipal] = useState<StaticWebAppsPrincipal | null>(null);
  const quickActions = useMemo<QuickAction[]>(
    () =>
      advisorMode === "local"
        ? [
            { label: "Analyze sample service", prompt: "Analyze sample service" },
            { label: "Get recommendations", prompt: "Get recommendations" },
            { label: "Cost simulation", prompt: "Cost simulation" },
          ]
        : [],
    [advisorMode],
  );

  useEffect(() => {
    if (authMode !== "static-web-apps" || advisorMode !== "foundry") {
      return;
    }

    getCurrentPrincipal()
      .then(setPrincipal)
      .catch((authError: unknown) => {
        const message = authError instanceof Error ? authError.message : "Unable to load Azure Static Web Apps session.";
        setError(message);
      });
  }, [advisorMode, authMode]);

  const handleSend = async (content: string) => {
    const userMessage = createMessage("user", content);
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage(nextMessages);
      setMessages((currentMessages) => [...currentMessages, createMessage("assistant", response.message)]);
      setRecommendations(response.recommendations);

      if (advisorMode === "foundry" && authMode === "static-web-apps") {
        const nextPrincipal = await getCurrentPrincipal();
        setPrincipal(nextPrincipal);
      }
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Something went wrong while contacting the advisor.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Microsoft Foundry · React prototype</p>
          <h1>Azure AI Search Advisor</h1>
          <p className="subtle-text">
            {advisorMode === "local"
              ? "Connected to the local FastAPI backend for development."
              : "Chat with the advisor agent using Azure identity locally and Azure Static Web Apps auth when deployed."}
          </p>
        </div>
        <div className="header-actions">
          <span className={`mode-chip ${advisorMode}`}>
            {advisorMode === "local" ? "Local API mode" : "Foundry mode"}
          </span>
          <span className="auth-chip">
            {advisorMode === "local"
              ? "No auth required"
              : authMode === "local-browser"
                ? "Local browser auth"
                : principal
                  ? `Signed in as ${principal.userDetails}`
                  : "Static Web Apps auth"}
          </span>
          {advisorMode === "foundry" && authMode === "static-web-apps" ? (
            principal ? (
              <button className="secondary-button" onClick={signOutFromStaticWebApps} type="button">
                Sign out
              </button>
            ) : (
              <button className="secondary-button" onClick={signInToStaticWebApps} type="button">
                Sign in
              </button>
            )
          ) : null}
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <ChatWindow
        disableInput={isLoading}
        isLoading={isLoading}
        messages={messages}
        onSend={handleSend}
        quickActions={quickActions}
        recommendations={recommendations}
      />
    </div>
  );
}
