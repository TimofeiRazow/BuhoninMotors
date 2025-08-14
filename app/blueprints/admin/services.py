# app/blueprints/admin/services.py
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, or_
from app.extensions import db
from app.models.user import User
from app.models.listing import Listing
from app.models.moderation import ModerationQueue, ReportedContent
from app.models.base import get_status_by_code
from app.utils.exceptions import NotFoundError, AuthorizationError
from app.utils.pagination import paginate_query


class AdminService:
    """Сервис для административных функций"""
    
    @staticmethod
    def get_dashboard_stats():
        """Получение статистики для дашборда"""
        today = datetime.utcnow().date()
        month_start = today.replace(day=1)
        
        stats = {
            # Пользователи
            'users_count': User.query.filter(User.is_active == True).count(),
            'new_users_today': User.query.filter(
                User.registration_date >= today,
                User.is_active == True
            ).count(),
            'new_users_month': User.query.filter(
                User.registration_date >= month_start,
                User.is_active == True
            ).count(),
            
            # Объявления
            'listings_count': Listing.query.filter(Listing.is_active == True).count(),
            'active_listings_count': Listing.query.filter(
                Listing.is_active == True
            ).count(),
            'new_listings_today': Listing.query.filter(
                Listing.created_date >= today,
                Listing.is_active == True
            ).count(),
            
            # Модерация
            'pending_moderation_count': ModerationQueue.query.filter(
                ModerationQueue.is_active == True
            ).count(),
            'pending_reports_count': ReportedContent.query.filter(
                ReportedContent.is_active == True
            ).count(),
        }
        
        return stats
    
    @staticmethod
    def get_moderation_queue(page=1, per_page=20, status=None, priority=None):
        """
        Получение очереди модерации
        
        Args:
            page: Номер страницы
            per_page: Элементов на странице
            status: Фильтр по статусу
            priority: Фильтр по приоритету
            
        Returns:
            Очередь модерации с пагинацией
        """
        query = ModerationQueue.query.filter(ModerationQueue.is_active == True)
        
        if status:
            # Фильтр по статусу можно добавить когда будет готова таблица статусов
            pass
        
        if priority is not None:
            query = query.filter(ModerationQueue.priority == priority)
        
        query = query.order_by(
            desc(ModerationQueue.priority),
            ModerationQueue.submitted_date
        )
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def moderate_content(moderation_id, moderator_id, action, reason=None, notes=None):
        """
        Модерация контента
        
        Args:
            moderation_id: ID элемента модерации
            moderator_id: ID модератора
            action: Действие (approve/reject)
            reason: Причина отклонения
            notes: Заметки модератора
            
        Returns:
            Результат модерации
            
        Raises:
            NotFoundError: Если элемент не найден
            AuthorizationError: Если нет прав
        """
        moderation_item = ModerationQueue.query.get(moderation_id)
        if not moderation_item:
            raise NotFoundError("Moderation item not found")
        
        # Проверяем права модератора
        moderator = User.query.get(moderator_id)
        if not moderator or moderator.user_type not in ['admin', 'moderator']:
            raise AuthorizationError("Insufficient permissions")
        
        if action == 'approve':
            moderation_item.approve(moderator_id, notes)
            # Активируем связанный контент
            AdminService._activate_moderated_content(moderation_item.entity_id)
        
        elif action == 'reject':
            moderation_item.reject(moderator_id, reason, notes)
            # Отклоняем связанный контент
            AdminService._reject_moderated_content(moderation_item.entity_id, reason)
        
        return moderation_item
    
    @staticmethod
    def _activate_moderated_content(entity_id):
        """Активация контента после одобрения"""
        try:
            from app.models.base import GlobalEntity
            
            entity = GlobalEntity.query.get(entity_id)
            if not entity:
                return
            
            if entity.entity_type == 'listing':
                listing = Listing.query.filter_by(entity_id=entity_id).first()
                if listing:
                    # Можно добавить логику для активации через статусы
                    listing.published_date = datetime.utcnow()
                    listing.save()
        except ImportError:
            # Если модель GlobalEntity не существует, работаем напрямую с Listing
            listing = Listing.query.get(entity_id)
            if listing:
                listing.published_date = datetime.utcnow()
                listing.save()
    
    @staticmethod
    def _reject_moderated_content(entity_id, reason):
        """Отклонение контента"""
        try:
            from app.models.base import GlobalEntity
            
            entity = GlobalEntity.query.get(entity_id)
            if not entity:
                return
            
            if entity.entity_type == 'listing':
                listing = Listing.query.filter_by(entity_id=entity_id).first()
                if listing:
                    listing.soft_delete()
        except ImportError:
            # Если модель GlobalEntity не существует, работаем напрямую с Listing
            listing = Listing.query.get(entity_id)
            if listing:
                listing.soft_delete()
    
    @staticmethod
    def get_reports(page=1, per_page=20, status=None, reason=None):
        """
        Получение жалоб
        
        Args:
            page: Номер страницы
            per_page: Элементов на странице
            status: Фильтр по статусу
            reason: Фильтр по причине
            
        Returns:
            Жалобы с пагинацией
        """
        query = ReportedContent.query.filter(ReportedContent.is_active == True)
        
        if status:
            # Фильтр по статусу можно добавить когда будет готова таблица статусов
            pass
        
        if reason:
            query = query.filter(ReportedContent.report_reason == reason)
        
        query = query.order_by(desc(ReportedContent.created_date))
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def report_content(reporter_id, entity_id, reason, description=None):
        """
        Создание жалобы на контент
        
        Args:
            reporter_id: ID пользователя, подающего жалобу
            entity_id: ID сущности
            reason: Причина жалобы
            description: Описание
            
        Returns:
            Созданная жалоба
        """
        # Проверяем, не подавал ли пользователь уже жалобу на этот контент
        existing = ReportedContent.query.filter(
            ReportedContent.reporter_id == reporter_id,
            ReportedContent.entity_id == entity_id,
            ReportedContent.is_active == True
        ).first()
        
        if existing:
            return existing
        
        report = ReportedContent(
            reporter_id=reporter_id,
            entity_id=entity_id,
            report_reason=reason,
            description=description
        )
        report.save()
        
        return report
    
    @staticmethod
    def resolve_report(report_id, resolver_id, action, notes=None):
        """
        Разрешение жалобы
        
        Args:
            report_id: ID жалобы
            resolver_id: ID разрешающего
            action: Действие
            notes: Заметки
            
        Returns:
            Разрешенная жалоба
        """
        report = ReportedContent.query.get(report_id)
        if not report:
            raise NotFoundError("Report not found")
        
        report.resolve(resolver_id, notes)
        
        if action == 'resolve':
            # Применяем действия к контенту
            AdminService._handle_confirmed_report(report)
        
        return report
    
    @staticmethod
    def _handle_confirmed_report(report):
        """Обработка подтвержденной жалобы"""
        if report.report_reason in ['spam', 'fraud', 'inappropriate']:
            # Деактивируем контент
            AdminService._deactivate_reported_content(report.entity_id)
        
        elif report.report_reason == 'duplicate':
            # Отправляем на модерацию
            AdminService._send_to_moderation(report.entity_id, 'duplicate_check')
    
    @staticmethod
    def _deactivate_reported_content(entity_id):
        """Деактивация контента по жалобе"""
        try:
            from app.models.base import GlobalEntity
            
            entity = GlobalEntity.query.get(entity_id)
            if not entity:
                return
            
            if entity.entity_type == 'listing':
                listing = Listing.query.filter_by(entity_id=entity_id).first()
                if listing:
                    listing.soft_delete()
        except ImportError:
            listing = Listing.query.get(entity_id)
            if listing:
                listing.soft_delete()
    
    @staticmethod
    def _send_to_moderation(entity_id, reason):
        """Отправка контента на модерацию"""
        # Проверяем, нет ли уже в очереди
        existing = ModerationQueue.query.filter(
            ModerationQueue.entity_id == entity_id,
            ModerationQueue.is_active == True
        ).first()
        
        if existing:
            return existing
        
        moderation_item = ModerationQueue(
            entity_id=entity_id,
            user_id=1,  # Системный пользователь
            priority=1
        )
        moderation_item.save()
        
        return moderation_item
    
    @staticmethod
    def get_users(page=1, per_page=20, user_type=None, status=None, search=None):
        """
        Получение пользователей для администрирования
        
        Args:
            page: Номер страницы
            per_page: Элементов на странице
            user_type: Фильтр по типу пользователя
            status: Фильтр по статусу
            search: Поисковый запрос
            
        Returns:
            Пользователи с пагинацией
        """
        query = User.query
        
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        if status == 'active':
            query = query.filter(User.is_active == True)
        elif status == 'blocked':
            query = query.filter(User.is_active == False)
        
        if search:
            query = query.filter(
                or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.phone_number.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        query = query.order_by(desc(User.registration_date))
        
        return paginate_query(query, page, per_page)
    
    @staticmethod
    def perform_user_action(user_id, admin_id, action, reason=None, duration_days=None):
        """
        Выполнение действия с пользователем
        
        Args:
            user_id: ID пользователя
            admin_id: ID администратора
            action: Действие
            reason: Причина
            duration_days: Длительность (для временных блокировок)
            
        Returns:
            Результат действия
        """
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        admin = User.query.get(admin_id)
        if not admin or admin.user_type != 'admin':
            raise AuthorizationError("Admin access required")
        
        if action == 'block':
            user.soft_delete()
            # Деактивируем все объявления пользователя
            Listing.query.filter(Listing.user_id == user_id).update({
                'is_active': False
            })
            
        elif action == 'unblock':
            user.is_active = True
            user.save()
            
        elif action == 'promote':
            if user.user_type == 'regular':
                user.user_type = 'pro'
            elif user.user_type == 'pro':
                user.user_type = 'dealer'
            user.save()
            
        elif action == 'demote':
            if user.user_type == 'dealer':
                user.user_type = 'pro'
            elif user.user_type == 'pro':
                user.user_type = 'regular'
            user.save()
        
        # Логируем действие
        AdminService._log_admin_action(admin_id, user_id, action, reason)
        
        return {'action': action, 'user_id': user_id, 'success': True}
    
    @staticmethod
    def _log_admin_action(admin_id, target_user_id, action, reason):
        """Логирование административных действий"""
        # Здесь можно создать таблицу логов административных действий
        pass
    
    @staticmethod
    def get_system_health():
        """Получение состояния системы"""
        try:
            # Проверка БД
            db_status = db.session.execute('SELECT 1').fetchone() is not None
        except:
            db_status = False
        
        try:
            # Проверка Redis
            from app.extensions import cache
            cache.get('health_check')
            redis_status = True
        except:
            redis_status = False
        
        return {
            'database': db_status,
            'redis': redis_status,
            'timestamp': datetime.utcnow().isoformat()
        }