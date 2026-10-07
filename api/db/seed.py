"""Наполнение базы данных.

Генерация детерминирована: генератор случайных чисел инициализируется
постоянным зерном, даты отсчитываются от SEED_BASE_DATE, поэтому повторный
запуск с тем же объёмом даёт ту же базу до последней записи.
"""

import hashlib
import random
from dataclasses import dataclass
from datetime import date, timedelta

from app.config import settings
from app.security import hash_password

SEED = 20260917

# Учётная запись, под которой работает интерфейс и снимаются замеры.
ACCOUNT = ("librarian", "librarian", "Библиотекарь абонемента")


@dataclass(frozen=True)
class Size:
    readers: int
    books: int
    copies: int
    loans: int


SIZES = {
    "small": Size(readers=50, books=100, copies=200, loans=300),
    "work": Size(readers=3_000, books=10_000, copies=30_000, loans=100_000),
}

# Выдачи распределяются по двум последним годам.
HISTORY_DAYS = 730
# Не больше стольких выдач на один экземпляр: иначе они не помещаются
# в историю без наложений.
MAX_LOANS_PER_COPY = 24
# Доля экземпляров, которые в момент наполнения на руках.
OPEN_SHARE = 0.12

LAST_NAMES = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов",
    "Михайлов", "Новиков", "Фёдоров", "Морозов", "Волков", "Алексеев", "Лебедев",
    "Семёнов", "Егоров", "Павлов", "Козлов", "Степанов", "Николаев", "Орлов",
    "Андреев", "Макаров", "Никитин", "Захаров", "Зайцев", "Соловьёв", "Борисов",
    "Яковлев", "Григорьев", "Романов", "Воробьёв", "Сергеев", "Кузьмин", "Фролов",
]
FIRST_NAMES_M = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей",
                 "Артём", "Илья", "Кирилл", "Михаил", "Никита", "Иван", "Егор"]
FIRST_NAMES_F = ["Анна", "Мария", "Елена", "Ольга", "Наталья", "Екатерина",
                 "Татьяна", "Ирина", "Дарья", "Алина", "Полина", "Виктория"]
PATRONYMICS_M = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич",
                 "Алексеевич", "Михайлович", "Иванович", "Петрович"]
PATRONYMICS_F = ["Александровна", "Дмитриевна", "Сергеевна", "Андреевна",
                 "Алексеевна", "Михайловна", "Ивановна", "Петровна"]
TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ы": "y", "ь": "", "ъ": "", "э": "e",
    "ю": "yu", "я": "ya",
})

TITLE_ADJ = ["Тихий", "Последний", "Северный", "Забытый", "Белый", "Долгий",
             "Старый", "Ночной", "Новый", "Дальний", "Красный", "Пустой",
             "Ясный", "Первый", "Тайный", "Золотой", "Морской", "Горный"]
TITLE_NOUN = ["дом", "берег", "город", "сад", "путь", "ветер", "огонь", "остров",
              "мост", "лес", "свет", "век", "рассвет", "перевал", "архив",
              "маяк", "двор", "поезд", "колокол", "переулок"]
TITLE_TAIL = ["", "", "", " и другие рассказы", ". Книга вторая", ". Хроники",
              " над рекой", " в сумерках", " за горизонтом", ": повесть"]
GENRES = ["роман", "повесть", "детектив", "фантастика", "история", "поэзия",
          "научно-популярная", "учебная", "детская", "биография"]


def person(rng: random.Random) -> str:
    last = rng.choice(LAST_NAMES)
    if rng.random() < 0.5:
        return f"{last} {rng.choice(FIRST_NAMES_M)} {rng.choice(PATRONYMICS_M)}"
    return f"{last}а {rng.choice(FIRST_NAMES_F)} {rng.choice(PATRONYMICS_F)}"


def account_rows() -> list[tuple]:
    login, password, full_name = ACCOUNT
    # Соль выводится из логина, чтобы и эта строка повторялась при перезапуске.
    salt = hashlib.sha256(login.encode()).digest()[:16]
    return [(1, login, hash_password(password, salt), full_name)]


def reader_rows(rng: random.Random, size: Size, base: date) -> list[tuple]:
    rows = []
    for rid in range(1, size.readers + 1):
        name = person(rng)
        latin = name.split()[0].lower().translate(TRANSLIT)
        rows.append((
            rid,
            name,
            f"{latin}.{rid}@example.org",
            f"+7 9{rng.randint(10, 99)} {rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}",
            base - timedelta(days=rng.randint(HISTORY_DAYS, HISTORY_DAYS + 1500)),
        ))
    return rows


def book_rows(rng: random.Random, size: Size) -> list[tuple]:
    rows = []
    for bid in range(1, size.books + 1):
        title = f"{rng.choice(TITLE_ADJ)} {rng.choice(TITLE_NOUN)}{rng.choice(TITLE_TAIL)}"
        last = rng.choice(LAST_NAMES)
        author = f"{last} {rng.choice('АБВГДЕИКЛМНОПРС')}. {rng.choice('АБВГДЕИКЛМНОПРС')}."
        isbn = f"978-5-{rng.randint(100, 999)}-{rng.randint(10000, 99999)}-{rng.randint(0, 9)}"
        rows.append((bid, title, author, isbn, rng.randint(1950, 2026), rng.choice(GENRES)))
    return rows


