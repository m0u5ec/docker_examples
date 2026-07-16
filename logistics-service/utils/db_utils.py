from db.models import db, Delivery

def init_db():
    db.create_all()
