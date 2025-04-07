from models import db, datetime

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))  # Added location field
    start_date = db.Column(db.Date)  # Added start date field
    end_date = db.Column(db.Date)  # Added end date field
    image = db.Column(db.String(255))
    client = db.Column(db.String(100))
    category = db.Column(db.String(100))
    technologies = db.Column(db.Text)  # Store as comma-separated values
    challenges = db.Column(db.Text)
    solution = db.Column(db.Text)
    repository = db.Column(db.String(255))

    # progress field removed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_technologies(self):
        if self.technologies:
            return [tech.strip() for tech in self.technologies.split(',')]
        return []
    