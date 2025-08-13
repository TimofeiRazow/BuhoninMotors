# app/blueprints/payments/schemas.py
"""
Marshmallow схемы для платежей
"""

from marshmallow import Schema, fields, validate
from marshmallow.validate import Length, Range, OneOf
from decimal import Decimal


class PaymentTransactionSchema(Schema):
    """Схема для транзакции платежа"""
    transaction_id = fields.Int(dump_only=True)
    transaction_type = fields.Str()
    amount = fields.Decimal(places=2)
    currency_id = fields.Int()
    payment_method = fields.Str(allow_none=True)
    external_transaction_id = fields.Str(allow_none=True)
    status_id = fields.Int()
    description = fields.Str(allow_none=True)
    created_date = fields.DateTime()
    processed_date = fields.DateTime(allow_none=True)
    error_message = fields.Str(allow_none=True)
    metadata = fields.Raw()


class PromotionServiceSchema(Schema):
    """Схема для услуги продвижения"""
    service_id = fields.Int()
    service_code = fields.Str()
    service_name = fields.Str()
    description = fields.Str(allow_none=True)
    price = fields.Decimal(places=2)
    currency_id = fields.Int()
    duration_days = fields.Int(allow_none=True)
    features = fields.Raw()
    is_active = fields.Bool()
    sort_order = fields.Int()


class EntityPromotionSchema(Schema):
    """Схема для продвижения сущности"""
    promotion_id = fields.Int()
    entity_id = fields.Int()
    service_id = fields.Int()
    user_id = fields.Int()
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    status = fields.Str()
    created_date = fields.DateTime()
    
    # Вложенные объекты
    service = fields.Nested(PromotionServiceSchema, dump_only=True)


class CreatePaymentSchema(Schema):
    """Схема для создания платежа"""
    amount = fields.Decimal(required=True, validate=Range(min=Decimal('0.01')))
    currency_id = fields.Int(required=True)
    description = fields.Str(validate=Length(max=500))
    promotion_id = fields.Int(allow_none=True)


class PromoteListingSchema(Schema):
    """Схема для продвижения объявления"""
    listing_id = fields.Int(required=True)
    service_id = fields.Int(required=True)


# app/blueprints/payments/providers.py
"""
Провайдеры платежных систем
"""

import hashlib
import hmac
import json
import requests
from abc import ABC, abstractmethod
from flask import current_app


class PaymentProviderInterface(ABC):
    """Интерфейс для платежных провайдеров"""
    
    @abstractmethod
    def process_payment(self, amount, currency, description, payment_data):
        """Обработка платежа"""
        pass
    
    @abstractmethod
    def handle_webhook(self, webhook_data):
        """Обработка webhook"""
        pass


