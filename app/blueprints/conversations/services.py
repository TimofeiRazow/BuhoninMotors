
# app/blueprints/conversations/services.py
from datetime import datetime
from sqlalchemy import and_, or_, desc, func
from app.extensions import db
from app.models.conversation import Conversation, ConversationParticipant, Message, MessageAttachment
from app.models.user import User
from app.models.base import get_status_by_code
from app.utils.exceptions import (
    NotFoundError, AuthorizationError, ValidationError, UserNotFoundError
)
from app.utils.pagination import paginate_query


class ConversationService:
    """Сервис для работы с диалогами"""
    
    @staticmethod
    def create_conversation(creator_id, participant_id, conversation_type='user_chat', 
                          subject=None, related_entity_id=None, initial_message=None):
        """
        Создание нового диалога
        
        Args:
            creator_id: ID создателя диалога
            participant_id: ID другого участника
            conversation_type: Тип диалога
            subject: Тема диалога
            related_entity_id: ID связанной сущности
            initial_message: Начальное сообщение
            
        Returns:
            Созданный диалог
            
        Raises:
            UserNotFoundError: Если участник не найден
            ValidationError: Если диалог уже существует
        """
        # Проверяем существование участника
        participant = User.query.get(participant_id)
        if not participant or not participant.is_active:
            raise UserNotFoundError(participant_id)
        
        # Проверяем, нет ли уже диалога между этими пользователями
        if conversation_type == 'user_chat':
            existing = ConversationService._find_existing_conversation(
                creator_id, participant_id, related_entity_id
            )
            if existing:
                return existing
        
        # Получаем статус
        active_status = get_status_by_code('conversation_status', 'active')
        
        # Создаем диалог
        conversation = Conversation(
            conversation_type=conversation_type,
            subject=subject,
            related_entity_id=related_entity_id,
            status_id=active_status.status_id if active_status else None
        )
        conversation.save()
        
        # Добавляем участников
        conversation.add_participant(creator_id, 'participant')
        conversation.add_participant(participant_id, 'participant')
        
        # Отправляем начальное сообщение
        if initial_message:
            ConversationService.send_message(
                conversation.conversation_id,
                creator_id,
                initial_message
            )
        
        return conversation
    
    @staticmethod
    def _find_existing_conversation(user1_id, user2_id, related_entity_id=None):
        """Поиск существующего диалога между пользователями"""
        query = db.session.query(Conversation).join(ConversationParticipant).filter(
            Conversation.conversation_type == 'user_chat',
            Conversation.is_active == True
        )
        
        if related_entity_id:
            query = query.filter(Conversation.related_entity_id == related_entity_id)
        
        # Находим диалоги, где участвуют оба пользователя
        conversations = query.filter(
            ConversationParticipant.user_id.in_([user1_id, user2_id])
        ).group_by(Conversation.conversation_id).having(
            func.count(ConversationParticipant.user_id) == 2
        ).all()
        
        # Проверяем, что участников именно двое и это нужные пользователи
        for conv in conversations:
            participant_ids = [p.user_id for p in conv.get_participants()]
            if set(participant_ids) == {user1_id, user2_id}:
                return conv
        
        return None
    
    @staticmethod
    def get_user_conversations(user_id, page=1, per_page=20):
        """
        Получение диалогов пользователя
        
        Args:
            user_id: ID пользователя
            page: Номер страницы
            per_page: Диалогов на странице
            
        Returns:
            Диалоги с пагинацией
        """
        query = Conversation.query.join(ConversationParticipant).filter(
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.is_active == True,
            Conversation.is_active == True
        ).order_by(
            desc(Conversation.last_message_date),
            desc(Conversation.created_date)
        )
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def get_conversation(conversation_id, user_id):
        """
        Получение диалога
        
        Args:
            conversation_id: ID диалога
            user_id: ID пользователя
            
        Returns:
            Диалог
            
        Raises:
            NotFoundError: Если диалог не найден
            AuthorizationError: Если пользователь не участник
        """
        conversation = Conversation.query.get(conversation_id)
        if not conversation or not conversation.is_active:
            raise NotFoundError("Conversation not found")
        
        # Проверяем, является ли пользователь участником
        participant = conversation.get_participant(user_id)
        if not participant:
            raise AuthorizationError("You are not a participant of this conversation")
        
        return conversation
    
    @staticmethod
    def get_conversation_messages(conversation_id, user_id, page=1, per_page=50):
        """
        Получение сообщений диалога
        
        Args:
            conversation_id: ID диалога
            user_id: ID пользователя
            page: Номер страницы
            per_page: Сообщений на странице
            
        Returns:
            Сообщения с пагинацией
            
        Raises:
            NotFoundError: Если диалог не найден
            AuthorizationError: Если пользователь не участник
        """
        # Проверяем доступ к диалогу
        conversation = ConversationService.get_conversation(conversation_id, user_id)
        
        # Получаем сообщения
        query = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        ).order_by(desc(Message.sent_date))
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def send_message(conversation_id, sender_id, message_text, message_type='text',
                    parent_message_id=None, meta_data=None):
        """
        Отправка сообщения
        
        Args:
            conversation_id: ID диалога
            sender_id: ID отправителя
            message_text: Текст сообщения
            message_type: Тип сообщения
            parent_message_id: ID родительского сообщения
            meta_data: Метаданные
            
        Returns:
            Отправленное сообщение
            
        Raises:
            NotFoundError: Если диалог не найден
            AuthorizationError: Если пользователь не участник
        """
        # Проверяем доступ к диалогу
        conversation = ConversationService.get_conversation(conversation_id, sender_id)
        
        # Создаем сообщение
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            message_text=message_text,
            message_type=message_type,
            parent_message_id=parent_message_id,
            meta_data=meta_data or {}
        )
        message.save()
        
        # Обновляем время последнего сообщения в диалоге
        conversation.update_last_message_date()
        
        # TODO: Отправить уведомления другим участникам
        
        return message
    
    @staticmethod
    def edit_message(message_id, user_id, new_text):
        """
        Редактирование сообщения
        
        Args:
            message_id: ID сообщения
            user_id: ID пользователя
            new_text: Новый текст
            
        Returns:
            Отредактированное сообщение
            
        Raises:
            NotFoundError: Если сообщение не найдено
            AuthorizationError: Если пользователь не автор
        """
        message = Message.query.get(message_id)
        if not message or message.is_deleted:
            raise NotFoundError("Message not found")
        
        # Проверяем, что пользователь - автор сообщения
        if message.sender_id != user_id:
            raise AuthorizationError("You can only edit your own messages")
        
        # Проверяем время редактирования (например, не позже 24 часов)
        time_limit = datetime.utcnow() - timedelta(hours=24)
        if message.sent_date < time_limit:
            raise ValidationError("Message is too old to edit")
        
        message.edit_message(new_text)
        return message
    
    @staticmethod
    def delete_message(message_id, user_id):
        """
        Удаление сообщения
        
        Args:
            message_id: ID сообщения
            user_id: ID пользователя
            
        Returns:
            True если успешно удалено
            
        Raises:
            NotFoundError: Если сообщение не найдено
            AuthorizationError: Если пользователь не автор
        """
        message = Message.query.get(message_id)
        if not message or message.is_deleted:
            raise NotFoundError("Message not found")
        
        # Проверяем права на удаление
        if message.sender_id != user_id:
            # Админы могут удалять любые сообщения
            user = User.query.get(user_id)
            if not user or user.user_type != 'admin':
                raise AuthorizationError("You can only delete your own messages")
        
        message.soft_delete()
        return True
    
    @staticmethod
    def mark_conversation_as_read(conversation_id, user_id):
        """
        Отметка диалога как прочитанного
        
        Args:
            conversation_id: ID диалога
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если диалог не найден
            AuthorizationError: Если пользователь не участник
        """
        conversation = ConversationService.get_conversation(conversation_id, user_id)
        conversation.mark_as_read(user_id)
        return True
    
    @staticmethod
    def get_unread_conversations_count(user_id):
        """
        Получение количества непрочитанных диалогов
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество непрочитанных диалогов
        """
        # Получаем диалоги где есть новые сообщения
        subquery = db.session.query(Message.conversation_id).join(
            ConversationParticipant,
            and_(
                Message.conversation_id == ConversationParticipant.conversation_id,
                ConversationParticipant.user_id == user_id
            )
        ).filter(
            Message.sender_id != user_id,
            Message.is_deleted == False,
            or_(
                ConversationParticipant.last_read_date.is_(None),
                Message.sent_date > ConversationParticipant.last_read_date
            )
        ).distinct().subquery()
        
        return db.session.query(func.count()).select_from(subquery).scalar()
    
    @staticmethod
    def leave_conversation(conversation_id, user_id):
        """
        Выход из диалога
        
        Args:
            conversation_id: ID диалога
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если диалог не найден
            AuthorizationError: Если пользователь не участник
        """
        conversation = ConversationService.get_conversation(conversation_id, user_id)
        participant = conversation.get_participant(user_id)
        
        if participant:
            participant.soft_delete()
            
            # Если остался только один участник, деактивируем диалог
            active_participants = conversation.get_participants()
            if len(active_participants) <= 1:
                conversation.soft_delete()
        
        return True