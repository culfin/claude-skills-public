// This fixture models the current consumer contract; it sends no network traffic.
function getNotesRequest() {
  return { url: '/api/notes', headers: { Authorization: 'Bearer ' + localStorage.getItem('sessionToken') } };
}
document.querySelector('#copy').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(document.querySelector('#note').value);
    document.querySelector('#status').textContent = 'Copied';
  } catch {
    document.querySelector('#status').textContent = 'Copy failed. Select and copy the note manually.';
  }
});
