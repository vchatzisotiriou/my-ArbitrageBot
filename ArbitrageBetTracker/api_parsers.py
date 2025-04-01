import json
import re
from datetime import datetime
import streamlit as st

# Utility functions for data normalization
def normalize_team_name(name):
    """
    Normalize team names to help with matching between different bookmakers
    
    Args:
        name (str): Original team name
    
    Returns:
        str: Normalized team name
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove FC, United, etc.
    normalized = re.sub(r'\bfc\b|\bf\.c\.\b', '', normalized)
    normalized = re.sub(r'\bunited\b|\butd\b', '', normalized)
    normalized = re.sub(r'\bcity\b', '', normalized)
    
    # Remove special characters and extra whitespace
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def match_key(team1, team2):
    """
    Create a consistent key for a match regardless of team order
    
    Args:
        team1 (str): First team name
        team2 (str): Second team name
    
    Returns:
        str: Normalized match key
    """
    norm_team1 = normalize_team_name(team1)
    norm_team2 = normalize_team_name(team2)
    
    # Sort to ensure consistency regardless of order
    sorted_teams = sorted([norm_team1, norm_team2])
    
    return f"{sorted_teams[0]} vs {sorted_teams[1]}"

def parse_datetime(date_str, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Parse datetime string to a standard format
    
    Args:
        date_str (str): Input date string
        format_str (str): Expected format of input
    
    Returns:
        str: Datetime in standard format
    """
    try:
        dt = datetime.strptime(date_str, format_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        # Return original if parsing fails
        return date_str

def identify_sport_from_league(league):
    """
    Try to identify sport based on league name
    
    Args:
        league (str): League name
    
    Returns:
        str: Sport name
    """
    soccer_keywords = ['premier', 'league', 'liga', 'serie a', 'bundesliga', 'ligue 1', 'cup', 'champions']
    basketball_keywords = ['nba', 'basketball', 'euroleague', 'acb', 'basket']
    tennis_keywords = ['atp', 'wta', 'open', 'grand slam', 'tennis', 'wimbledon', 'us open']
    
    league_lower = league.lower()
    
    for kw in soccer_keywords:
        if kw in league_lower:
            return "Soccer"
    
    for kw in basketball_keywords:
        if kw in league_lower:
            return "Basketball"
    
    for kw in tennis_keywords:
        if kw in league_lower:
            return "Tennis"
    
    return "Other"

# Bet365 specific parser
def parse_bet365_odds(response_data):
    """
    Parse Bet365 API response to standardized format
    
    Args:
        response_data (dict): Bet365 API response
    
    Returns:
        list: List of standardized match dictionaries
    """
    if not response_data or "events" not in response_data:
        return []
    
    standardized_matches = []
    
    for event in response_data.get("events", []):
        try:
            # Extract match details
            match_name = event.get("name", "")
            match_id = event.get("id", "")
            sport = event.get("sport", {}).get("name", "")
            league = event.get("competition", {}).get("name", "")
            start_time = parse_datetime(event.get("startTime", ""))
            
            # Extract teams
            teams = match_name.split(" vs ")
            if len(teams) != 2:
                teams = match_name.split(" - ")
            
            if len(teams) == 2:
                home_team, away_team = teams
            else:
                # Handle special cases (e.g. tennis matches)
                home_team = match_name
                away_team = ""
            
            # Get market data
            markets = event.get("markets", [])
            outcomes = {}
            
            for market in markets:
                market_type = market.get("type", "")
                
                # Handle different market types
                if market_type == "1X2" or market_type == "Match Result":
                    for selection in market.get("selections", []):
                        name = selection.get("name", "")
                        price = float(selection.get("price", 0))
                        
                        if name == home_team or "1" in name:
                            outcomes["home"] = {"name": home_team, "odds": price}
                        elif name == away_team or "2" in name:
                            outcomes["away"] = {"name": away_team, "odds": price}
                        elif "Draw" in name or "X" in name:
                            outcomes["draw"] = {"name": "Draw", "odds": price}
                
                # Handle tennis and other 2-way markets
                elif market_type == "Match Winner" or market_type == "Winner":
                    for selection in market.get("selections", []):
                        name = selection.get("name", "")
                        price = float(selection.get("price", 0))
                        
                        if name == home_team:
                            outcomes["home"] = {"name": home_team, "odds": price}
                        elif name == away_team:
                            outcomes["away"] = {"name": away_team, "odds": price}
            
            # Skip matches without sufficient odds data
            if len(outcomes) < 2:
                continue
            
            normalized_match = {
                "id": match_id,
                "sport": sport,
                "league": league,
                "match": match_name,
                "normalized_match": match_key(home_team, away_team),
                "start_time": start_time,
                "outcomes": outcomes,
                "is_active": True,
                "bookmaker": "bet365"
            }
            
            standardized_matches.append(normalized_match)
        
        except Exception as e:
            st.error(f"Error parsing Bet365 event: {str(e)}")
            continue
    
    return standardized_matches

# Betfair specific parser
def parse_betfair_odds(response_data):
    """
    Parse Betfair API response to standardized format
    
    Args:
        response_data (list): Betfair API response
    
    Returns:
        list: List of standardized match dictionaries
    """
    if not response_data:
        return []
    
    standardized_matches = []
    
    try:
        # Betfair API returns a list of market books
        for market_book in response_data:
            # Extract market details
            market_id = market_book.get("marketId", "")
            market_name = market_book.get("marketName", "")
            event = market_book.get("event", {})
            
            match_name = event.get("name", "")
            start_time = parse_datetime(event.get("openDate", ""))
            
            # Fetch market definition from metadata
            market_def = market_book.get("marketDefinition", {})
            sport = market_def.get("sport", "")
            league = market_def.get("competition", "")
            
            # Extract teams from event name
            teams = match_name.split(" vs ")
            if len(teams) != 2:
                teams = match_name.split(" - ")
            
            if len(teams) == 2:
                home_team, away_team = teams
            else:
                # Handle special cases (e.g. tennis matches)
                home_team = match_name
                away_team = ""
            
            # Extract the odds for each runner
            outcomes = {}
            runners = market_book.get("runners", [])
            
            for runner in runners:
                runner_name = runner.get("runnerName", "")
                
                # Get the best available price
                best_price = 0
                available_prices = runner.get("ex", {}).get("availableToBack", [])
                
                if available_prices:
                    # Sort by price (highest first)
                    available_prices.sort(key=lambda x: x.get("price", 0), reverse=True)
                    best_price = available_prices[0].get("price", 0)
                
                # Map to outcome type
                if runner_name == home_team or "1" in runner_name:
                    outcomes["home"] = {"name": home_team, "odds": best_price}
                elif runner_name == away_team or "2" in runner_name:
                    outcomes["away"] = {"name": away_team, "odds": best_price}
                elif "Draw" in runner_name or "X" in runner_name:
                    outcomes["draw"] = {"name": "Draw", "odds": best_price}
            
            # Skip matches without sufficient odds data
            if len(outcomes) < 2:
                continue
            
            # Infer sport from competition name if not provided
            if not sport:
                sport = identify_sport_from_league(league)
            
            normalized_match = {
                "id": market_id,
                "sport": sport,
                "league": league,
                "match": match_name,
                "normalized_match": match_key(home_team, away_team),
                "start_time": start_time,
                "outcomes": outcomes,
                "is_active": True,
                "bookmaker": "betfair"
            }
            
            standardized_matches.append(normalized_match)
    
    except Exception as e:
        st.error(f"Error parsing Betfair data: {str(e)}")
    
    return standardized_matches

# Generic parser for similar API structures (Stoiximan, Netbet, Novibet)
def parse_generic_odds(response_data, bookmaker):
    """
    Parse generic API response to standardized format
    
    Args:
        response_data (dict): API response
        bookmaker (str): Bookmaker name
    
    Returns:
        list: List of standardized match dictionaries
    """
    if not response_data or "events" not in response_data:
        return []
    
    standardized_matches = []
    
    for event in response_data.get("events", []):
        try:
            # Extract match details
            match_name = event.get("name", "")
            match_id = event.get("id", "")
            sport = event.get("sport", {}).get("name", "")
            league = event.get("competition", {}).get("name", "")
            start_time = parse_datetime(event.get("startTime", ""))
            
            # Extract teams
            teams = match_name.split(" vs ")
            if len(teams) != 2:
                teams = match_name.split(" - ")
            
            if len(teams) == 2:
                home_team, away_team = teams
            else:
                # Handle special cases (e.g. tennis matches)
                home_team = match_name
                away_team = ""
            
            # Get market data
            markets = event.get("markets", [])
            outcomes = {}
            
            for market in markets:
                market_type = market.get("type", "")
                
                # Handle different market types
                if market_type == "1X2" or market_type == "Match Result":
                    for selection in market.get("selections", []):
                        name = selection.get("name", "")
                        price = float(selection.get("price", 0))
                        
                        if name == home_team or "Home" in name or "1" in name:
                            outcomes["home"] = {"name": home_team, "odds": price}
                        elif name == away_team or "Away" in name or "2" in name:
                            outcomes["away"] = {"name": away_team, "odds": price}
                        elif "Draw" in name or "X" in name:
                            outcomes["draw"] = {"name": "Draw", "odds": price}
                
                # Handle tennis and other 2-way markets
                elif market_type == "Match Winner" or market_type == "Winner":
                    for selection in market.get("selections", []):
                        name = selection.get("name", "")
                        price = float(selection.get("price", 0))
                        
                        if name == home_team:
                            outcomes["home"] = {"name": home_team, "odds": price}
                        elif name == away_team:
                            outcomes["away"] = {"name": away_team, "odds": price}
            
            # Skip matches without sufficient odds data
            if len(outcomes) < 2:
                continue
            
            normalized_match = {
                "id": match_id,
                "sport": sport,
                "league": league,
                "match": match_name,
                "normalized_match": match_key(home_team, away_team),
                "start_time": start_time,
                "outcomes": outcomes,
                "is_active": True,
                "bookmaker": bookmaker
            }
            
            standardized_matches.append(normalized_match)
        
        except Exception as e:
            st.error(f"Error parsing {bookmaker} event: {str(e)}")
            continue
    
    return standardized_matches

# Specific parser functions for each bookmaker
def parse_stoiximan_odds(response_data):
    return parse_generic_odds(response_data, "stoiximan")

def parse_casinoly_odds(response_data):
    return parse_generic_odds(response_data, "casinoly")

def parse_netbet_odds(response_data):
    return parse_generic_odds(response_data, "netbet")

def parse_novibet_odds(response_data):
    return parse_generic_odds(response_data, "novibet")

# Function to normalize all bookmaker responses
def normalize_all_responses(bookmaker_responses):
    """
    Normalize responses from all bookmakers
    
    Args:
        bookmaker_responses (dict): Dictionary of raw API responses by bookmaker
    
    Returns:
        dict: Dictionary of normalized match data by bookmaker
    """
    normalized_data = {}
    
    for bookmaker, response in bookmaker_responses.items():
        if bookmaker == "bet365":
            normalized_data[bookmaker] = parse_bet365_odds(response)
        elif bookmaker == "betfair":
            normalized_data[bookmaker] = parse_betfair_odds(response)
        elif bookmaker == "stoiximan":
            normalized_data[bookmaker] = parse_stoiximan_odds(response)
        elif bookmaker == "casinoly":
            normalized_data[bookmaker] = parse_casinoly_odds(response)
        elif bookmaker == "netbet":
            normalized_data[bookmaker] = parse_netbet_odds(response)
        elif bookmaker == "novibet":
            normalized_data[bookmaker] = parse_novibet_odds(response)
    
    return normalized_data