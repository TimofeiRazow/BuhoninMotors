# app/blueprints/conversations/routes.py
from flask import request, jsonify, g, current_app
from app.blueprints.conversations import bp
from app.blueprints.conversations.services import ConversationService
from app.blueprints.conversations.schemas import (
    CreateConversationSchema, SendMessageSchema, EditMessageSchema,
    ConversationSchema, MessageSchema
)
from app.utils.decorators import (
    handle_errors, auth_required, validate_json, paginate, rate_limit_by_user
)
from app.utils.pagination import create_pagination_response


@bp.route('/', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_conversations():
    """Получение диалогов пользователя"""
    try:
        current_app.logger.info(f"Getting conversations for user: {g.current_user.user_id}")
        
        pagination = ConversationService.get_user_conversations(
            user_id=g.current_user.user_id,
            page=g.pagination['page'],
            per_page=g.pagination['per_page']
        )
        
        # Добавляем информацию для текущего пользователя
        conversations_data = []
        for conversation in pagination.items:
            conv_dict = conversation.to_dict(user_id=g.current_user.user_id)
            conversations_data.append(conv_dict)
        
        # Создаем ответ с пагинацией
        response = create_pagination_response(pagination)
        response['data'] = conversations_data
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting conversations: {str(e)}")
        return jsonify({
            'error': 'Failed to get conversations',
            'message': str(e)
        }), 500


@bp.route('/', methods=['POST'])
@handle_errors
@auth_required
@validate_json(CreateConversationSchema)
def create_conversation():
    """Создание нового диалога"""
    try:
        data = g.validated_data
        
        conversation = ConversationService.create_conversation(
            creator_id=g.current_user.user_id,
            participant_id=data['participant_id'],
            conversation_type=data['conversation_type'],
            subject=data.get('subject'),
            related_entity_id=data.get('related_entity_id'),
            initial_message=data['initial_message']
        )
        
        schema = ConversationSchema()
        
        return jsonify({
            'data': schema.dump(conversation),
            'message': "Conversation created successfully",
            'status_code': 201
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating conversation: {str(e)}")
        return jsonify({
            'error': 'Failed to create conversation',
            'message': str(e)
        }), 500


@bp.route('/<int:conversation_id>', methods=['GET'])
@handle_errors
@auth_required
def get_conversation(conversation_id):
    """Получение диалога"""
    try:
        conversation = ConversationService.get_conversation(
            conversation_id=conversation_id,
            user_id=g.current_user.user_id
        )
        
        conv_dict = conversation.to_dict(user_id=g.current_user.user_id)
        
        return jsonify({
            'data': conv_dict,
            'message': "Conversation retrieved successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to get conversation',
            'message': str(e)
        }), 500


@bp.route('/<int:conversation_id>/messages', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_conversation_messages(conversation_id):
    """Получение сообщений диалога"""
    try:
        pagination = ConversationService.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=g.current_user.user_id,
            page=g.pagination['page'],
            per_page=g.pagination['per_page']
        )
        
        # Автоматически отмечаем диалог как прочитанный
        ConversationService.mark_conversation_as_read(
            conversation_id=conversation_id,
            user_id=g.current_user.user_id
        )
        
        response = create_pagination_response(pagination)
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to get messages',
            'message': str(e)
        }), 500


@bp.route('/<int:conversation_id>/messages', methods=['POST'])
@handle_errors
@auth_required
@validate_json(SendMessageSchema)
def send_message(conversation_id):
    """Отправка сообщения"""
    try:
        data = g.validated_data
        
        message = ConversationService.send_message(
            conversation_id=conversation_id,
            sender_id=g.current_user.user_id,
            message_text=data['message_text'],
            message_type=data.get('message_type', 'text'),
            parent_message_id=data.get('parent_message_id'),
            meta_data=data.get('meta_data')
        )
        
        schema = MessageSchema()
        
        return jsonify({
            'data': schema.dump(message),
            'message': "Message sent successfully",
            'status_code': 201
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error sending message to conversation {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to send message',
            'message': str(e)
        }), 500


@bp.route('/messages/<int:message_id>', methods=['PUT'])
@handle_errors
@auth_required
@validate_json(EditMessageSchema)
def edit_message(message_id):
    """Редактирование сообщения"""
    try:
        data = g.validated_data
        
        message = ConversationService.edit_message(
            message_id=message_id,
            user_id=g.current_user.user_id,
            new_text=data['message_text']
        )
        
        schema = MessageSchema()
        
        return jsonify({
            'data': schema.dump(message),
            'message': "Message edited successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error editing message {message_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to edit message',
            'message': str(e)
        }), 500


@bp.route('/messages/<int:message_id>', methods=['DELETE'])
@handle_errors
@auth_required
def delete_message(message_id):
    """Удаление сообщения"""
    try:
        success = ConversationService.delete_message(
            message_id=message_id,
            user_id=g.current_user.user_id
        )
        
        return jsonify({
            'data': {'deleted': success},
            'message': "Message deleted successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting message {message_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to delete message',
            'message': str(e)
        }), 500


@bp.route('/<int:conversation_id>/read', methods=['POST'])
@handle_errors
@auth_required
def mark_as_read(conversation_id):
    """Отметка диалога как прочитанного"""
    try:
        success = ConversationService.mark_conversation_as_read(
            conversation_id=conversation_id,
            user_id=g.current_user.user_id
        )
        
        return jsonify({
            'data': {'marked_as_read': success},
            'message': "Conversation marked as read"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error marking conversation {conversation_id} as read: {str(e)}")
        return jsonify({
            'error': 'Failed to mark as read',
            'message': str(e)
        }), 500


@bp.route('/<int:conversation_id>/leave', methods=['POST'])
@handle_errors
@auth_required
def leave_conversation(conversation_id):
    """Выход из диалога"""
    try:
        success = ConversationService.leave_conversation(
            conversation_id=conversation_id,
            user_id=g.current_user.user_id
        )
        
        return jsonify({
            'data': {'left': success},
            'message': "Left conversation successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error leaving conversation {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to leave conversation',
            'message': str(e)
        }), 500


@bp.route('/unread-count', methods=['GET'])
@handle_errors
@auth_required
def get_unread_count():
    """Получение количества непрочитанных диалогов"""
    try:
        current_app.logger.info(f"Getting unread count for user: {g.current_user.user_id}")
        
        count = ConversationService.get_unread_conversations_count(g.current_user.user_id)
        
        return jsonify({
            'data': {'unread_count': count},
            'message': "Unread count retrieved successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({
            'error': 'Failed to get unread count',
            'message': str(e)
        }), 500