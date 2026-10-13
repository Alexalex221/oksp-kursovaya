// Проверочный прогон: каждое действие профиля один раз. Должны пройти все
// проверки — значит, сценарий ходит в нужные операции под нужной учётной записью.
import { login, useSession } from "../flows/auth.js";
import { freePairs } from "../flows/pairs.js";
import { PROFILE, runOperation } from "../scenarios/profile.js";

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: { checks: ["rate==1"] },
};

export function setup() {
  return { ...login(), pairs: freePairs(5) };
}

export default function (data) {
  useSession(data);
  for (const p of PROFILE) runOperation(p.op, data);
}
