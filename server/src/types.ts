export type Role = 'admin' | 'manager' | 'viewer';

export interface User {
  id: string;
  email: string;
  passwordHash: string; // bcrypt hash
  role: Role;
  name: string;
}

export interface AuthPayload {
  userId: string;
  role: Role;
}
