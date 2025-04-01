import json
from datetime import datetime, timedelta
import logging
import db_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data_store')

# Cache for recent queries
odds_cache = {}
opportunities_cache = []
last_cache_update = datetime.now() - timedelta(minutes=10)  # Initialize to force update on first query

def update_odds(matches, bookmaker):
    """
    Update the database with new odds data
    
    Args:
        matches (list): List of match data with odds
        bookmaker (str): Name of the bookmaker
    """
    global odds_cache, last_cache_update
    
    try:
        # Store matches in the database
        db_service.store_matches_and_odds(matches, bookmaker)
        
        # Invalidate the cache
        odds_cache = {}
        last_cache_update = datetime.now() - timedelta(minutes=10)
        
        logger.info(f"Updated odds for bookmaker {bookmaker}: {len(matches)} matches")
    except Exception as e:
        logger.error(f"Error updating odds for {bookmaker}: {str(e)}")

def get_odds(bookmaker):
    """
    Get odds data for a specific bookmaker
    
    Args:
        bookmaker (str): Name of the bookmaker
    
    Returns:
        list: List of match data with odds
    """
    return get_all_odds().get(bookmaker, [])

def get_all_odds():
    """
    Get all odds data
    
    Returns:
        dict: Dictionary of bookmakers with their match data
    """
    global odds_cache, last_cache_update
    
    # Check if cache is still valid (less than 1 minute old)
    if odds_cache and (datetime.now() - last_cache_update).total_seconds() < 60:
        return odds_cache
    
    try:
        # Get fresh data from database
        odds_cache = db_service.get_all_matches_with_odds()
        last_cache_update = datetime.now()
        return odds_cache
    except Exception as e:
        logger.error(f"Error getting odds data: {str(e)}")
        return odds_cache if odds_cache else {}

def add_arbitrage_opportunity(opportunity):
    """
    Add a new arbitrage opportunity to the database
    
    Args:
        opportunity (dict): Arbitrage opportunity data
    """
    global opportunities_cache, last_cache_update
    
    try:
        db_service.store_arbitrage_opportunity(opportunity)
        
        # Invalidate the cache
        opportunities_cache = []
        last_cache_update = datetime.now() - timedelta(minutes=10)
        
        logger.info(f"Added new arbitrage opportunity: {opportunity['match']}")
    except Exception as e:
        logger.error(f"Error adding arbitrage opportunity: {str(e)}")

def update_arbitrage_opportunities(opportunities):
    """
    Update the arbitrage opportunities in the database
    
    Args:
        opportunities (list): New list of arbitrage opportunities
    """
    global opportunities_cache, last_cache_update
    
    try:
        count = db_service.store_arbitrage_opportunities(opportunities)
        
        # Invalidate the cache
        opportunities_cache = []
        last_cache_update = datetime.now() - timedelta(minutes=10)
        
        logger.info(f"Updated arbitrage opportunities: {count} total")
    except Exception as e:
        logger.error(f"Error updating arbitrage opportunities: {str(e)}")

def get_arbitrage_opportunities(active_only=True):
    """
    Get arbitrage opportunities from the database
    
    Args:
        active_only (bool): If True, return only active opportunities
    
    Returns:
        list: List of arbitrage opportunities
    """
    global opportunities_cache, last_cache_update
    
    # Check if cache is still valid (less than 1 minute old)
    if opportunities_cache and (datetime.now() - last_cache_update).total_seconds() < 60:
        if active_only:
            return [opp for opp in opportunities_cache if opp.get('is_active', False)]
        return opportunities_cache
    
    try:
        # Get fresh data from database
        opportunities_cache = db_service.get_arbitrage_opportunities(active_only=active_only)
        last_cache_update = datetime.now()
        return opportunities_cache
    except Exception as e:
        logger.error(f"Error getting arbitrage opportunities: {str(e)}")
        return [] if not opportunities_cache else opportunities_cache

def mark_opportunity_inactive(opportunity_id):
    """
    Mark an opportunity as inactive in the database
    
    Args:
        opportunity_id (int): ID of the opportunity to mark
    """
    global opportunities_cache, last_cache_update
    
    try:
        success = db_service.mark_opportunity_inactive(opportunity_id)
        
        # Invalidate the cache
        opportunities_cache = []
        last_cache_update = datetime.now() - timedelta(minutes=10)
        
        if success:
            logger.info(f"Marked opportunity {opportunity_id} as inactive")
        else:
            logger.warning(f"Failed to mark opportunity {opportunity_id} as inactive")
    except Exception as e:
        logger.error(f"Error marking opportunity inactive: {str(e)}")

def clear_old_data(max_age_hours=24):
    """
    Clear old data from the database
    
    Args:
        max_age_hours (int): Maximum age in hours to keep data active
    """
    global odds_cache, opportunities_cache, last_cache_update
    
    try:
        # Clear old data in the database
        matches_count, opps_count = db_service.clear_old_data(max_age_hours)
        
        # Invalidate the cache
        odds_cache = {}
        opportunities_cache = []
        last_cache_update = datetime.now() - timedelta(minutes=10)
        
        logger.info(f"Marked {matches_count} matches and {opps_count} opportunities as inactive (older than {max_age_hours} hours)")
    except Exception as e:
        logger.error(f"Error clearing old data: {str(e)}")
        
# Initialize the database on import
db_service.initialize_db()
