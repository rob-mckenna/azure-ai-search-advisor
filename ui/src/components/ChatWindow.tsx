import LoadingIndicator from "./LoadingIndicator";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";
import type { ChatMessage, Recommendation } from "../types";

interface ChatWindowProps {
  messages: ChatMessage[];
  recommendations: Recommendation[];
  isLoading: boolean;
  disableInput?: boolean;
  onSend: (message: string) => Promise<void> | void;
}

export default function ChatWindow({
  messages,
  recommendations,
  isLoading,
  disableInput = false,
  onSend,
}: ChatWindowProps) {
  return (
    <main className="chat-layout">
      <section className="chat-panel">
        <MessageList messages={messages} />
        {isLoading ? <LoadingIndicator /> : null}
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
