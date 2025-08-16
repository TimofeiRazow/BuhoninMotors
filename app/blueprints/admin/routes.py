# app/blueprints/admin/routes.py
from flask import request, jsonify, g
from app.blueprints.admin import bp
from app.blueprints.admin.services import AdminService
from app.blueprints.admin.schemas import (
    ModerationActionSchema, ReportContentSchema, ResolveReportSchema,
    UserActionSchema, AdminStatsSchema
)
from app.utils.decorators import (
    handle_errors, admin_required, validate_json, paginate, cache_response
)
from app.utils.pagination import create_pagination_response


@bp.route('/dashboard', methods=['GET'])
@handle_errors
@admin_required
@cache_response(timeout=300)
def get_dashboard():
    """Получение данных для дашборда"""
    stats = AdminService.get_dashboard_stats()
    
    return jsonify(
        data=stats,
        message="Dashboard data retrieved successfully"
    )


@bp.route('/moderation', methods=['GET'])
@handle_errors
@admin_required
@paginate()
def get_moderation_queue():
    """Получение очереди модерации"""
    status = request.args.get('status')
    priority = request.args.get('priority', type=int)
    
    pagination = AdminService.get_moderation_queue(
        page=g.pagination['page'],
        per_page=g.pagination['per_page'],
        status=status,
        priority=priority
    )
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/moderation/<int:moderation_id>', methods=['POST'])
@handle_errors
@validate_json(ModerationActionSchema)
@admin_required
def moderate_content(moderation_id):
    """Модерация контента"""
    data = g.validated_data
    
    result = AdminService.moderate_content(
        moderation_id=moderation_id,
        moderator_id=g.current_user.user_id,
        action=data['action'],
        reason=data.get('reason'),
        notes=data.get('notes')
    )
    
    return jsonify(
        data=result.to_dict(),
        message=f"Content {data['action']}d successfully"
    )


@bp.route('/reports', methods=['GET'])
@handle_errors
@admin_required
@paginate()
def get_reports():
    """Получение жалоб"""
    status = request.args.get('status')
    reason = request.args.get('reason')
    
    pagination = AdminService.get_reports(
        page=g.pagination['page'],
        per_page=g.pagination['per_page'],
        status=status,
        reason=reason
    )
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/reports', methods=['POST'])
@handle_errors
@validate_json(ReportContentSchema)
@admin_required  # В реальности это может быть auth_required
def report_content():
    """Создание жалобы на контент"""
    data = g.validated_data
    
    report = AdminService.report_content(
        reporter_id=g.current_user.user_id,
        entity_id=data['entity_id'],
        reason=data['report_reason'],
        description=data.get('description')
    )
    
    return jsonify(
        data=report.to_dict(),
        message="Content reported successfully",
        status_code=201
    )


@bp.route('/reports/<int:report_id>/resolve', methods=['POST'])
@handle_errors
@validate_json(ResolveReportSchema)
@admin_required
def resolve_report(report_id):
    """Разрешение жалобы"""
    data = g.validated_data
    
    report = AdminService.resolve_report(
        report_id=report_id,
        resolver_id=g.current_user.user_id,
        action=data['action'],
        notes=data.get('notes')
    )
    
    return jsonify(
        data=report.to_dict(),
        message="Report resolved successfully"
    )


@bp.route('/users', methods=['GET'])
@handle_errors
@admin_required
@paginate()
def get_users():
    """Получение пользователей для администрирования"""
    user_type = request.args.get('user_type')
    status = request.args.get('status')
    search = request.args.get('search')
    
    pagination = AdminService.get_users(
        page=g.pagination['page'],
        per_page=g.pagination['per_page'],
        user_type=user_type,
        status=status,
        search=search
    )
    
    response = create_pagination_response(pagination)
    
    return jsonify(response)


@bp.route('/users/<int:user_id>/action', methods=['POST'])
@handle_errors
@validate_json(UserActionSchema)
@admin_required
def perform_user_action(user_id):
    """Выполнение действия с пользователем"""
    data = g.validated_data
    
    result = AdminService.perform_user_action(
        user_id=user_id,
        admin_id=g.current_user.user_id,
        action=data['action'],
        reason=data.get('reason'),
        duration_days=data.get('duration_days')
    )
    
    return jsonify(
        data=result,
        message=f"User action '{data['action']}' performed successfully"
    )


@bp.route('/system/health', methods=['GET'])
@handle_errors
@admin_required
def get_system_health():
    """Получение состояния системы"""
    health = AdminService.get_system_health()
    
    return jsonify(
        data=health,
        message="System health retrieved successfully"
    )


@bp.route('/stats', methods=['GET'])
@handle_errors
@admin_required
@cache_response(timeout=600)
def get_admin_stats():
    """Получение расширенной административной статистики"""
    stats = AdminService.get_dashboard_stats()
    schema = AdminStatsSchema()
    
    return jsonify(
        data=schema.dump(stats),
        message="Admin statistics retrieved successfully"
    )