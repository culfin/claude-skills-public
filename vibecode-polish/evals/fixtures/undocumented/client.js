import { formatTimestamp } from './date.js';
export function getNotesRequest(storage) {
  return { url: '/api/notes', headers: { Authorization: 'Bearer ' + storage.getItem('sessionToken') } };
}
const stamp = document.querySelector('time');
stamp.textContent = stamp.dateTime;
