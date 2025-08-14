# app/blueprints/support/routes.py
"""
Роуты для системы поддержки
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.blueprints.support import support_bp
from app.blueprints.support.services import SupportService
from app.blueprints.support.schemas import (
    SupportTicketSchema, CreateTicketSchema, TicketResponseSchema,
    TicketListSchema, UpdateTicketSchema
)
from app.utils.decorators import admin_required, validate_json
from app.database import get_db


@support_bp.route('/tickets', methods=['GET'])
@jwt_required()
def get_user_tickets():
    """Получение тикетов пользователя"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        category_id = request.args.get('category_id', type=int)
        
        tickets = SupportService.get_user_tickets(
            db, user_id, page, per_page, status, category_id
        )
        
        schema = TicketListSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': {
                'tickets': schema.dump(tickets['items']),
                'pagination': {
                    'page': tickets['page'],
                    'per_page': tickets['per_page'],
                    'total': tickets['total'],
                    'pages': tickets['pages']
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user tickets: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/tickets', methods=['POST'])
@jwt_required()
@validate_json(CreateTicketSchema)
def create_ticket():
    """Создание нового тикета поддержки"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        schema = CreateTicketSchema()
        data = schema.load(request.json)
        
        ticket = SupportService.create_ticket(db, user_id, data)
        
        response_schema = SupportTicketSchema()
        return jsonify({
            'success': True,
            'data': response_schema.dump(ticket),
            'message': 'Support ticket created successfully'
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating ticket: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    """Получение конкретного тикета"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        ticket = SupportService.get_ticket(db, ticket_id, user_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        schema = SupportTicketSchema()
        return jsonify({
            'success': True,
            'data': schema.dump(ticket)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting ticket: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/tickets/<int:ticket_id>/response', methods=['POST'])
@jwt_required()
@validate_json(TicketResponseSchema)
def add_ticket_response():
    """Добавление ответа к тикету"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        schema = TicketResponseSchema()
        data = schema.load(request.json)
        
        response = SupportService.add_ticket_response(db, ticket_id, user_id, data)
        if not response:
            return jsonify({'error': 'Ticket not found'}), 404
        
        return jsonify({
            'success': True,
            'data': schema.dump(response),
            'message': 'Response added successfully'
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error adding ticket response: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/tickets/<int:ticket_id>/close', methods=['PUT'])
@jwt_required()
def close_ticket(ticket_id):
    """Закрытие тикета пользователем"""
    try:
        user_id = get_jwt_identity()
        db = get_db()
        
        satisfaction = request.json.get('satisfaction') if request.json else None
        
        success = SupportService.close_ticket(db, ticket_id, user_id, satisfaction)
        if not success:
            return jsonify({'error': 'Ticket not found or cannot be closed'}), 400
        
        return jsonify({
            'success': True,
            'message': 'Ticket closed successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error closing ticket: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/categories', methods=['GET'])
def get_support_categories():
    """Получение категорий поддержки"""
    try:
        db = get_db()
        
        categories = SupportService.get_support_categories(db)
        
        return jsonify({
            'success': True,
            'data': categories
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting support categories: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/faq', methods=['GET'])
def get_faq():
    """Получение часто задаваемых вопросов"""
    try:
        db = get_db()
        
        category_id = request.args.get('category_id', type=int)
        search = request.args.get('search', '')
        
        faq = SupportService.get_faq(db, category_id, search)
        
        return jsonify({
            'success': True,
            'data': faq
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting FAQ: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Административные роуты
@support_bp.route('/admin/tickets', methods=['GET'])
@jwt_required()
@admin_required
def get_all_tickets():
    """Получение всех тикетов (для админов)"""
    try:
        db = get_db()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        assigned_to = request.args.get('assigned_to', type=int)
        
        tickets = SupportService.get_all_tickets(
            db, page, per_page, status, priority, assigned_to
        )
        
        schema = TicketListSchema(many=True)
        
        return jsonify({
            'success': True,
            'data': {
                'tickets': schema.dump(tickets['items']),
                'pagination': {
                    'page': tickets['page'],
                    'per_page': tickets['per_page'],
                    'total': tickets['total'],
                    'pages': tickets['pages']
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting all tickets: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/admin/tickets/<int:ticket_id>', methods=['PUT'])
@jwt_required()
@admin_required
@validate_json(UpdateTicketSchema)
def update_ticket(ticket_id):
    """Обновление тикета (для админов)"""
    try:
        admin_id = get_jwt_identity()
        db = get_db()
        
        schema = UpdateTicketSchema()
        data = schema.load(request.json)
        
        ticket = SupportService.update_ticket(db, ticket_id, admin_id, data)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        response_schema = SupportTicketSchema()
        return jsonify({
            'success': True,
            'data': response_schema.dump(ticket),
            'message': 'Ticket updated successfully'
        })
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating ticket: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/admin/tickets/<int:ticket_id>/assign', methods=['PUT'])
@jwt_required()
@admin_required
@validate_json
def assign_ticket(ticket_id):
    """Назначение тикета администратору"""
    try:
        admin_id = get_jwt_identity()
        db = get_db()
        
        assigned_to = request.json.get('assigned_to')
        
        success = SupportService.assign_ticket(db, ticket_id, assigned_to, admin_id)
        if not success:
            return jsonify({'error': 'Ticket not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Ticket assigned successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error assigning ticket: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@support_bp.route('/admin/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_support_statistics():
    """Получение статистики поддержки"""
    try:
        db = get_db()
        
        stats = SupportService.get_support_statistics(db)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting support statistics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


