import http from "k6/http";
import { check, fail } from "k6";

import { BASE, PASSWORD, USER } from "../config.js";

const COOKIE = "library_session";

// Вход выполняется один раз в setup(): сеансовая кука подписана сервером,
// и все виртуальные пользователи работают под ней, не нагружая сервис
// хешированием пароля на каждой итерации.
export function login() {
  const response = http.post(
    `${BASE}/api/login`,
    JSON.stringify({ login: USER, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" }, tags: { operation: "login" } },
  );

  const cookie = response.cookies[COOKIE];
  const ok = check(response, {
    "вход: ответ 200": (r) => r.status === 200,
    "вход: получена сеансовая кука": () => cookie && cookie.length > 0,
  });
  if (!ok) {
    fail(`вход под ${USER} не удался: ${response.status} ${response.body}`);
  }

  return { session: cookie[0].value };
}

// Положить куку сеанса в хранилище кук текущего виртуального пользователя.
export function useSession(data) {
  http.cookieJar().set(BASE, COOKIE, data.session);
}
