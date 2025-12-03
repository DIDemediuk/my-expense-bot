import { User, Role } from './types.js';
import bcrypt from 'bcryptjs';

// Temporary in-memory user store. Replace with DB later.
const users: User[] = [];

function seedInitial() {
  if (users.length) return;
  const seed = [
    { email: 'admin@example.com', role: 'admin' as Role, name: 'Адмін' },
    { email: 'manager@example.com', role: 'manager' as Role, name: 'Менеджер' },
    { email: 'viewer@example.com', role: 'viewer' as Role, name: 'Переглядач' }
  ];
  seed.forEach(s => {
    const passwordHash = bcrypt.hashSync('password123', 10);
    users.push({ id: crypto.randomUUID(), email: s.email, role: s.role, name: s.name, passwordHash });
  });
}

seedInitial();

export function findByEmail(email: string) {
  return users.find(u => u.email === email);
}

export function getUser(id: string) {
  return users.find(u => u.id === id);
}
