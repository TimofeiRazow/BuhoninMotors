# app/models/review.py
"""
Модель отзывов пользователей
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.extensions import db


class UserReview(BaseModel):
    """Модель отзывов о пользователях"""
    __tablename__ = 'user_reviews'
    
    review_id = Column(Integer, primary_key=True)
    reviewer_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    reviewed_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    rating = Column(Integer, nullable=False)  # от 1 до 5
    comment = Column(Text)
    is_public = Column(Boolean, default=True)
    listing_id = Column(Integer, ForeignKey('listings.listing_id'), nullable=True)  # связь с объявлением
    
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        db.Index('idx_user_reviews_reviewed_user', 'reviewed_user_id'),
        db.Index('idx_user_reviews_reviewer', 'reviewer_id'),
    )
    
    # Отношения
    reviewer = relationship('User', foreign_keys=[reviewer_id], backref='given_reviews')
    reviewed_user = relationship('User', foreign_keys=[reviewed_user_id], backref='received_reviews')
    # listing = relationship('Listing', backref='reviews')  # раскомментировать когда создадим модель Listing
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'review_id': self.review_id,
            'reviewer_id': self.reviewer_id,
            'reviewed_user_id': self.reviewed_user_id,
            'rating': self.rating,
            'comment': self.comment,
            'is_public': self.is_public,
            'listing_id': self.listing_id,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'reviewer_name': f"{self.reviewer.first_name} {self.reviewer.last_name}".strip() if self.reviewer else None
        }
    
    @classmethod
    def get_user_rating(cls, user_id):
        """Получение среднего рейтинга пользователя"""
        from sqlalchemy import func
        result = db.session.query(
            func.avg(cls.rating).label('avg_rating'),
            func.count(cls.review_id).label('reviews_count')
        ).filter(
            cls.reviewed_user_id == user_id,
            cls.is_public == True,
            cls.is_active == True
        ).first()
        
        return {
            'average_rating': float(result.avg_rating or 0),
            'reviews_count': int(result.reviews_count or 0)
        }
    
    def __repr__(self):
        return f'<UserReview {self.review_id}: {self.rating} stars>'