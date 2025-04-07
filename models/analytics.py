from models import db, datetime
from datetime import timezone

class PageVisit(db.Model):
    __tablename__ = 'page_visit'  
    
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    visit_time = db.Column(db.DateTime, default=datetime.now(timezone.utc))