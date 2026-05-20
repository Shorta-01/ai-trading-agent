export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="empty-state">
      <p className="empty-title">{title}</p>
      <p>{message}</p>
    </div>
  );
}
