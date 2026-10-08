// Общие параметры нагрузочных тестов k6.
// Любое значение переопределяется флагом -e без правки исходников:
//   docker compose run --rm k6 run -e USER=librarian /load/tests/...

export const BASE = __ENV.BASE || "http://api:8000";

// Все испытания идут под одной учётной записью — той же, что и замеры этапа 1.
export const USER = __ENV.USER || "librarian";
export const PASSWORD = __ENV.PASSWORD || "librarian";
