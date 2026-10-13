// Одна ступень открытой нагрузки: RATE действий библиотекаря в секунду.
import { DURATION, LIMIT_MS, RATE } from "../config.js";
import { login, useSession } from "../flows/auth.js";
import { freePairs } from "../flows/pairs.js";
import { librarianStep } from "../scenarios/profile.js";

export const options = {
  scenarios: {
    step: {
      executor: "constant-arrival-rate", // открытая модель: темп не зависит от ответов
      rate: RATE,
      timeUnit: "1s",
      duration: DURATION,
      preAllocatedVUs: Math.max(20, RATE * 4),
      maxVUs: Math.max(100, RATE * 20),
    },
  },
  thresholds: {
    // все действия профиля; вход и подготовка из setup() в выборку не входят
    "http_req_duration{profile:librarian}": [`p(95)<${LIMIT_MS}`],
    "http_req_failed{profile:librarian}": ["rate<0.01"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "max"],
};

export function setup() {
  return { ...login(), pairs: freePairs(200) };
}

export default function (data) {
  useSession(data);
  librarianStep(data);
}
