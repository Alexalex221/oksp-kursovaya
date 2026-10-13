// Общие параметры нагрузочных тестов k6.
// Любое значение переопределяется флагом -e без правки исходников:
//   docker compose run --rm k6 run -e RATE=40 /load/tests/open-step.test.js

export const BASE = __ENV.BASE || "http://api:8000";

// Все испытания идут под одной учётной записью — той же, что и замеры этапа 1.
export const USER = __ENV.USER || "librarian";
export const PASSWORD = __ENV.PASSWORD || "librarian";

// Критерий приёмки: 95 % операций профиля укладываются в LIMIT_MS.
export const LIMIT_MS = Number(__ENV.LIMIT_MS || 500);

// Ступень открытой нагрузки: RATE операций профиля в секунду в течение DURATION.
export const RATE = Number(__ENV.RATE || 2);
export const DURATION = __ENV.DURATION || "10s";

// Разгон: от START_RATE до PEAK_RATE пятью ступенями по STEP_TIME.
export const START_RATE = Number(__ENV.START_RATE || 5);
export const PEAK_RATE = Number(__ENV.PEAK_RATE || 80);
export const STEP_TIME = __ENV.STEP_TIME || "10s";
