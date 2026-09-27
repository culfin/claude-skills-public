export function setPending(button, pending) {
  button.dataset.pending = String(pending);
  button.disabled = false;
}
