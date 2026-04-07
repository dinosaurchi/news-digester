import { db } from './lib/db/index';
import { users } from './lib/db/schema';
import bcrypt from 'bcryptjs';
import { v4 as uuidv4 } from 'uuid';

async function seed() {
  console.log('Seeding database...');
  
  // Check if user 'chi' already exists
  const existingUser = await db.query.users.findFirst({
    where: (users, { eq }) => eq(users.username, 'chi'),
  });

  if (!existingUser) {
    const hashedPassword = await bcrypt.hash('123456', 10);
    await db.insert(users).values({
      id: 'user-1',
      username: 'chi',
      password: hashedPassword,
      displayName: 'Chi Admin',
      role: 'admin',
      createdAt: new Date(),
    });
    console.log('User "chi" created.');
  } else {
    console.log('User "chi" already exists.');
  }
  
  console.log('Seeding complete.');
}

seed().catch(console.error);
