export function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatHours(hours: number | null | undefined): string {
  if (hours == null) {
    return "\u2014";
  }
  if (hours < 48) {
    return `${hours.toFixed(1)} h`;
  }
  return `${(hours / 24).toFixed(1)} days`;
}
