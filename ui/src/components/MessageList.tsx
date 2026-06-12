import type { ChatMessage } from "../types";

interface MessageListProps {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="message-list" role="log" aria-live="polite">
      {messages.map((message) => (
        <article className={`message-bubble ${message.role}`} key={message.id}>
          <div className="message-meta">
            <span>{message.role === "assistant" ? "Advisor" : "You"}</span>
            <time dateTime={message.timestamp}>{new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
          </div>
          <p>{message.content}</p>
        </article>
      ))}
    </div>
  );
}
