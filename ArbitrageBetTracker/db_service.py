import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from db_models import initialize_db, get_session, close_session, Bookmaker, Match, Odds, ArbitrageOpportunity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_service')

# Initialize database
initialize_db()

def get_or_create_bookmaker(name, url=None):
    """
    Get or create a bookmaker record
    
    Args:
        name (str): Name of the bookmaker
        url (str, optional): URL of the bookmaker website
    
    Returns:
        Bookmaker: The bookmaker record
    """
    session = get_session()
    try:
        bookmaker = session.query(Bookmaker).filter(func.lower(Bookmaker.name) == func.lower(name)).first()
        if not bookmaker:
            bookmaker = Bookmaker(name=name, url=url)
            session.add(bookmaker)
            session.commit()
            logger.info(f"Created new bookmaker: {name}")
        return bookmaker
    except Exception as e:
        session.rollback()
        logger.error(f"Error getting/creating bookmaker {name}: {str(e)}")
        raise
    finally:
        close_session(session)

def store_matches_and_odds(matches_data, bookmaker_name):
    """
    Store matches and odds data in the database
    
    Args:
        matches_data (list): List of match data dictionaries
        bookmaker_name (str): Name of the bookmaker
    
    Returns:
        int: Number of matches stored
    """
    session = get_session()
    count = 0
    try:
        # Get or create bookmaker
        bookmaker = get_or_create_bookmaker(bookmaker_name)
        
        for match_data in matches_data:
            # Check if match already exists for this bookmaker
            existing_match = session.query(Match).filter(
                Match.match_id == match_data["id"],
                Match.bookmaker_id == bookmaker.id
            ).first()
            
            # Extract and parse start_time
            start_time = None
            if "start_time" in match_data:
                try:
                    start_time = datetime.strptime(match_data["start_time"], "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid start_time format for match {match_data.get('match')}")
            
            if existing_match:
                # Update existing match
                existing_match.sport = match_data.get("sport")
                existing_match.league = match_data.get("league")
                existing_match.match_name = match_data.get("match")
                existing_match.normalized_match = match_data.get("normalized_match")
                existing_match.start_time = start_time
                existing_match.is_active = match_data.get("is_active", True)
                existing_match.updated_at = datetime.now()
                
                # Delete old odds
                session.query(Odds).filter(Odds.match_id == existing_match.id).delete()
                
                # Add new odds
                for outcome_type, outcome_data in match_data.get("outcomes", {}).items():
                    odds = Odds(
                        match_id=existing_match.id,
                        outcome_type=outcome_type,
                        outcome_name=outcome_data.get("name", ""),
                        odds_value=outcome_data.get("odds", 0.0)
                    )
                    session.add(odds)
                
            else:
                # Create new match
                new_match = Match(
                    match_id=match_data.get("id", ""),
                    bookmaker_id=bookmaker.id,
                    sport=match_data.get("sport"),
                    league=match_data.get("league"),
                    match_name=match_data.get("match"),
                    normalized_match=match_data.get("normalized_match"),
                    start_time=start_time,
                    is_active=match_data.get("is_active", True)
                )
                session.add(new_match)
                session.flush()  # Get the new match ID
                
                # Add odds
                for outcome_type, outcome_data in match_data.get("outcomes", {}).items():
                    odds = Odds(
                        match_id=new_match.id,
                        outcome_type=outcome_type,
                        outcome_name=outcome_data.get("name", ""),
                        odds_value=outcome_data.get("odds", 0.0)
                    )
                    session.add(odds)
            
            count += 1
        
        session.commit()
        logger.info(f"Stored {count} matches for {bookmaker_name}")
        return count
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing matches for {bookmaker_name}: {str(e)}")
        raise
    finally:
        close_session(session)

