import { check } from "k6";

// Смысловые проверки ответа. Кроме кода смотрим на состав тела: если сеанс
// слетит, сервис ответит быстрым 401, и без проверки тела замер окажется
// замером не той операции. Тело разбирается, только если пришёл ответ 200:
// под перегрузкой сервис отвечает 500 с текстом, а не с JSON.

function json(r, field) {
  if (r.status !== 200 && r.status !== 201) return undefined;
  try {
    return field === undefined ? r.json() : r.json(field);
  } catch (e) {
    return undefined;
  }
}

export function checkPage(response, name) {
  return check(response, {
    [`${name}: 200`]: (r) => r.status === 200,
    [`${name}: страница записей`]: (r) => {
      const body = json(r);
      return body !== undefined && Array.isArray(body.items) && typeof body.total === "number";
    },
  });
}

export function checkCard(response, name, field) {
  return check(response, {
    [`${name}: 200`]: (r) => r.status === 200,
    [`${name}: карточка`]: (r) => {
      const value = json(r, field);
      return value !== undefined && value !== null;
    },
  });
}

export function checkStatus(response, name, status) {
  return check(response, { [`${name}: ${status}`]: (r) => r.status === status });
}
