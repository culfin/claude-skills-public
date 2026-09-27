import test from 'node:test';
import assert from 'node:assert/strict';
import { formatTimestamp } from './date.js';
test('timestamp display is a string', () => {
  assert.equal(typeof formatTimestamp('2026-09-27T07:45:00Z', 'en-GB'), 'string');
});
