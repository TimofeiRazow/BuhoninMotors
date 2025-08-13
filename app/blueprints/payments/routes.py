# app/blueprints/payments/routes.py
"""
Роуты для платежей и продвижения объявлений
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.blueprints.payments import payments_bp
from app.blueprints.payments.services import PaymentService, PromotionService
from app.blueprints.payments.schemas import (
    PaymentTransactionSchema, PromotionServiceSchema, EntityPromotionSchema,
    CreatePaymentSchema, PromoteListingSchema
)
from app.utils.decorators import validate_json
from app.database import get_db


@payments_bp.route('/services', methods=['GET'])
def get_promotion_services():
    """Получение доступных услуг продвижения"""
    try:
        db = get_db()
        
        services = PromotionService.get_promotion_services(db)
        schema = PromotionServiceSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': schema.dump(services)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting promotion services: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/promote-listing', methods=['POST'])
@jwt_required()
@validate_json
def promote_listing():
    """Продвижение объявления"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        schema = PromoteListingSchema()
        data = schema.load(request.json)
        
        # Проверяем права на объявление
        if not PromotionService.user_owns_listing(db, user_id, data['listing_id']):
            return jsonify({'error': 'Access denied'}), 403
        
        # Создаем платеж и продвижение
        result = PromotionService.create_promotion(db, user_id, data)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Listing promotion created successfully'
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error promoting listing: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/my-promotions', methods=['GET'])
@jwt_required()
def get_my_promotions():
    """Получение активных продвижений пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        promotions = PromotionService.get_user_promotions(
            db, user_id, page, per_page, status
        )
        
        schema = EntityPromotionSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': {
                'promotions': schema.dump(promotions['items']),
                'pagination': {
                    'page': promotions['page'],
                    'per_page': promotions['per_page'],
                    'total': promotions['total'],
                    'pages': promotions['pages']
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user promotions: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_payment_history():
    """Получение истории платежей пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        transaction_type = request.args.get('type')
        
        transactions = PaymentService.get_user_transactions(
            db, user_id, page, per_page, transaction_type
        )
        
        schema = PaymentTransactionSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': {
                'transactions': schema.dump(transactions['items']),
                'pagination': {
                    'page': transactions['page'],
                    'per_page': transactions['per_page'],
                    'total': transactions['total'],
                    'pages': transactions['pages']
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting payment history: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/create-payment', methods=['POST'])
@jwt_required()
@validate_json
def create_payment():
    """Создание платежа"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        schema = CreatePaymentSchema()
        data = schema.load(request.json)
        
        payment = PaymentService.create_payment(db, user_id, data)
        
        response_schema = PaymentTransactionSchema()
        return jsonify({
            'success': True,
            'data': response_schema.dump(payment),
            'message': 'Payment created successfully'
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating payment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/process-payment/<int:transaction_id>', methods=['POST'])
@jwt_required()
@validate_json
def process_payment(transaction_id):
    """Обработка платежа через платежную систему"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        payment_method = request.json.get('payment_method', 'card')
        payment_data = request.json.get('payment_data', {})
        
        result = PaymentService.process_payment(
            db, transaction_id, user_id, payment_method, payment_data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Payment processed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error processing payment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/webhook/<provider>', methods=['POST'])
def payment_webhook(provider):
    """Webhook для обработки уведомлений от платежных систем"""
    try:
        db = get_db()
        
        webhook_data = request.get_json() or request.form.to_dict()
        
        result = PaymentService.handle_webhook(db, provider, webhook_data)
        
        if result:
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'status': 'error'}), 400
        
    except Exception as e:
        current_app.logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error'}), 500


@payments_bp.route('/refund/<int:transaction_id>', methods=['POST'])
@jwt_required()
def request_refund(transaction_id):
    """Запрос возврата средств"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        reason = request.json.get('reason', '') if request.json else ''
        
        refund = PaymentService.create_refund(db, transaction_id, user_id, reason)
        
        if refund:
            return jsonify({
                'success': True,
                'message': 'Refund request created successfully'
            })
        else:
            return jsonify({
                'error': 'Transaction not found or refund not allowed'
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error requesting refund: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/balance', methods=['GET'])
@jwt_required()
def get_user_balance():
    """Получение баланса пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        balance = PaymentService.get_user_balance(db, user_id)
        
        return jsonify({
            'success': True,
            'data': {'balance': balance}
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user balance: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payments_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_payment_statistics():
    """Получение статистики платежей пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        stats = PaymentService.get_user_payment_stats(db, user_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting payment statistics: {e}")
        return jsonify({'error': 'Internal server error'}), 500



