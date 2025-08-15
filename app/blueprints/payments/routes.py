# app/blueprints/payments/routes.py
"""
Роуты для платежей и продвижения объявлений (тестовые данные)
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app.blueprints.payments import payments_bp
from app.utils.decorators import validate_json
from app.blueprints.payments.schemas import PromoteListingSchema, CreatePaymentSchema

@payments_bp.route('/services', methods=['GET'])
def get_promotion_services():
    """Получение доступных услуг продвижения (тестовые данные)"""
    # db = get_db()
    # services = PromotionService.get_promotion_services(db)
    return jsonify({
        'success': True,
        'data': [
            {'id': 1, 'name': 'Top placement', 'price': 1000},
            {'id': 2, 'name': 'Highlight', 'price': 500}
        ]
    })


@payments_bp.route('/promote-listing', methods=['POST'])
@jwt_required()
@validate_json(PromoteListingSchema)
def promote_listing():
    """Продвижение объявления (тестовые данные)"""
    # user_id = get_jwt_identity()
    # schema = PromoteListingSchema()
    # data = schema.load(request.json)
    return jsonify({
        'success': True,
        'data': {'listing_id': 123, 'promotion_type': 'top', 'status': 'active'},
        'message': 'Listing promotion created successfully'
    }), 201


@payments_bp.route('/my-promotions', methods=['GET'])
@jwt_required()
def get_my_promotions():
    """Получение активных продвижений пользователя (тестовые данные)"""
    return jsonify({
        'success': True,
        'data': {
            'promotions': [
                {'id': 1, 'listing_id': 123, 'status': 'active', 'expires_at': '2025-12-31'},
                {'id': 2, 'listing_id': 456, 'status': 'expired', 'expires_at': '2025-01-01'}
            ],
            'pagination': {'page': 1, 'per_page': 20, 'total': 2, 'pages': 1}
        }
    })


@payments_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_payment_history():
    """Получение истории платежей пользователя (тестовые данные)"""
    return jsonify({
        'success': True,
        'data': {
            'transactions': [
                {'id': 1, 'amount': 1000, 'type': 'promotion', 'status': 'completed'},
                {'id': 2, 'amount': 500, 'type': 'promotion', 'status': 'pending'}
            ],
            'pagination': {'page': 1, 'per_page': 20, 'total': 2, 'pages': 1}
        }
    })


@payments_bp.route('/create-payment', methods=['POST'])
@jwt_required()
@validate_json(CreatePaymentSchema)
def create_payment():
    """Создание платежа (тестовые данные)"""
    return jsonify({
        'success': True,
        'data': {'id': 1, 'amount': 1000, 'status': 'pending'},
        'message': 'Payment created successfully'
    }), 201


@payments_bp.route('/process-payment/<int:transaction_id>', methods=['POST'])
@jwt_required()
def process_payment(transaction_id):
    """Обработка платежа (тестовые данные)"""
    return jsonify({
        'success': True,
        'data': {'transaction_id': transaction_id, 'status': 'completed'},
        'message': 'Payment processed successfully'
    })


@payments_bp.route('/webhook/<provider>', methods=['POST'])
def payment_webhook(provider):
    """Webhook для обработки уведомлений (тестовые данные)"""
    return jsonify({'status': 'ok'})


@payments_bp.route('/refund/<int:transaction_id>', methods=['POST'])
@jwt_required()
def request_refund(transaction_id):
    """Запрос возврата средств (тестовые данные)"""
    return jsonify({
        'success': True,
        'message': f'Refund request for transaction {transaction_id} created successfully'
    })


@payments_bp.route('/balance', methods=['GET'])
@jwt_required()
def get_user_balance():
    """Получение баланса пользователя (тестовые данные)"""
    return jsonify({
        'success': True,
        'data': {'balance': 2500}
    })


@payments_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_payment_statistics():
    """Получение статистики платежей пользователя (тестовые данные)"""
    return jsonify({
        'success': True,
        'data': {'total_payments': 5, 'total_amount': 5000}
    })
