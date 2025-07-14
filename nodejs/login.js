const { Pool } = require('pg');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function login(useremail, password) {
  const useremailLowerCase = (useremail || '').toLowerCase();

  const { rows } = await pool.query(
    'SELECT * FROM usuario WHERE LOWER(useremail) = $1',
    [useremailLowerCase]
  );

  if (rows.length === 0) {
    throw new Error('Correo electrónico incorrecto');
  }

  const user = rows[0];

  const match = await bcrypt.compare(password, user.password);
  if (!match) {
    throw new Error('Contraseña incorrecta');
  }

  const token = jwt.sign(
    { id_usuario: user.id_usuario, useremail: user.useremail },
    process.env.SECRETKEY,
    { expiresIn: '1d' }
  );

  return { serviceToken: token, user };
}

module.exports = login;
