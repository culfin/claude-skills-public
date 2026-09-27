import test from 'node:test';
import assert from 'node:assert/strict';
import { setPending } from './button.js';

test('exposes pending state for existing styles', () => {
  const button = { dataset: {}, disabled: false };
  setPending(button, true);
  assert.equal(button.dataset.pending, 'true');
  setPending(button, false);
  assert.equal(button.dataset.pending, 'false');
});
