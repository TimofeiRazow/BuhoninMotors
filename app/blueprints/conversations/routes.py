# app/blueprints/conversations/routes.py
from flask import request, jsonify, g
from app.blueprints.conversations import bp
from app.blueprints.conversations.services import ConversationService
from app.blueprints.conversations.schemas import (
    CreateConversationSchema, SendMessageSchema, EditMessageSchema,
    ConversationSchema, MessageSchema
)
from app.utils.decorators import (
    handle_errors, auth_required, validate_json, paginate, rate_limit_by_user
)
from app.utils.helpers import build_response
from app.utils.pagination import create_pagination_response


@bp.route('/', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_conversations():
    """Получение диалогов пользователя"""
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


@bp.route('/', methods=['POST'])
@handle_errors
@validate_json(CreateConversationSchema)
@auth_required
@rate_limit_by_user('create_conversation', max_requests=20, window_minutes=60)
def create_conversation():
    """Создание нового диалога"""
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
    
    return jsonify(build_response(
        data=schema.dump(conversation),
        message="Conversation created successfully",
        status_code=201
    ))


@bp.route('/<int:conversation_id>', methods=['GET'])
@handle_errors
@auth_required
def get_conversation(conversation_id):
    """Получение диалога"""
    conversation = ConversationService.get_conversation(
        conversation_id=conversation_id,
        user_id=g.current_user.user_id
    )
    
    conv_dict = conversation.to_dict(user_id=g.current_user.user_id)
    
    return jsonify(build_response(
        data=conv_dict,
        message="Conversation retrieved successfully"
    ))


@bp.route('/<int:conversation_id>/messages', methods=['GET'])
@handle_errors
@auth_required
@paginate()
def get_conversation_messages(conversation_id):
    """Получение сообщений диалога"""
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


@bp.route('/<int:conversation_id>/messages', methods=['POST'])
@handle_errors
@validate_json(SendMessageSchema)
@auth_required
@rate_limit_by_user('send_message', max_requests=100, window_minutes=60)
def send_message(conversation_id):
    """Отправка сообщения"""
    data = g.validated_data
    
    message = ConversationService.send_message(
        conversation_id=conversation_id,
        sender_id=g.current_user.user_id,
        message_text=data['message_text'],
        message_type=data.get('message_type', 'text'),
        parent_message_id=data.get('parent_message_id'),
        metadata=data.get('metadata')
    )
    
    schema = MessageSchema()
    
    return jsonify(build_response(
        data=schema.dump(message),
        message="Message sent successfully",
        status_code=201
    ))


@bp.route('/messages/<int:message_id>', methods=['PUT'])
@handle_errors
@validate_json(EditMessageSchema)
@auth_required
def edit_message(message_id):
    """Редактирование сообщения"""
    data = g.validated_data
    
    message = ConversationService.edit_message(
        message_id=message_id,
        user_id=g.current_user.user_id,
        new_text=data['message_text']
    )
    
    schema = MessageSchema()
    
    return jsonify(build_response(
        data=schema.dump(message),
        message="Message edited successfully"
    ))


@bp.route('/messages/<int:message_id>', methods=['DELETE'])
@handle_errors
@auth_required
def delete_message(message_id):
    """Удаление сообщения"""
    success = ConversationService.delete_message(
        message_id=message_id,
        user_id=g.current_user.user_id
    )
    
    return jsonify(build_response(
        data={'deleted': success},
        message="Message deleted successfully"
    ))


@bp.route('/<int:conversation_id>/read', methods=['POST'])
@handle_errors
@auth_required
def mark_as_read(conversation_id):
    """Отметка диалога как прочитанного"""
    success = ConversationService.mark_conversation_as_read(
        conversation_id=conversation_id,
        user_id=g.current_user.user_id
    )
    
    return jsonify(build_response(
        data={'marked_as_read': success},
        message="Conversation marked as read"
    ))


@bp.route('/<int:conversation_id>/leave', methods=['POST'])
@handle_errors
@auth_required
def leave_conversation(conversation_id):
    """Выход из диалога"""
    success = ConversationService.leave_conversation(
        conversation_id=conversation_id,
        user_id=g.current_user.user_id
    )
    
    return jsonify(build_response(
        data={'left': success},
        message="Left conversation successfully"
    ))


@bp.route('/unread-count', methods=['GET'])
@handle_errors
@auth_required
def get_unread_count():
    """Получение количества непрочитанных диалогов"""
    count = ConversationService.get_unread_conversations_count(g.current_user.user_id)
    
    return jsonify(build_response(
        data={'unread_count': count},
        message="Unread count retrieved successfully"
    ))