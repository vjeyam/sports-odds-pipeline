type TabItem<T extends string> = { value: T; label: string };

export function Tabs<T extends string>(props: {
  value: T;
  onChange: (v: T) => void;
  items: TabItem<T>[];
}) {
  const { value, onChange, items } = props;

  return (
    <div style={{ display: "flex", gap: 8 }}>
      {items.map((it) => (
        <button
          key={it.value}
          onClick={() => onChange(it.value)}
          disabled={value === it.value}
          style={{ padding: "8px 12px" }}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
