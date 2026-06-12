export default function LoadingIndicator() {
  return (
    <div className="loading-indicator" aria-live="polite" aria-label="Advisor is generating a response">
      <span />
      <span />
      <span />
      <p>Advisor is thinking…</p>
    </div>
  );
}
