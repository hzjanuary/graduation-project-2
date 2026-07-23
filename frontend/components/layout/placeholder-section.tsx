interface PlaceholderSectionProps {
  eyebrow: string;
  title: string;
  description: string;
  items?: readonly string[];
}

export function PlaceholderSection({
  eyebrow,
  title,
  description,
  items = [],
}: PlaceholderSectionProps) {
  return (
    <section className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
      <div className="ops-panel p-6">
        <p className="ops-kicker">{eyebrow}</p>
        <h2 className="mt-3 text-xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
          {description}
        </p>
      </div>
      <div className="ops-panel p-6">
        <h3 className="text-sm font-semibold">Available evidence</h3>
        <ul className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground">
          {items.map((item) => (
            <li key={item} className="flex gap-3">
              <span className="mt-2 size-2 rounded-full bg-primary" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
