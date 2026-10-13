import http from "k6/http";
import { fail } from "k6";

import { BASE } from "../config.js";

// Подбор пар «свободный экземпляр — читатель без просрочек» для выдач под
// нагрузкой. Выполняется в setup(), запросы помечены operation: setup и в
// пороги не входят.
export function freePairs(count) {
  const tags = { tags: { operation: "setup" } };
  const readers = [];
  for (let id = 1; readers.length < count && id <= 3000; id += 7) {
    const r = http.get(`${BASE}/api/readers/${id}`, tags);
    if (r.status === 200 && r.json("stats.overdue") === 0) readers.push(id);
  }
  const copies = [];
  for (let id = 11; copies.length < count && id <= 10000; id += 13) {
    const r = http.get(`${BASE}/api/books/${id}`, tags);
    if (r.status !== 200) continue;
    for (const c of r.json("copies")) {
      if (c.status === "free" && copies.length < count) copies.push(c.id);
    }
  }
  if (readers.length < count || copies.length < count) {
    fail(`не набрано ${count} пар: читателей ${readers.length}, экземпляров ${copies.length}`);
  }
  return readers.map((reader, i) => ({ reader, copy: copies[i] }));
}
