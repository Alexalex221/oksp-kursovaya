-- Схема сервиса выдачи книг. Имя схемы подставляется из DB_SCHEMA.
-- Индексов, кроме первичных ключей, на первом этапе нет: ни уникальных,
-- ни по внешним ключам.

CREATE EXTENSION IF NOT EXISTS pg_stat_statements SCHEMA public;

CREATE SCHEMA IF NOT EXISTS :schema;
SET search_path TO :schema;

-- Учётные записи библиотекарей: под ними работает интерфейс и снимаются замеры.
CREATE TABLE IF NOT EXISTS accounts (
    id            serial PRIMARY KEY,
    login         text NOT NULL,
    password_hash text NOT NULL,
    full_name     text NOT NULL
);

CREATE TABLE IF NOT EXISTS readers (
    id            serial PRIMARY KEY,
    full_name     text NOT NULL,
    email         text NOT NULL,
    phone         text NOT NULL,
    registered_on date NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    id             serial PRIMARY KEY,
    title          text NOT NULL,
    author         text NOT NULL,
    isbn           text NOT NULL,
    published_year integer NOT NULL,
    genre          text NOT NULL
);

-- Экземпляр — конкретная физическая книга на полке.
CREATE TABLE IF NOT EXISTS copies (
    id           serial PRIMARY KEY,
    book_id      integer NOT NULL REFERENCES books (id),
    inventory_no text NOT NULL,
    shelf        text NOT NULL,
    acquired_on  date NOT NULL
);

-- Выдача экземпляра читателю. returned_on пуст, пока книга на руках.
CREATE TABLE IF NOT EXISTS loans (
    id          serial PRIMARY KEY,
    copy_id     integer NOT NULL REFERENCES copies (id),
    reader_id   integer NOT NULL REFERENCES readers (id),
    issued_on   date NOT NULL,
    due_on      date NOT NULL,
    returned_on date,
    CHECK (due_on >= issued_on),
    CHECK (returned_on IS NULL OR returned_on >= issued_on)
);
