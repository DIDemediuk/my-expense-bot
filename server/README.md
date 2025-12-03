# CampManager Server (Початкова версія)

## Що реалізовано
- Express + TypeScript скелет
- Тимчасове зберігання користувачів у пам'яті (3 користувачі: admin, manager, viewer)
- Авторизація: /api/auth/login (email + пароль) -> JWT
- Перевірка токена: /api/auth/me
- Приклад захищеного роуту: /api/secure/example

## Логін (тимчасові дані)
| Email | Пароль | Роль |
|-------|--------|------|
| admin@example.com | password123 | admin |
| manager@example.com | password123 | manager |
| viewer@example.com | password123 | viewer |

## Запуск (після встановлення залежностей)
```
npm install
npm run dev
```
Сервер за замовчуванням на порті 4000.

## Наступні кроки
1. Додати постійну БД (PostgreSQL + Prisma)
2. Хешування паролів вже є (bcryptjs), але потрібне створення реєстрації
3. Розширити модель ролей (можливо: finance, analytics окремо)
4. Винести permissions у окремий модуль
5. Підключити фронтенд (fetch /api/auth/login) і зберігати token у localStorage
6. Додати refresh токени (довший життєвий цикл)
7. Лог аудиту змін (operations, refunds)

## Тимчасові обмеження
- Користувачі губляться після перезапуску (in-memory)
- Немає rate limiting / захисту від brute-force
- JWT секрет захардкожений (потрібен .env)

## .env приклад (створити пізніше)
```
PORT=4000
JWT_SECRET=super-long-secret-string
```
