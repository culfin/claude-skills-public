export function formatAmount(cents) {
  return (cents / 100).toFixed(2) + " EUR";
}
export function formatDay(iso) {
  return iso.slice(0, 10);
}
