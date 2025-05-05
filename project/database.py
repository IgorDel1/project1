# database.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float
from databases import Database  # Добавьте эту строку!

DATABASE_URL = "sqlite+aiosqlite:///./shop.db"

database = Database(DATABASE_URL)
metadata = MetaData()

products = Table(
    "product",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String, index=True),
    Column("price_kg", Float),
    Column("weight", Float),
    Column("category", String),
)

bank = Table(
    "bank",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("money", Float),
)

engine = create_engine(str(DATABASE_URL).replace("aiosqlite", "pysqlite"))

metadata.create_all(engine)