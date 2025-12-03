import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import authRouter from './auth.js';
import jwt from 'jsonwebtoken';
import { AuthPayload } from './types.js';
import { getUser } from './usersStore.js';

const app = express();
app.use(cors());
app.use(express.json());

// Middleware для перевірки токена (опціонально на роуті)
function requireAuth(req: Request, res: Response, next: NextFunction) {
  const auth = req.headers.authorization;
  if (!auth?.startsWith('Bearer ')) return res.status(401).json({ error: 'Токен відсутній' });
  try {
    const token = auth.substring(7);
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'dev-secret-change-me') as AuthPayload;
    const user = getUser(decoded.userId);
    if (!user) return res.status(404).json({ error: 'Користувача не знайдено' });
    // @ts-expect-error додамо на req
    req.currentUser = user;
    next();
  } catch (e) {
    return res.status(401).json({ error: 'Невалідний або прострочений токен' });
  }
}

app.get('/api/ping', (_req: Request, res: Response) => {
  res.json({ ok: true, time: new Date().toISOString() });
});

app.use('/api/auth', authRouter);

// Приклад захищеного роуту
app.get('/api/secure/example', requireAuth, (req: Request, res: Response) => {
  // @ts-expect-error
  const user = req.currentUser;
  res.json({ message: 'Секретні дані', user: { id: user.id, role: user.role } });
});

const PORT = Number(process.env.PORT) || 4000;
app.listen(PORT, () => {
  console.log(`✅ Auth/roles API стартувало на порті ${PORT}`);
});
