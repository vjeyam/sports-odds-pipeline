export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div style={{ marginTop: 12, padding: 12, border: "1px solid #f99" }}>
      <strong>Error:</strong> {error}
    </div>
  );
}