def get_all_matches_with_odds():
    """
    Get all active matches with their odds, grouped by bookmaker
    
    Returns:
        dict: Dictionary with bookmaker names as keys and lists of match data as values
    """
    session = get_session()
    try:
        result = {}
        
        # Get all active matches with their bookmakers
        matches = session.query(Match).filter(Match.is_active == True).all()
        
        for match in matches:
            bookmaker_name = match.bookmaker.name
            if bookmaker_name not in result:
                result[bookmaker_name] = []
            
            # Build match data dictionary
            match_data = {
                "id": match.match_id,
                "sport": match.sport,
                "league": match.league,
                "match": match.match_name,
                "normalized_match": match.normalized_match,
                "start_time": match.start_time.strftime("%Y-%m-%d %H:%M:%S") if match.start_time else None,
                "is_active": match.is_active,
                "bookmaker": bookmaker_name,
                "outcomes": {}
            }
            
            # Add odds data
            for odds in match.odds:
                match_data["outcomes"][odds.outcome_type] = {
                    "name": odds.outcome_name,
                    "odds": odds.odds_value
                }
            
            result[bookmaker_name].append(match_data)
        
        return result
    
    except Exception as e:
        logger.error(f"Error retrieving matches with odds: {str(e)}")
        return {}
    finally:
        close_session(session)

