# app/tasks/indexing.py
"""
Задачи для индексации и поиска
"""

from celery import Celery
from app.extensions import db
from app.models.listing import Listing
from sqlalchemy import text

celery = Celery('kolesa_indexing')


@celery.task
def update_search_vectors():
    """Обновление поисковых векторов для объявлений"""
    # Обновляем search_vector для всех активных объявлений
    query = text("""
        UPDATE listings 
        SET search_vector = to_tsvector('russian', COALESCE(title, '') || ' ' || COALESCE(description, ''))
        WHERE is_active = true AND search_vector IS NULL
    """)
    
    result = db.session.execute(query)
    db.session.commit()
    
    return {'updated_vectors': result.rowcount}


@celery.task
def reindex_listing(listing_id):
    """Переиндексация конкретного объявления"""
    listing = Listing.query.get(listing_id)
    if not listing:
        return {'error': 'Listing not found'}
    
    # Обновляем поисковый вектор
    search_text = f"{listing.title or ''} {listing.description or ''}"
    
    query = text("""
        UPDATE listings 
        SET search_vector = to_tsvector('russian', :search_text)
        WHERE listing_id = :listing_id
    """)
    
    db.session.execute(query, {
        'search_text': search_text,
        'listing_id': listing_id
    })
    db.session.commit()
    
    return {'listing_id': listing_id, 'reindexed': True}


@celery.task
def rebuild_search_index():
    """Полная переиндексация всех объявлений"""
    query = text("""
        UPDATE listings 
        SET search_vector = to_tsvector('russian', COALESCE(title, '') || ' ' || COALESCE(description, ''))
        WHERE is_active = true
    """)
    
    result = db.session.execute(query)
    db.session.commit()
    
    return {'reindexed_listings': result.rowcount}
