# app/models/payment.py
"""
Модели для платежей и продвижения
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, backref
from app.database import db


class PromotionService(db.Model):
    """Модель услуги продвижения"""
    __tablename__ = 'promotion_services'
    
    service_id = Column(Integer, primary_key=True)
    service_code = Column(String(50), unique=True, nullable=False)
    service_name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(10, 2), nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.currency_id'), nullable=False)
    duration_days = Column(Integer)
    features = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    currency = relationship('Currency', backref='promotion_services')
    
    def __repr__(self):
        return f'<PromotionService {self.service_name}>'


class EntityPromotion(db.Model):
    """Модель продвижения сущности"""
    __tablename__ = 'entity_promotions'
    
    promotion_id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('global_entities.entity_id'), nullable=False)
    service_id = Column(Integer, ForeignKey('promotion_services.service_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    payment_id = Column(Integer)
    status = Column(String(20), default='active')  # active, expired, cancelled
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service = relationship('PromotionService', backref='promotions')
    user = relationship('User', backref='promotions')
    
    def __repr__(self):
        return f'<EntityPromotion {self.promotion_id}>'
    
    @property
    def is_active(self):
        """Проверка активности продвижения"""
        return (
            self.status == 'active' and 
            self.end_date > datetime.utcnow()
        )


class PaymentTransaction(db.Model):
    """Модель транзакции платежа"""
    __tablename__ = 'payment_transactions'
    
    transaction_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # payment, refund, bonus, withdrawal
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.currency_id'), nullable=False)
    payment_method = Column(String(50))
    external_transaction_id = Column(String(255))
    status_id = Column(Integer, ForeignKey('statuses.status_id'), nullable=False)
    description = Column(Text)
    created_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)
    related_promotion_id = Column(Integer, ForeignKey('entity_promotions.promotion_id'))
    meta_data = Column(JSON, default=dict)
    error_message = Column(Text)
    
    # Relationships
    user = relationship('User', backref='payment_transactions')
    currency = relationship('Currency', backref='payment_transactions')
    status = relationship('Status', backref='payment_transactions')
    promotion = relationship('EntityPromotion', backref='payment_transactions')
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_id}: {self.amount} {self.currency.currency_code}>'
    
    @property
    def is_successful(self):
        """Проверка успешности транзакции"""
        return self.status.status_code == 'success' if self.status else False
    
    @property
    def is_pending(self):
        """Проверка ожидания обработки"""
        return self.status.status_code == 'pending' if self.status else False


class PaymentMethod(db.Model):
    """Модель способа оплаты"""
    __tablename__ = 'payment_methods'
    
    method_id = Column(Integer, primary_key=True)
    method_code = Column(String(50), unique=True, nullable=False)
    method_name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)  # kaspi, halyk, paybox, etc.
    is_active = Column(Boolean, default=True)
    configuration = Column(JSON, default=dict)
    sort_order = Column(Integer, default=0)
    
    def __repr__(self):
        return f'<PaymentMethod {self.method_name}>'


class UserWallet(db.Model):
    """Модель кошелька пользователя"""
    __tablename__ = 'user_wallets'
    
    wallet_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, unique=True)
    balance = Column(DECIMAL(15, 2), default=0)
    currency_id = Column(Integer, ForeignKey('currencies.currency_id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref=backref('wallet', uselist=False))
    currency = relationship('Currency', backref='user_wallets')
    
    def __repr__(self):
        return f'<UserWallet user_id={self.user_id}: {self.balance} {self.currency.currency_code}>'
    
    def add_funds(self, amount, description=""):
        """Пополнение кошелька"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += amount
        self.updated_date = datetime.utcnow()
        
        # Создаем транзакцию пополнения
        transaction = PaymentTransaction(
            user_id=self.user_id,
            transaction_type='deposit',
            amount=amount,
            currency_id=self.currency_id,
            description=description or f"Wallet deposit: {amount}",
            status_id=2  # success
        )
        db.session.add(transaction)
        return transaction
    
    def withdraw_funds(self, amount, description=""):
        """Списание с кошелька"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.balance < amount:
            raise ValueError("Insufficient funds")
        
        self.balance -= amount
        self.updated_date = datetime.utcnow()
        
        # Создаем транзакцию списания
        transaction = PaymentTransaction(
            user_id=self.user_id,
            transaction_type='withdrawal',
            amount=amount,
            currency_id=self.currency_id,
            description=description or f"Wallet withdrawal: {amount}",
            status_id=2  # success
        )
        db.session.add(transaction)
        return transaction
    
    def can_withdraw(self, amount):
        """Проверка возможности списания"""
        return self.balance >= amount and amount > 0


class Subscription(db.Model):
    """Модель подписки пользователя"""
    __tablename__ = 'subscriptions'
    
    subscription_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    service_id = Column(Integer, ForeignKey('promotion_services.service_id'), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    auto_renewal = Column(Boolean, default=False)
    status = Column(String(20), default='active')  # active, expired, cancelled
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref='subscriptions')
    service = relationship('PromotionService', backref='subscriptions')
    
    def __repr__(self):
        return f'<Subscription {self.subscription_id}: {self.service.service_name}>'
    
    @property
    def is_active(self):
        """Проверка активности подписки"""
        return (
            self.status == 'active' and 
            self.end_date > datetime.utcnow()
        )
    
    @property
    def days_remaining(self):
        """Количество дней до окончания"""
        if self.end_date > datetime.utcnow():
            return (self.end_date - datetime.utcnow()).days
        return 0


class PaymentNotification(db.Model):
    """Модель уведомлений о платежах"""
    __tablename__ = 'payment_notifications'
    
    notification_id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('payment_transactions.transaction_id'), nullable=False)
    provider = Column(String(50), nullable=False)
    webhook_data = Column(JSON)
    processed = Column(Boolean, default=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)
    error_message = Column(Text)
    
    # Relationships
    transaction = relationship('PaymentTransaction', backref='notifications')
    
    def __repr__(self):
        return f'<PaymentNotification {self.notification_id}: {self.provider}>'