def store_arbitrage_opportunity(opportunity_data):
    """
    Store an arbitrage opportunity in the database
    
    Args:
        opportunity_data (dict): Arbitrage opportunity data
    
    Returns:
        ArbitrageOpportunity: The stored opportunity
    """
    session = get_session()
    try:
        # Extract and parse start_time and discovered_at
        start_time = None
        if "start_time" in opportunity_data:
            try:
                start_time = datetime.strptime(opportunity_data["start_time"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                logger.warning(f"Invalid start_time format for opportunity: {opportunity_data.get('match')}")
        
        discovered_at = None
        if "discovered_at" in opportunity_data:
            try:
                discovered_at = datetime.strptime(opportunity_data["discovered_at"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                discovered_at = datetime.now()
        else:
            discovered_at = datetime.now()
        
        # Check if similar opportunity already exists
        existing_opp = session.query(ArbitrageOpportunity).filter(
            ArbitrageOpportunity.normalized_match == opportunity_data.get("normalized_match"),
            ArbitrageOpportunity.is_active == True,
            func.abs(ArbitrageOpportunity.profit_percentage - opportunity_data.get("profit_percentage", 0)) < 0.1
        ).first()
        
        if existing_opp:
            # Update existing opportunity
            existing_opp.profit_percentage = opportunity_data.get("profit_percentage", 0)
            existing_opp.investment = opportunity_data.get("investment", 0)
            existing_opp.expected_return = opportunity_data.get("expected_return", 0)
            existing_opp.bets = opportunity_data.get("bets", [])
            existing_opp.updated_at = datetime.now()
            
            session.commit()
            logger.info(f"Updated arbitrage opportunity: {existing_opp.match_name}")
            return existing_opp
        else:
            # Create new opportunity
            new_opp = ArbitrageOpportunity(
                normalized_match=opportunity_data.get("normalized_match", ""),
                match_name=opportunity_data.get("match", ""),
                sport=opportunity_data.get("sport", ""),
                league=opportunity_data.get("league", ""),
                start_time=start_time,
                profit_percentage=opportunity_data.get("profit_percentage", 0),
                investment=opportunity_data.get("investment", 0),
                expected_return=opportunity_data.get("expected_return", 0),
                is_active=opportunity_data.get("is_active", True),
                discovered_at=discovered_at
            )
            # Set bets using the property setter
            new_opp.bets = opportunity_data.get("bets", [])
            
            session.add(new_opp)
            session.commit()
            logger.info(f"Created new arbitrage opportunity: {new_opp.match_name}")
            return new_opp
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing arbitrage opportunity: {str(e)}")
        raise
    finally:
        close_session(session)

def store_arbitrage_opportunities(opportunities):
    """
    Store multiple arbitrage opportunities in the database
    
    Args:
        opportunities (list): List of arbitrage opportunity data dictionaries
    
    Returns:
        int: Number of opportunities stored
    """
    count = 0
    for opp in opportunities:
        try:
            store_arbitrage_opportunity(opp)
            count += 1
        except Exception as e:
            logger.error(f"Error storing arbitrage opportunity {opp.get('match')}: {str(e)}")
    
    return count

def get_arbitrage_opportunities(active_only=True, limit=None):
    """
    Get arbitrage opportunities from the database
    
    Args:
        active_only (bool, optional): Whether to return only active opportunities. Defaults to True.
        limit (int, optional): Maximum number of opportunities to return. Defaults to None.
    
    Returns:
        list: List of arbitrage opportunity dictionaries
    """
    session = get_session()
    try:
        query = session.query(ArbitrageOpportunity)
        
        if active_only:
            query = query.filter(ArbitrageOpportunity.is_active == True)
        
        # Order by profit percentage (descending) and discovery time (newest first)
        query = query.order_by(ArbitrageOpportunity.profit_percentage.desc(), ArbitrageOpportunity.discovered_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        opportunities = query.all()
        
        # Convert to dictionaries
        result = []
        for opp in opportunities:
            opp_dict = {
                "id": opp.id,
                "match": opp.match_name,
                "normalized_match": opp.normalized_match,
                "sport": opp.sport,
                "league": opp.league,
                "start_time": opp.start_time.strftime("%Y-%m-%d %H:%M:%S") if opp.start_time else None,
                "profit_percentage": opp.profit_percentage,
                "investment": opp.investment,
                "expected_return": opp.expected_return,
                "bets": opp.bets,
                "is_active": opp.is_active,
                "discovered_at": opp.discovered_at.strftime("%Y-%m-%d %H:%M:%S") if opp.discovered_at else None
            }
            result.append(opp_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"Error retrieving arbitrage opportunities: {str(e)}")
        return []
    finally:
        close_session(session)

def mark_opportunity_inactive(opportunity_id):
    """
    Mark an arbitrage opportunity as inactive
    
    Args:
        opportunity_id (int): ID of the opportunity to mark inactive
    
    Returns:
        bool: True if successful, False otherwise
    """
    session = get_session()
    try:
        opportunity = session.query(ArbitrageOpportunity).filter(ArbitrageOpportunity.id == opportunity_id).first()
        if opportunity:
            opportunity.is_active = False
            session.commit()
            logger.info(f"Marked opportunity {opportunity_id} as inactive")
            return True
        else:
            logger.warning(f"Opportunity with ID {opportunity_id} not found")
            return False
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error marking opportunity {opportunity_id} as inactive: {str(e)}")
        return False
    finally:
        close_session(session)

def clear_old_data(max_age_hours=48):
    """
    Mark old matches and opportunities as inactive
    
    Args:
        max_age_hours (int, optional): Maximum age in hours to keep data active. Defaults to 48.
    
    Returns:
        tuple: (matches_count, opportunities_count) - Number of matches and opportunities marked inactive
    """
    session = get_session()
    try:
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Mark old matches as inactive
        matches_result = session.query(Match).filter(
            Match.is_active == True,
            Match.start_time < cutoff_time
        ).update({Match.is_active: False}, synchronize_session=False)
        
        # Mark old opportunities as inactive
        opps_result = session.query(ArbitrageOpportunity).filter(
            ArbitrageOpportunity.is_active == True,
            ArbitrageOpportunity.start_time < cutoff_time
        ).update({ArbitrageOpportunity.is_active: False}, synchronize_session=False)
        
        session.commit()
        logger.info(f"Marked {matches_result} matches and {opps_result} opportunities as inactive")
        return (matches_result, opps_result)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error clearing old data: {str(e)}")
        return (0, 0)
    finally:
        close_session(session)

# Run database initialization if this file is executed directly
if __name__ == "__main__":
    logger.info("Initializing database...")
    initialize_db()
    logger.info("Database initialized successfully")