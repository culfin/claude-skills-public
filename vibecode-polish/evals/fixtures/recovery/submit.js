import { setPending } from './button.js';
export async function submit(button, save) {
  setPending(button, true);
  const result = await save();
  setPending(button, false);
  return result;
}
