"""Minimal Flask test server for pamfilico-flask-collection integration tests."""

import os
from datetime import date, datetime

from flask import Flask, request
from marshmallow import Schema, fields
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from pamfilico_flask_core import init_errors, standard_response
from pamfilico_flask_collection import collection, apply_filters

Base = declarative_base()


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    status = Column(String(50))
    category = Column(String(50))
    price = Column(Float)
    quantity = Column(Integer)
    is_active = Column(Boolean)
    created_date = Column(Date)
    created_at = Column(DateTime)


class ItemSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    status = fields.String()
    category = fields.String()
    price = fields.Float()
    quantity = fields.Integer()
    is_active = fields.Boolean()
    created_date = fields.Date()
    created_at = fields.DateTime()


DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://test:test@localhost:5497/testdb"
)

engine = create_engine(DATABASE_URL)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

app = Flask(__name__)
init_errors(app)

SEED_ITEMS = [
    Item(
        id=1, name="Gaming Laptop", status="active", category="electronics",
        price=1200.0, quantity=5, is_active=True,
        created_date=date(2025, 1, 15), created_at=datetime(2025, 1, 15, 10, 30),
    ),
    Item(
        id=2, name="Office Laptop", status="active", category="electronics",
        price=800.0, quantity=10, is_active=True,
        created_date=date(2025, 2, 20), created_at=datetime(2025, 2, 20, 14, 0),
    ),
    Item(
        id=3, name="Wireless Mouse", status="active", category="accessories",
        price=25.0, quantity=100, is_active=True,
        created_date=date(2025, 3, 1), created_at=datetime(2025, 3, 1, 9, 0),
    ),
    Item(
        id=4, name="Mechanical Keyboard", status="pending", category="accessories",
        price=150.0, quantity=30, is_active=True,
        created_date=date(2025, 3, 10), created_at=datetime(2025, 3, 10, 16, 45),
    ),
    Item(
        id=5, name="Broken Monitor", status="deleted", category="electronics",
        price=300.0, quantity=0, is_active=False,
        created_date=date(2024, 12, 1), created_at=datetime(2024, 12, 1, 8, 0),
    ),
]


def seed_db():
    Base.metadata.create_all(engine)
    session = Session()
    if session.query(Item).count() == 0:
        session.add_all(SEED_ITEMS)
        session.commit()
    session.close()


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/api/items")
@collection(
    ItemSchema,
    searchable_fields=["name", "status", "category"],
    sortable_fields=["name", "price", "quantity", "created_at"],
)
def list_items():
    return Session().query(Item)


@app.route("/api/items-filtered")
def list_items_filtered():
    session = Session()
    query = session.query(Item)
    query, active_filters = apply_filters(
        query, Item, request.args,
        allowed_fields={"status", "category", "price", "quantity", "is_active", "created_date"},
    )
    results = query.all()
    schema = ItemSchema(many=True)
    data = schema.dump(results)
    session.close()
    return standard_response(data=data, filtering=active_filters)


seed_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
