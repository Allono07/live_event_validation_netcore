"""Validation Rule model."""
from datetime import datetime
from config.database import db


class ValidationRule(db.Model):
    """Validation rules for event payloads."""
    __tablename__ = 'validation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False)
    event_name = db.Column(db.String(200), nullable=False, index=True)
    field_name = db.Column(db.String(200), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)  # text, integer, float, date, boolean
    is_required = db.Column(db.Boolean, default=False)
    expected_pattern = db.Column(db.String(500), nullable=True)  # Pattern or range validation
    condition = db.Column(db.JSON, nullable=True)  # Conditional validation rules
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite index for faster lookups
    __table_args__ = (
        db.Index('idx_app_event', 'app_id', 'event_name'),
    )
    
    def __repr__(self):
        return f'<ValidationRule {self.event_name}.{self.field_name}>'
    
    def to_dict(self):
        """Convert validation rule to dictionary."""
        return {
            'id': self.id,
            'app_id': self.app_id,
            'event_name': self.event_name,
            'field_name': self.field_name,
            'data_type': self.data_type,
            'is_required': self.is_required,
            'expected_pattern': self.expected_pattern,
            'condition': self.condition,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
