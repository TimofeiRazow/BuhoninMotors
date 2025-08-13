# app/blueprints/support/services.py
"""
Сервисы для системы поддержки
"""

from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from app.models.support import SupportTicket
from app.models.category import Category
from app.models.user import User
from app.utils.pagination import paginate


class SupportService:
    """Сервис для работы с системой поддержки"""
    
    @staticmethod
    def get_user_tickets(db, user_id, page=1, per_page=20, status=None, category_id=None):
        """Получение тикетов пользователя"""
        query = db.query(SupportTicket).options(
            joinedload(SupportTicket.category),
            joinedload(SupportTicket.assigned_user)
        ).filter(
            SupportTicket.user_id == user_id
        )
        
        if status:
            query = query.filter(SupportTicket.status_id == status)
        
        if category_id:
            query = query.filter(SupportTicket.category_id == category_id)
        
        query = query.order_by(SupportTicket.created_date.desc())
        
        return paginate(query, page, per_page)
    
    @staticmethod
    def create_ticket(db, user_id, data):
        """Создание нового тикета поддержки"""
        from app.models.base import GlobalEntity
        
        # Создаем сущность
        entity = GlobalEntity(entity_type='ticket')
        db.add(entity)
        db.flush()
        
        # Создаем тикет
        ticket = SupportTicket(
            entity_id=entity.entity_id,
            user_id=user_id,
            category_id=data.get('category_id'),
            priority=data.get('priority', 'medium'),
            subject=data['subject'],
            description=data['description'],
            status_id=1  # открыт
        )
        
        db.add(ticket)
        db.commit()
        
        # Отправляем уведомление администраторам
        SupportService._notify_admins_new_ticket(db, ticket)
        
        return ticket
    
    @staticmethod
    def get_ticket(db, ticket_id, user_id):
        """Получение конкретного тикета"""
        return db.query(SupportTicket).options(
            joinedload(SupportTicket.category),
            joinedload(SupportTicket.assigned_user),
            joinedload(SupportTicket.user)
        ).filter(
            SupportTicket.ticket_id == ticket_id,
            SupportTicket.user_id == user_id
        ).first()
    
    @staticmethod
    def add_ticket_response(db, ticket_id, user_id, data):
        """Добавление ответа к тикету"""
        from app.models.conversation import Conversation, Message
        from app.models.base import GlobalEntity
        
        ticket = db.query(SupportTicket).filter(
            SupportTicket.ticket_id == ticket_id,
            SupportTicket.user_id == user_id
        ).first()
        
        if not ticket:
            return None
        
        # Находим или создаем диалог для тикета
        conversation = db.query(Conversation).filter_by(
            related_entity_id=ticket.entity_id
        ).first()
        
        if not conversation:
            # Создаем диалог
            conv_entity = GlobalEntity(entity_type='conversation')
            db.add(conv_entity)
            db.flush()
            
            conversation = Conversation(
                entity_id=conv_entity.entity_id,
                conversation_type='support',
                subject=ticket.subject,
                related_entity_id=ticket.entity_id,
                status_id=1
            )
            db.add(conversation)
            db.flush()
        
        # Создаем сообщение
        msg_entity = GlobalEntity(entity_type='message')
        db.add(msg_entity)
        db.flush()
        
        message = Message(
            entity_id=msg_entity.entity_id,
            conversation_id=conversation.conversation_id,
            sender_id=user_id,
            message_text=data['message'],
            message_type='text'
        )
        
        db.add(message)
        
        # Обновляем статус тикета
        if ticket.status_id in [3, 4]:  # если был закрыт или решен
            ticket.status_id = 1  # открываем снова
        
        db.commit()
        
        return message
    
    @staticmethod
    def close_ticket(db, ticket_id, user_id, satisfaction=None):
        """Закрытие тикета пользователем"""
        ticket = db.query(SupportTicket).filter(
            SupportTicket.ticket_id == ticket_id,
            SupportTicket.user_id == user_id
        ).first()
        
        if not ticket or ticket.status_id == 4:  # уже закрыт
            return False
        
        ticket.status_id = 4  # закрыт
        ticket.resolved_date = datetime.utcnow()
        
        if satisfaction:
            ticket.customer_satisfaction = satisfaction
        
        db.commit()
        return True
    
    @staticmethod
    def get_support_categories(db):
        """Получение категорий поддержки"""
        categories = db.query(Category).filter(
            Category.tree_id == (
                db.query(Category.tree_id).join(
                    CategoryTree, Category.tree_id == CategoryTree.tree_id
                ).filter(CategoryTree.tree_code == 'support_categories').scalar()
            ),
            Category.is_active == True
        ).order_by(Category.sort_order).all()
        
        return [
            {
                'category_id': cat.category_id,
                'category_name': cat.category_name,
                'description': cat.description,
                'parent_category_id': cat.parent_category_id
            }
            for cat in categories
        ]
    
    @staticmethod
    def get_faq(db, category_id=None, search=''):
        """Получение FAQ"""
        # Здесь можно реализовать отдельную таблицу FAQ или использовать категории
        # Для примера, возвращаем статические данные
        faq_data = [
            {
                'id': 1,
                'question': 'Как создать объявление?',
                'answer': 'Для создания объявления перейдите в раздел "Подать объявление" и заполните все необходимые поля.',
                'category_id': 1
            },
            {
                'id': 2,
                'question': 'Как продвинуть объявление?',
                'answer': 'Вы можете воспользоваться платными услугами продвижения в разделе "Мои объявления".',
                'category_id': 1
            },
            {
                'id': 3,
                'question': 'Как связаться с продавцом?',
                'answer': 'Используйте кнопку "Написать продавцу" в карточке объявления.',
                'category_id': 2
            },
            {
                'id': 4,
                'question': 'Проблемы с оплатой',
                'answer': 'Если у вас возникли проблемы с оплатой, обратитесь в службу поддержки.',
                'category_id': 3
            }
        ]
        
        # Фильтрация по категории
        if category_id:
            faq_data = [item for item in faq_data if item['category_id'] == category_id]
        
        # Поиск
        if search:
            search_lower = search.lower()
            faq_data = [
                item for item in faq_data 
                if search_lower in item['question'].lower() or search_lower in item['answer'].lower()
            ]
        
        return faq_data
    
    @staticmethod
    def get_all_tickets(db, page=1, per_page=20, status=None, priority=None, assigned_to=None):
        """Получение всех тикетов для администраторов"""
        query = db.query(SupportTicket).options(
            joinedload(SupportTicket.category),
            joinedload(SupportTicket.user),
            joinedload(SupportTicket.assigned_user)
        )
        
        if status:
            query = query.filter(SupportTicket.status_id == status)
        
        if priority:
            query = query.filter(SupportTicket.priority == priority)
        
        if assigned_to:
            query = query.filter(SupportTicket.assigned_to == assigned_to)
        
        query = query.order_by(
            SupportTicket.priority.desc(),
            SupportTicket.created_date.desc()
        )
        
        return paginate(query, page, per_page)
    
    @staticmethod
    def update_ticket(db, ticket_id, admin_id, data):
        """Обновление тикета администратором"""
        ticket = db.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
        
        if not ticket:
            return None
        
        # Обновляем поля
        if 'status_id' in data:
            ticket.status_id = data['status_id']
            if data['status_id'] in [3, 4]:  # решен или закрыт
                ticket.resolved_date = datetime.utcnow()
        
        if 'priority' in data:
            ticket.priority = data['priority']
        
        if 'assigned_to' in data:
            ticket.assigned_to = data['assigned_to']
            if not ticket.first_response_date:
                ticket.first_response_date = datetime.utcnow()
        
        if 'category_id' in data:
            ticket.category_id = data['category_id']
        
        db.commit()
        return ticket
    
    @staticmethod
    def assign_ticket(db, ticket_id, assigned_to, admin_id):
        """Назначение тикета администратору"""
        ticket = db.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
        
        if not ticket:
            return False
        
        ticket.assigned_to = assigned_to
        
        if not ticket.first_response_date:
            ticket.first_response_date = datetime.utcnow()
        
        db.commit()
        return True
    
    @staticmethod
    def get_support_statistics(db):
        """Получение статистики поддержки"""
        # Общая статистика
        total_tickets = db.query(SupportTicket).count()
        open_tickets = db.query(SupportTicket).filter(SupportTicket.status_id.in_([1, 2])).count()
        resolved_tickets = db.query(SupportTicket).filter(SupportTicket.status_id == 3).count()
        closed_tickets = db.query(SupportTicket).filter(SupportTicket.status_id == 4).count()
        
        # Статистика по приоритетам
        priority_stats = db.query(
            SupportTicket.priority,
            func.count(SupportTicket.ticket_id).label('count')
        ).group_by(SupportTicket.priority).all()
        
        # Статистика по категориям
        category_stats = db.query(
            Category.category_name,
            func.count(SupportTicket.ticket_id).label('count')
        ).join(
            SupportTicket, Category.category_id == SupportTicket.category_id
        ).group_by(Category.category_name).all()
        
        # Среднее время ответа
        avg_response_time = db.query(
            func.avg(
                func.extract('epoch', SupportTicket.first_response_date - SupportTicket.created_date)
            ).label('avg_seconds')
        ).filter(SupportTicket.first_response_date.isnot(None)).scalar()
        
        # Среднее время решения
        avg_resolution_time = db.query(
            func.avg(
                func.extract('epoch', SupportTicket.resolved_date - SupportTicket.created_date)
            ).label('avg_seconds')
        ).filter(SupportTicket.resolved_date.isnot(None)).scalar()
        
        # Средняя оценка удовлетворенности
        avg_satisfaction = db.query(
            func.avg(SupportTicket.customer_satisfaction)
        ).filter(SupportTicket.customer_satisfaction.isnot(None)).scalar()
        
        return {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'resolved_tickets': resolved_tickets,
            'closed_tickets': closed_tickets,
            'priority_stats': [
                {'priority': stat.priority, 'count': stat.count}
                for stat in priority_stats
            ],
            'category_stats': [
                {'category': stat.category_name, 'count': stat.count}
                for stat in category_stats
            ],
            'avg_response_time_hours': round((avg_response_time or 0) / 3600, 2),
            'avg_resolution_time_hours': round((avg_resolution_time or 0) / 3600, 2),
            'avg_satisfaction': round(float(avg_satisfaction or 0), 2)
        }
    
    @staticmethod
    def _notify_admins_new_ticket(db, ticket):
        """Уведомление администраторов о новом тикете"""
        from app.models.notification import Notification, NotificationChannel
        
        # Получаем администраторов
        admins = db.query(User).filter(User.user_type == 'admin', User.is_active == True).all()
        
        # Получаем канал уведомлений
        channel = db.query(NotificationChannel).filter_by(channel_code='email').first()
        
        if channel:
            for admin in admins:
                notification = Notification(
                    user_id=admin.user_id,
                    channel_id=channel.channel_id,
                    title='Новый тикет поддержки',
                    message=f'Создан новый тикет #{ticket.ticket_id}: {ticket.subject}',
                    notification_type='new_support_ticket',
                    related_entity_id=ticket.entity_id
                )
                db.add(notification)
        
        db.commit()