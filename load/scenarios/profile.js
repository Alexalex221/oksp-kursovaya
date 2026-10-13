import http from "k6/http";
import exec from "k6/execution";

import { BASE } from "../config.js";
import { checkCard, checkPage, checkStatus } from "../validators/api.js";

// Профиль нагрузки: смена библиотекаря на абонементе. Одна итерация — одно
// действие библиотекаря, действие выбирается случайно с весом из таблицы.
// Веса — доли действий за смену, в сумме 100.
export const PROFILE = [
  { op: "loans", weight: 25, run: loans },                 // журнал выдач, первые страницы
  { op: "loans_filter", weight: 15, run: loansFiltered },  // журнал с фильтром
  { op: "books_search", weight: 15, run: booksSearch },    // поиск книги
  { op: "book_card", weight: 10, run: bookCard },          // карточка книги
  { op: "readers_search", weight: 8, run: readersSearch }, // поиск читателя
  { op: "reader_card", weight: 10, run: readerCard },      // карточка читателя
  { op: "loan_card", weight: 7, run: loanCard },           // карточка выдачи
  { op: "summary", weight: 5, run: summary },              // сводка
  { op: "issue_return", weight: 5, run: issueReturn },     // выдача и возврат
];

// Объём рабочего наполнения: идентификаторы берутся из этих диапазонов.
const READERS = 3000;
const BOOKS = 10000;
const LOANS = 100000;

const BOOK_WORDS = ["дом", "берег", "город", "сад", "путь", "ветер", "маяк", "остров",
  "Тихий", "Северный", "Забытый", "архив", "поезд", "Иванов", "Смирнов", "Орлов"];
const READER_WORDS = ["Иван", "Анна", "Петров", "Соколов", "Мария", "Алексеев",
  "Ольга", "Козлов", "Дмитрий", "Егоров"];
const STATUSES = ["active", "overdue", "returned"];

// Опыт с урезанным профилем: -e EXCLUDE=loans,loans_filter убирает действия
// из смеси, остальные сохраняют свои веса относительно друг друга.
const EXCLUDE = (__ENV.EXCLUDE || "").split(",").filter((s) => s);
const ACTIVE = PROFILE.filter((p) => !EXCLUDE.includes(p.op));
const TOTAL = ACTIVE.reduce((s, p) => s + p.weight, 0);

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function id(max) {
  return 1 + Math.floor(Math.random() * max);
}

function get(path, op) {
  return http.get(`${BASE}${path}`, { tags: { operation: op, profile: "librarian" } });
}

function loans() {
  const page = 1 + Math.floor(Math.random() * 3);
  checkPage(get(`/api/loans?page=${page}`, "loans"), "журнал");
}

function loansFiltered() {
  const r = Math.random();
  let query;
  if (r < 0.34) query = `status=${pick(STATUSES)}`;
  else if (r < 0.67) query = `reader_id=${id(READERS)}`;
  else query = `book_id=${id(BOOKS)}`;
  checkPage(get(`/api/loans?${query}`, "loans_filter"), "журнал с фильтром");
}

function booksSearch() {
  checkPage(get(`/api/books?q=${encodeURIComponent(pick(BOOK_WORDS))}`, "books_search"), "поиск книг");
}

function bookCard() {
  checkCard(get(`/api/books/${id(BOOKS)}`, "book_card"), "карточка книги", "copies");
}

function readersSearch() {
  checkPage(get(`/api/readers?q=${encodeURIComponent(pick(READER_WORDS))}`, "readers_search"), "поиск читателей");
}

function readerCard() {
  checkCard(get(`/api/readers/${id(READERS)}`, "reader_card"), "карточка читателя", "stats");
}

function loanCard() {
  checkCard(get(`/api/loans/${id(LOANS)}`, "loan_card"), "карточка выдачи", "book");
}

function summary() {
  checkCard(get("/api/summary", "summary"), "сводка", "top_books");
}

// Выдача свободного экземпляра и сразу возврат: в базе прибавляется одна
// закрытая выдача, экземпляр остаётся свободным для следующих итераций.
// Пары «экземпляр — читатель» подготовлены в setup() и берутся по кругу,
// поэтому одновременные итерации не выдают один экземпляр дважды.
function issueReturn(data) {
  const i = exec.scenario.iterationInTest % data.pairs.length;
  const pair = data.pairs[i];
  const tags = { operation: "issue", profile: "librarian" };
  const issued = http.post(
    `${BASE}/api/loans`,
    JSON.stringify({ copy_id: pair.copy, reader_id: pair.reader }),
    { headers: { "Content-Type": "application/json" }, tags },
  );
  if (!checkStatus(issued, "выдача", 201)) return;
  const back = http.post(`${BASE}/api/loans/${issued.json("id")}/return`, null, {
    tags: { operation: "return", profile: "librarian" },
  });
  checkStatus(back, "возврат", 200);
}

// Одно действие библиотекаря по весам профиля.
export function librarianStep(data) {
  let r = Math.random() * TOTAL;
  for (const p of ACTIVE) {
    r -= p.weight;
    if (r < 0) return p.run(data);
  }
  return ACTIVE[ACTIVE.length - 1].run(data);
}

// Одно действие заданного вида — для проверочного прогона.
export function runOperation(op, data) {
  return PROFILE.find((p) => p.op === op).run(data);
}
