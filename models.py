from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

def _n(v):           # helper ⟶ None → 0
    return v or 0

class DayRecord(db.Model):
    __tablename__ = 'day_records'
    id   = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)

    sugar       = db.Column(db.Float, default=0)
    essence     = db.Column(db.Float, default=0)
    tax         = db.Column(db.Float, default=0)
    water       = db.Column(db.Float, default=0)
    electricity = db.Column(db.Float, default=0)
    gas         = db.Column(db.Float, default=0)
    other       = db.Column(db.Float, default=0)      # ← НОВОЕ
    revenue     = db.Column(db.Float, default=0)

    def expenses_total(self):
        return (_n(self.sugar) + _n(self.essence) + _n(self.tax) +
                _n(self.water) + _n(self.electricity) + _n(self.gas) +
                _n(self.other))                      # ← + other

    def profit(self):
        return _n(self.revenue) - self.expenses_total()
