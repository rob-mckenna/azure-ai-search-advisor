import LoadingIndicator from "./LoadingIndicator";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";
import type { ChatMessage, QuickAction, Recommendation } from "../types";

interface ChatWindowProps {
  messages: ChatMessage[];
  recommendations: Recommendation[];
  isLoading: boolean;
  disableInput?: boolean;
  onSend: (message: string) => Promise<void> | void;
  quickActions?: QuickAction[];
}

export default function ChatWindow({
  messages,
  recommendations,
  isLoading,
  disableInput = false,
  onSend,
  quickActions = [],
}: ChatWindowProps) {
  return (
    <main className="chat-layout">
      <section className="chat-panel">
        <MessageList messages={messages} />
        {isLoading ? <LoadingIndicator /> : null}
        {quickActions.length > 0 ? (
          <div className="quick-actions-panel">
            <div className="quick-actions-header">
              <strong>Quick actions</strong>
              <span className="subtle-text">Local backend samples</span>
            </div>
            <div className="quick-actions-list">
              {quickActions.map((quickAction) => (
                <button
                  className="secondary-button quick-action-button"
                  disabled={disableInput}
                  key={quickAction.label}
                  onClick={() => void onSend(quickAction.prompt)}
                  type="button"
                >
                  {quickAction.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <MessageInput disabled={disableInput} onSend={onSend} />
      </section>

      <aside className="sidebar-panel">
        <div className="sidebar-card">
          <h2>Latest findings</h2>
          {recommendations.length === 0 ? (
            <p className="subtle-text">Structured recommendations will appear here after the advisor returns them.</p>
          ) : (
            <ul className="recommendation-list">
              {recommendations.map((recommendation) => (
                <li className="recommendation-item" key={recommendation.id}>
                  <div className="recommendation-heading">
                    <strong>{recommendation.title}</strong>
                    {recommendation.priority ? <span>{recommendation.priority}</span> : null}
                  </div>
                  <p>{recommendation.detail}</p>
                  {recommendation.category ? <small>{recommendation.category}</small> : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </main>
  );
}