def popularity(rng: random.Random, n: int) -> list[float]:
    """Вес книги: несколько книг читают много, большинство — изредка."""
    ranks = list(range(1, n + 1))
    rng.shuffle(ranks)
    return [1.0 / (rank + 10) ** 0.9 for rank in ranks]


def copy_rows(rng: random.Random, size: Size, weights: list[float], base: date) -> list[tuple]:
    # У каждой книги хотя бы один экземпляр, остальные — чаще у популярных.
    per_book = [1] * size.books
    soft = [w ** 0.5 for w in weights]
    for i in rng.choices(range(size.books), weights=soft, k=size.copies - size.books):
        per_book[i] += 1
    rows = []
    cid = 0
    for i, count in enumerate(per_book):
        for _ in range(count):
            cid += 1
            rows.append((
                cid,
                i + 1,
                f"ИНВ-{cid:06d}",
                f"{rng.choice('АБВГДЕЖЗ')}-{rng.randint(1, 40):02d}",
                base - timedelta(days=rng.randint(HISTORY_DAYS, HISTORY_DAYS + 3000)),
            ))
    return rows


def loans_per_copy(rng: random.Random, size: Size, copies: list[tuple], weights: list[float]) -> list[int]:
    # Вес экземпляра — вес его книги: популярную книгу берут чаще.
    copy_weights = [weights[c[1] - 1] for c in copies]
    counts = [0] * len(copies)
    left = size.loans
    while left:
        for i in rng.choices(range(len(copies)), weights=copy_weights, k=left):
            if counts[i] < MAX_LOANS_PER_COPY:
                counts[i] += 1
                left -= 1
        # Заполненные экземпляры из розыгрыша убираются.
        copy_weights = [0 if counts[i] >= MAX_LOANS_PER_COPY else w for i, w in enumerate(copy_weights)]
    return counts


def loan_rows(rng: random.Random, size: Size, copies: list[tuple], weights: list[float], base: date) -> list[tuple]:
    counts = loans_per_copy(rng, size, copies, weights)
    start = base - timedelta(days=HISTORY_DAYS)
    loan_days = settings.loan_days
    rows = []
    for copy, n in zip(copies, counts):
        if not n:
            continue
        slot = HISTORY_DAYS // n
        is_open = rng.random() < OPEN_SHARE
        prev_returned = start
        for k in range(n):
            reader_id = rng.randint(1, size.readers)
            if k == n - 1 and is_open:
                # Книга на руках: выдана недавно, у части выдач срок уже вышел.
                ago = rng.randint(0, 13) if rng.random() < 0.85 else rng.randint(15, 60)
                issued = max(base - timedelta(days=ago), prev_returned + timedelta(days=1))
                issued = min(issued, base)
                rows.append((copy[0], reader_id, issued, issued + timedelta(days=loan_days), None))
                break
            slot_start = start + timedelta(days=k * slot)
            issued = max(slot_start + timedelta(days=rng.randint(0, max(0, slot // 3))),
                         prev_returned + timedelta(days=1))
            # Большинство возвращает в срок, часть — с опозданием.
            if rng.random() < 0.8:
                held = rng.randint(2, loan_days)
            else:
                held = rng.randint(loan_days + 1, loan_days + 30)
            returned = min(issued + timedelta(days=held),
                           slot_start + timedelta(days=slot - 1),
                           base - timedelta(days=1))
            returned = max(returned, issued)
            rows.append((copy[0], reader_id, issued, issued + timedelta(days=loan_days), returned))
            prev_returned = returned
    # Идентификаторы выдач идут в хронологическом порядке, как в живой базе.
    rows.sort(key=lambda r: (r[2], r[0]))
    return [(i + 1, *r) for i, r in enumerate(rows)]


def generate(size_name: str) -> dict[str, list[tuple]]:
    size = SIZES[size_name]
    rng = random.Random(SEED)
    base = settings.seed_base_date
    weights = popularity(rng, size.books)
    copies = copy_rows(rng, size, weights, base)
    return {
        "accounts": account_rows(),
        "readers": reader_rows(rng, size, base),
        "books": book_rows(rng, size),
        "copies": copies,
        "loans": loan_rows(rng, size, copies, weights, base),
    }


COLUMNS = {
    "accounts": ["id", "login", "password_hash", "full_name"],
    "readers": ["id", "full_name", "email", "phone", "registered_on"],
    "books": ["id", "title", "author", "isbn", "published_year", "genre"],
    "copies": ["id", "book_id", "inventory_no", "shelf", "acquired_on"],
    "loans": ["id", "copy_id", "reader_id", "issued_on", "due_on", "returned_on"],
}


async def load(conn, size_name: str) -> None:
    data = generate(size_name)
    async with conn.transaction():
        await conn.execute("TRUNCATE loans, copies, books, readers, accounts RESTART IDENTITY")
        for table in ["accounts", "readers", "books", "copies", "loans"]:
            await conn.copy_records_to_table(table, records=data[table], columns=COLUMNS[table])
            # Последовательность продолжает нумерацию после загруженных строк.
            await conn.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT max(id) FROM {table}))"
            )
    await conn.execute("ANALYZE")
