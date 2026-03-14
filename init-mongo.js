db.getSiblingDB(process.env.MONGO_DB).createUser({
  user: process.env.MONGO_DB_USERNAME,
  pwd: process.env.MONGO_DB_PASSWORD,
  roles: [{ role: "readWrite", db: process.env.MONGO_DB }],
});