// Разгон: пять ступеней от START_RATE до PEAK_RATE, чтобы найти диапазон,
// в котором лежит предел. Числа разгона в таблицу ступеней не идут.
import { LIMIT_MS, PEAK_RATE, START_RATE, STEP_TIME } from "../config.js";
import { login, useSession } from "../flows/auth.js";
import { freePairs } from "../flows/pairs.js";
import { librarianStep } from "../scenarios/profile.js";

const STEPS = 5;
const rates = Array.from({ length: STEPS }, (_, i) =>
  Math.round(START_RATE + ((PEAK_RATE - START_RATE) * i) / (STEPS - 1)));

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-arrival-rate",
      startRate: START_RATE,
      timeUnit: "1s",
      preAllocatedVUs: Math.max(20, PEAK_RATE * 2),
      maxVUs: Math.max(200, PEAK_RATE * 20),
      stages: rates.map((target) => ({ target, duration: STEP_TIME })),
    },
  },
  thresholds: {
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
