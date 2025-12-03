import express from 'express';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { findByEmail, getUser } from './usersStore.js';
import { AuthPayload } from './types.js';

const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';
const TOKEN_EXPIRES = '8h';

router.post('/login', async (req, res) => {
  const { email, password } = req.body || {};
  if (!email || !password) {
    return res.status(400).json({ error: 'Email та пароль обов\'язкові' });
  }
  const user = findByEmail(email);
  if (!user) return res.status(401).json({ error: 'Невірні дані' });
  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) return res.status(401).json({ error: 'Невірні дані' });
  const payload: AuthPayload = { userId: user.id, role: user.role };
  const token = jwt.sign(payload, JWT_SECRET, { expiresIn: TOKEN_EXPIRES });
  return res.json({ token, user: { id: user.id, email: user.email, role: user.role, name: user.name } });
});

router.get('/me', (req, res) => {
  const auth = req.headers.authorization;
  if (!auth?.startsWith('Bearer ')) return res.status(401).json({ error: 'Немає токена' });
  try {
    const token = auth.substring(7);
    const decoded = jwt.verify(token, JWT_SECRET) as AuthPayload;
    const user = getUser(decoded.userId);
    if (!user) return res.status(404).json({ error: 'Користувача не знайдено' });
    return res.json({ user: { id: user.id, email: user.email, role: user.role, name: user.name } });
  } catch (e) {
    return res.status(401).json({ error: 'Невалідний токен' });
  }
});

export default router;