class KaspiPayProvider(PaymentProviderInterface):
    """Провайдер для Kaspi Pay"""
    
    def __init__(self):
        self.merchant_id = current_app.config.get('KASPI_MERCHANT_ID')
        self.secret_key = current_app.config.get('KASPI_SECRET_KEY')
        self.api_url = current_app.config.get('KASPI_API_URL', 'https://api.kaspi.kz')
    
    def process_payment(self, amount, currency, description, payment_data):
        """Обработка платежа через Kaspi Pay"""
        try:
            payment_request = {
                'merchant_id': self.merchant_id,
                'amount': amount,
                'currency': currency,
                'description': description,
                'order_id': payment_data.get('order_id'),
                'return_url': payment_data.get('return_url'),
                'webhook_url': payment_data.get('webhook_url')
            }
            
            # Генерируем подпись
            payment_request['signature'] = self._generate_signature(payment_request)
            
            response = requests.post(
                f'{self.api_url}/payments/create',
                json=payment_request,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'transaction_id': result.get('transaction_id'),
                    'redirect_url': result.get('payment_url')
                }
            else:
                return {
                    'success': False,
                    'error': f'Kaspi Pay error: {response.status_code}'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def handle_webhook(self, webhook_data):
        """Обработка webhook от Kaspi Pay"""
        try:
            # Проверяем подпись
            if not self._verify_webhook_signature(webhook_data):
                return None
            
            return {
                'transaction_id': webhook_data.get('transaction_id'),
                'status': 'success' if webhook_data.get('status') == 'SUCCESS' else 'failed',
                'error': webhook_data.get('error_message')
            }
            
        except Exception as e:
            current_app.logger.error(f"Error handling Kaspi webhook: {e}")
            return None
    
    def _generate_signature(self, data):
        """Генерация подписи для запроса"""
        # Сортируем параметры и создаем строку для подписи
        sorted_params = sorted(data.items())
        sign_string = '&'.join([f'{k}={v}' for k, v in sorted_params if k != 'signature'])
        
        return hmac.new(
            self.secret_key.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_webhook_signature(self, webhook_data):
        """Проверка подписи webhook"""
        received_signature = webhook_data.get('signature')
        if not received_signature:
            return False
        
        expected_signature = self._generate_signature(webhook_data)
        return hmac.compare_digest(received_signature, expected_signature)


class HalykPayProvider(PaymentProviderInterface):
    """Провайдер для Halyk Pay"""
    
    def __init__(self):
        self.merchant_id = current_app.config.get('HALYK_MERCHANT_ID')
        self.secret_key = current_app.config.get('HALYK_SECRET_KEY')
        self.api_url = current_app.config.get('HALYK_API_URL', 'https://pay.halykbank.kz')
    
    def process_payment(self, amount, currency, description, payment_data):
        """Обработка платежа через Halyk Pay"""
        try:
            payment_request = {
                'pg_merchant_id': self.merchant_id,
                'pg_order_id': payment_data.get('order_id'),
                'pg_amount': amount,
                'pg_currency': currency,
                'pg_description': description,
                'pg_result_url': payment_data.get('return_url'),
                'pg_request_method': 'POST'
            }
            
            # Генерируем подпись
            payment_request['pg_sig'] = self._generate_halyk_signature(payment_request)
            
            response = requests.post(
                f'{self.api_url}/webapi/payment',
                data=payment_request,
                timeout=30
            )
            
            if response.status_code == 200:
                # Halyk возвращает HTML форму для редиректа
                return {
                    'success': True,
                    'transaction_id': payment_data.get('order_id'),
                    'redirect_html': response.text
                }
            else:
                return {
                    'success': False,
                    'error': f'Halyk Pay error: {response.status_code}'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def handle_webhook(self, webhook_data):
        """Обработка webhook от Halyk Pay"""
        try:
            # Проверяем подпись
            if not self._verify_halyk_signature(webhook_data):
                return None
            
            status = 'success' if webhook_data.get('pg_result') == '1' else 'failed'
            
            return {
                'transaction_id': webhook_data.get('pg_order_id'),
                'status': status,
                'error': webhook_data.get('pg_failure_description')
            }
            
        except Exception as e:
            current_app.logger.error(f"Error handling Halyk webhook: {e}")
            return None
    
    def _generate_halyk_signature(self, data):
        """Генерация подписи для Halyk Pay"""
        # Убираем подпись из данных
        sign_data = {k: v for k, v in data.items() if k != 'pg_sig'}
        
        # Сортируем и создаем строку для подписи
        sorted_params = sorted(sign_data.items())
        sign_string = ';'.join([str(v) for k, v in sorted_params])
        sign_string += ';' + self.secret_key
        
        return hashlib.md5(sign_string.encode()).hexdigest()
    
    def _verify_halyk_signature(self, webhook_data):
        """Проверка подписи webhook от Halyk"""
        received_signature = webhook_data.get('pg_sig')
        if not received_signature:
            return False
        
        expected_signature = self._generate_halyk_signature(webhook_data)
        return received_signature == expected_signature


class PaymentProviderFactory:
    """Фабрика для создания провайдеров платежей"""
    
    _providers = {
        'kaspi': KaspiPayProvider,
        'halyk': HalykPayProvider,
        'card': KaspiPayProvider,  # По умолчанию используем Kaspi для карт
    }
    
    @classmethod
    def get_provider(cls, provider_name):
        """Получение провайдера по имени"""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown payment provider: {provider_name}")
        
        return provider_class()
    
    @classmethod
    def register_provider(cls, name, provider_class):
        """Регистрация нового провайдера"""
        cls._providers[name] = provider_class