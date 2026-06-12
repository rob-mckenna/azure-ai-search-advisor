import { useEffect, useMemo, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import {
  getAuthMode,
  getCurrentPrincipal,
  signInToStaticWebApps,
  signOutFromStaticWebApps,
  type StaticWebAppsPrincipal,
} from "./services/auth";
import { sendChatMessage } from "./services/foundryClient";
import type { ChatMessage, Recommendation } from "./types";

const createMessage = (role: ChatMessage["role"], content: string): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
  timestamp: new Date().toISOString(),
});

const initialMessages: ChatMessage[] = [
  createMessage(
    "assistant",
    "Hi — I’m the Azure AI Search Advisor prototype. Ask about cost, scale, features, or optimization trade-offs.",
  ),
];

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [principal, setPrincipal] = useState<StaticWebAppsPrincipal | null>(null);
  const authMode = useMemo(() => getAuthMode(), []);

  useEffect(() => {
    if (authMode !== "static-web-apps") {
      return;
    }

    getCurrentPrincipal()
      .then(setPrincipal)
      .catch((authError: unknown) => {
        const message = authError instanceof Error ? authError.message : "Unable to load Azure Static Web Apps session.";
        setError(message);
      });
  }, [authMode]);

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

      if (authMode === "static-web-apps") {
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
            Chat with the advisor agent using Azure identity locally and Azure Static Web Apps auth when deployed.
          </p>
        </div>
        <div className="header-actions">
          <span className="auth-chip">
            {authMode === "local-browser" ? "Local browser auth" : principal ? `Signed in as ${principal.userDetails}` : "Static Web Apps auth"}
          </span>
          {authMode === "static-web-apps" ? (
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
        recommendations={recommendations}
      />
    </div>
  );
}
