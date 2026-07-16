from db.models import db, Order

def init_db():
    db.create_all()
