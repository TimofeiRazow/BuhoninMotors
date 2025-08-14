# app/blueprints/payments/services.py
"""
Сервисы для работы с платежами и продвижением
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from app.models.payment import PaymentTransaction, PromotionService as PromotionServiceModel, EntityPromotion
from app.models.listing import Listing
from app.models.user import User
from app.blueprints.payments.providers import PaymentProviderFactory
from app.utils.pagination import paginate_query as paginate


class PaymentService:
    """Сервис для работы с платежами"""
    
    @staticmethod
    def get_user_transactions(db, user_id, page=1, per_page=20, transaction_type=None):
        """Получение транзакций пользователя"""
        query = db.query(PaymentTransaction).filter(
            PaymentTransaction.user_id == user_id
        )
        
        if transaction_type:
            query = query.filter(PaymentTransaction.transaction_type == transaction_type)
        
        query = query.order_by(PaymentTransaction.created_date.desc())
        
        return paginate(query, page, per_page)
    
    @staticmethod
    def create_payment(db, user_id, data):
        """Создание платежа"""
        transaction = PaymentTransaction(
            user_id=user_id,
            transaction_type='payment',
            amount=data['amount'],
            currency_id=data['currency_id'],
            description=data.get('description', ''),
            related_promotion_id=data.get('promotion_id'),
            status_id=1  # pending
        )
        
        db.add(transaction)
        db.commit()
        
        return transaction
    
    @staticmethod
    def process_payment(db, transaction_id, user_id, payment_method, payment_data):
        """Обработка платежа через платежную систему"""
        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.transaction_id == transaction_id,
            PaymentTransaction.user_id == user_id
        ).first()
        
        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}
        
        if transaction.status_id != 1:  # not pending
            return {'success': False, 'error': 'Transaction already processed'}
        
        try:
            # Получаем провайдер платежей
            provider = PaymentProviderFactory.get_provider(payment_method)
            
            # Обрабатываем платеж
            result = provider.process_payment(
                amount=float(transaction.amount),
                currency='KZT',
                description=transaction.description,
                payment_data=payment_data
            )
            
            if result['success']:
                transaction.status_id = 2  # success
                transaction.processed_date = datetime.utcnow()
                transaction.external_transaction_id = result.get('transaction_id')
                transaction.payment_method = payment_method
                
                # Активируем связанное продвижение
                if transaction.related_promotion_id:
                    promotion = db.query(EntityPromotion).filter_by(
                        promotion_id=transaction.related_promotion_id
                    ).first()
                    if promotion:
                        promotion.status = 'active'
                
                db.commit()
                
                return {
                    'success': True,
                    'transaction_id': result.get('transaction_id'),
                    'redirect_url': result.get('redirect_url')
                }
            else:
                transaction.status_id = 3  # failed
                transaction.error_message = result.get('error', 'Payment failed')
                db.commit()
                
                return {'success': False, 'error': result.get('error', 'Payment failed')}
                
        except Exception as e:
            transaction.status_id = 3  # failed
            transaction.error_message = str(e)
            db.commit()
            
            return {'success': False, 'error': 'Payment processing error'}
    
    @staticmethod
    def handle_webhook(db, provider, webhook_data):
        """Обработка webhook от платежной системы"""
        try:
            payment_provider = PaymentProviderFactory.get_provider(provider)
            result = payment_provider.handle_webhook(webhook_data)
            
            if result and 'transaction_id' in result:
                transaction = db.query(PaymentTransaction).filter_by(
                    external_transaction_id=result['transaction_id']
                ).first()
                
                if transaction:
                    if result['status'] == 'success':
                        transaction.status_id = 2  # success
                        transaction.processed_date = datetime.utcnow()
                        
                        # Активируем продвижение
                        if transaction.related_promotion_id:
                            promotion = db.query(EntityPromotion).filter_by(
                                promotion_id=transaction.related_promotion_id
                            ).first()
                            if promotion:
                                promotion.status = 'active'
                    
                    elif result['status'] == 'failed':
                        transaction.status_id = 3  # failed
                        transaction.error_message = result.get('error', 'Payment failed')
                    
                    db.commit()
                    return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error handling webhook: {e}")
            return False
    
    @staticmethod
    def create_refund(db, transaction_id, user_id, reason):
        """Создание возврата средств"""
        original_transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.transaction_id == transaction_id,
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.transaction_type == 'payment',
            PaymentTransaction.status_id == 2  # success
        ).first()
        
        if not original_transaction:
            return None
        
        # Проверяем, можно ли сделать возврат (например, в течение 30 дней)
        if (datetime.utcnow() - original_transaction.processed_date).days > 30:
            return None
        
        refund_transaction = PaymentTransaction(
            user_id=user_id,
            transaction_type='refund',
            amount=original_transaction.amount,
            currency_id=original_transaction.currency_id,
            description=f'Refund for transaction #{transaction_id}: {reason}',
            status_id=1,  # pending
            meta_data={'original_transaction_id': transaction_id, 'reason': reason}
        )
        
        db.add(refund_transaction)
        db.commit()
        
        return refund_transaction
    
    @staticmethod
    def get_user_balance(db, user_id):
        """Получение баланса пользователя"""
        # Сумма успешных платежей
        payments = db.query(func.sum(PaymentTransaction.amount)).filter(
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.transaction_type == 'payment',
            PaymentTransaction.status_id == 2
        ).scalar() or Decimal('0')
        
        # Сумма возвратов
        refunds = db.query(func.sum(PaymentTransaction.amount)).filter(
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.transaction_type == 'refund',
            PaymentTransaction.status_id == 2
        ).scalar() or Decimal('0')
        
        # Сумма списаний за услуги
        withdrawals = db.query(func.sum(PaymentTransaction.amount)).filter(
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.transaction_type == 'withdrawal',
            PaymentTransaction.status_id == 2
        ).scalar() or Decimal('0')
        
        return float(payments + refunds - withdrawals)
    
    @staticmethod
    def get_user_payment_stats(db, user_id):
        """Получение статистики платежей пользователя"""
        # Общая статистика
        total_payments = db.query(
            func.count(PaymentTransaction.transaction_id),
            func.sum(PaymentTransaction.amount)
        ).filter(
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.transaction_type == 'payment',
            PaymentTransaction.status_id == 2
        ).first()
        
        # Статистика по месяцам
        monthly_stats = db.query(
            func.date_trunc('month', PaymentTransaction.processed_date).label('month'),
            func.count(PaymentTransaction.transaction_id).label('count'),
            func.sum(PaymentTransaction.amount).label('amount')
        ).filter(
            PaymentTransaction.user_id == user_id,
            PaymentTransaction.transaction_type == 'payment',
            PaymentTransaction.status_id == 2,
            PaymentTransaction.processed_date >= datetime.utcnow() - timedelta(days=365)
        ).group_by(
            func.date_trunc('month', PaymentTransaction.processed_date)
        ).order_by('month').all()
        
        return {
            'total_payments': total_payments[0] or 0,
            'total_amount': float(total_payments[1] or 0),
            'monthly_stats': [
                {
                    'month': stat.month.isoformat(),
                    'count': stat.count,
                    'amount': float(stat.amount)
                }
                for stat in monthly_stats
            ]
        }


class PromotionService:
    """Сервис для работы с продвижением объявлений"""
    
    @staticmethod
    def get_promotion_services(db):
        """Получение доступных услуг продвижения"""
        return db.query(PromotionServiceModel).filter(
            PromotionServiceModel.is_active == True
        ).order_by(PromotionServiceModel.sort_order).all()
    
    @staticmethod
    def user_owns_listing(db, user_id, listing_id):
        """Проверка принадлежности объявления пользователю"""
        listing = db.query(Listing).filter(
            Listing.listing_id == listing_id,
            Listing.user_id == user_id
        ).first()
        return listing is not None
    
    @staticmethod
    def create_promotion(db, user_id, data):
        """Создание продвижения объявления"""
        service = db.query(PromotionServiceModel).filter_by(
            service_id=data['service_id']
        ).first()
        
        if not service:
            raise ValueError('Service not found')
        
        listing = db.query(Listing).filter_by(
            listing_id=data['listing_id']
        ).first()
        
        if not listing:
            raise ValueError('Listing not found')
        
        # Создаем продвижение
        end_date = datetime.utcnow() + timedelta(days=service.duration_days)
        
        promotion = EntityPromotion(
            entity_id=listing.entity_id,
            service_id=service.service_id,
            user_id=user_id,
            end_date=end_date,
            status='pending'
        )
        
        db.add(promotion)
        db.flush()  # Получаем ID продвижения
        
        # Создаем платеж
        payment = PaymentTransaction(
            user_id=user_id,
            transaction_type='payment',
            amount=service.price,
            currency_id=service.currency_id,
            description=f'Promotion service: {service.service_name} for listing #{listing.listing_id}',
            related_promotion_id=promotion.promotion_id,
            status_id=1  # pending
        )
        
        db.add(payment)
        db.commit()
        
        return {
            'promotion_id': promotion.promotion_id,
            'payment_id': payment.transaction_id,
            'amount': float(service.price),
            'service_name': service.service_name,
            'duration_days': service.duration_days,
            'end_date': end_date.isoformat()
        }
    
    @staticmethod
    def get_user_promotions(db, user_id, page=1, per_page=20, status=None):
        """Получение продвижений пользователя"""
        query = db.query(EntityPromotion).options(
            joinedload(EntityPromotion.service)
        ).filter(
            EntityPromotion.user_id == user_id
        )
        
        if status:
            query = query.filter(EntityPromotion.status == status)
        
        query = query.order_by(EntityPromotion.created_date.desc())
        
        return paginate(query, page, per_page)
    
    @staticmethod
    def get_active_promotions(db, entity_id):
        """Получение активных продвижений для сущности"""
        return db.query(EntityPromotion).options(
            joinedload(EntityPromotion.service)
        ).filter(
            EntityPromotion.entity_id == entity_id,
            EntityPromotion.status == 'active',
            EntityPromotion.end_date > datetime.utcnow()
        ).all()
    
    @staticmethod
    def expire_promotions(db):
        """Завершение истекших продвижений"""
        expired_count = db.query(EntityPromotion).filter(
            EntityPromotion.status == 'active',
            EntityPromotion.end_date <= datetime.utcnow()
        ).update({'status': 'expired'})
        
        db.commit()
        return expired_count


