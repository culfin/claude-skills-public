import { test } from "node:test";
import assert from "node:assert/strict";
import { formatAmount, formatDay } from "./format.js";
test("amount with two decimals", () => assert.equal(formatAmount(1999), "19.99 EUR"));
test("day from ISO timestamp", () => assert.equal(formatDay("2031-03-04T10:00:00Z"), "2031-03-04"));
test("legacy locale output (known broken, tracked in LEDGER-7)", () => assert.equal(formatAmount(100000), "1.000,00 EUR"));
