import requests
import time
import os
import json
from datetime import datetime
import streamlit as st

# Define base URLs and endpoints for different bookmakers
API_CONFIG = {
    "bet365": {
        "base_url": "https://api.bet365.com/v1",
        "endpoints": {
            "sports": "/sports",
            "events": "/events",
            "markets": "/markets",
            "odds": "/odds"
        },
        "requires_auth": True
    },
    "betfair": {
        "base_url": "https://api.betfair.com/exchange/betting/rest/v1.0",
        "endpoints": {
            "sports": "/listEventTypes",
            "events": "/listEvents",
            "markets": "/listMarketCatalogue",
            "odds": "/listMarketBook"
        },
        "requires_auth": True
    },
    "stoiximan": {
        "base_url": "https://api.stoiximan.gr/v1",
        "endpoints": {
            "sports": "/sports",
            "events": "/events",
            "markets": "/markets",
            "odds": "/odds"
        },
        "requires_auth": True
    },
    "casinoly": {
        "base_url": "https://api.casinoly.com/v1",
        "endpoints": {
            "sports": "/sports",
            "events": "/events",
            "markets": "/markets",
            "odds": "/odds"
        },
        "requires_auth": True
    },
    "netbet": {
        "base_url": "https://api.netbet.com/v1",
        "endpoints": {
            "sports": "/sports",
            "events": "/events",
            "markets": "/markets",
            "odds": "/odds"
        },
        "requires_auth": True
    },
    "novibet": {
        "base_url": "https://api.novibet.com/v1",
        "endpoints": {
            "sports": "/sports",
            "events": "/events",
            "markets": "/markets",
            "odds": "/odds"
        },
        "requires_auth": True
    }
}

# Initialize API keys
def get_api_keys():
    """Get API keys from environment variables or session state"""
    api_keys = {}
    
    for bookmaker in API_CONFIG.keys():
        env_key = f"{bookmaker.upper()}_API_KEY"
        if env_key in os.environ:
            api_keys[bookmaker] = os.environ[env_key]
        elif f"{bookmaker}_api_key" in st.session_state:
            api_keys[bookmaker] = st.session_state[f"{bookmaker}_api_key"]
    
    return api_keys

def api_key_exists(bookmaker):
    """Check if API key exists for a bookmaker"""
    env_key = f"{bookmaker.upper()}_API_KEY"
    return env_key in os.environ or f"{bookmaker}_api_key" in st.session_state

# Generic API request function
def make_api_request(bookmaker, endpoint, params=None, headers=None):
    """
    Make an API request to a bookmaker's API
    
    Args:
        bookmaker (str): Name of the bookmaker
        endpoint (str): API endpoint to request
        params (dict, optional): Query parameters
        headers (dict, optional): Request headers
    
    Returns:
        dict: API response as JSON
    """
    if bookmaker not in API_CONFIG:
        raise ValueError(f"Unsupported bookmaker: {bookmaker}")
    
    config = API_CONFIG[bookmaker]
    
    if config["requires_auth"]:
        api_keys = get_api_keys()
        if bookmaker not in api_keys:
            raise ValueError(f"API key required for {bookmaker}")
        
        if headers is None:
            headers = {}
        
        headers["Authorization"] = f"Bearer {api_keys[bookmaker]}"
    
    url = f"{config['base_url']}{endpoint}"
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return {"error": str(e)}

# Specific API functions for each bookmaker
def get_bet365_odds(sport=None, competition=None):
    """Get odds from Bet365 API"""
    params = {}
    if sport:
        params["sport"] = sport
    if competition:
        params["competition"] = competition
    
    try:
        return make_api_request("bet365", API_CONFIG["bet365"]["endpoints"]["odds"], params)
    except ValueError as e:
        st.warning(str(e))
        return None

def get_betfair_odds(event_type_id=None, market_id=None):
    """Get odds from Betfair API"""
    params = {}
    if event_type_id:
        params["eventTypeId"] = event_type_id
    if market_id:
        params["marketId"] = market_id
    
    try:
        return make_api_request("betfair", API_CONFIG["betfair"]["endpoints"]["odds"], params)
    except ValueError as e:
        st.warning(str(e))
        return None

def get_stoiximan_odds(sport=None, competition=None):
    """Get odds from Stoiximan API"""
    params = {}
    if sport:
        params["sport"] = sport
    if competition:
        params["competition"] = competition
    
    try:
        return make_api_request("stoiximan", API_CONFIG["stoiximan"]["endpoints"]["odds"], params)
    except ValueError as e:
        st.warning(str(e))
        return None

def get_casinoly_odds(sport=None, competition=None):
    """Get odds from Casinoly API"""
    params = {}
    if sport:
        params["sport"] = sport
    if competition:
        params["competition"] = competition
    
    try:
        return make_api_request("casinoly", API_CONFIG["casinoly"]["endpoints"]["odds"], params)
    except ValueError as e:
        st.warning(str(e))
        return None

def get_netbet_odds(sport=None, competition=None):
    """Get odds from Netbet API"""
    params = {}
    if sport:
        params["sport"] = sport
    if competition:
        params["competition"] = competition
    
    try:
        return make_api_request("netbet", API_CONFIG["netbet"]["endpoints"]["odds"], params)
    except ValueError as e:
        st.warning(str(e))
        return None

def get_novibet_odds(sport=None, competition=None):
    """Get odds from Novibet API"""
    params = {}
    if sport:
        params["sport"] = sport
    if competition:
        params["competition"] = competition
    
    try:
        return make_api_request("novibet", API_CONFIG["novibet"]["endpoints"]["odds"], params)
    except ValueError as e:
        st.warning(str(e))
        return None

# Unified odds fetching
def fetch_all_bookmaker_odds(sport=None, competition=None):
    """
    Fetch odds from all configured bookmakers
    
    Args:
        sport (str, optional): Sport to fetch odds for
        competition (str, optional): Competition to fetch odds for
    
    Returns:
        dict: Dictionary of bookmaker-specific odds data
    """
    all_odds = {}
    bookmakers = API_CONFIG.keys()
    
    for bookmaker in bookmakers:
        # Skip bookmakers without API keys
        if API_CONFIG[bookmaker]["requires_auth"] and not api_key_exists(bookmaker):
            continue
        
        # Use appropriate function based on bookmaker
        odds_data = None
        if bookmaker == "bet365":
            odds_data = get_bet365_odds(sport, competition)
        elif bookmaker == "betfair":
            odds_data = get_betfair_odds()
        elif bookmaker == "stoiximan":
            odds_data = get_stoiximan_odds(sport, competition)
        elif bookmaker == "casinoly":
            odds_data = get_casinoly_odds(sport, competition)
        elif bookmaker == "netbet":
            odds_data = get_netbet_odds(sport, competition)
        elif bookmaker == "novibet":
            odds_data = get_novibet_odds(sport, competition)
        
        if odds_data and "error" not in odds_data:
            all_odds[bookmaker] = odds_data
    
    return all_odds

# Response transformation functions to normalize data across different APIs
def normalize_bet365_response(response):
    """Transform Bet365 API response to standardized format"""
    if not response or "error" in response:
        return []
    
    normalized_matches = []
    # Implement transformation logic based on actual API response format
    
    return normalized_matches

def normalize_betfair_response(response):
    """Transform Betfair API response to standardized format"""
    if not response or "error" in response:
        return []
    
    normalized_matches = []
    # Implement transformation logic based on actual API response format
    
    return normalized_matches

# Add similar normalization functions for other bookmakers

def get_normalized_odds(use_real_apis=False):
    """
    Get odds data either from real APIs or simulated data
    
    Args:
        use_real_apis (bool): Whether to use real APIs or simulated data
    
    Returns:
        dict: Dictionary of bookmaker odds in standardized format
    """
    if not use_real_apis:
        # Return simulated data when API keys are not available
        from simple_app import generate_bookmaker_data
        return generate_bookmaker_data()
    
    # Fetch real odds from APIs
    all_odds = fetch_all_bookmaker_odds()
    
    # Transform responses to standardized format
    normalized_odds = {}
    
    for bookmaker, response in all_odds.items():
        if bookmaker == "bet365":
            normalized_odds[bookmaker] = normalize_bet365_response(response)
        elif bookmaker == "betfair":
            normalized_odds[bookmaker] = normalize_betfair_response(response)
        # Add other bookmakers
    
    # Fill in missing bookmakers with simulated data
    from simple_app import generate_bookmaker_data, BOOKMAKERS
    simulated_data = generate_bookmaker_data()
    
    for bookmaker in BOOKMAKERS:
        if bookmaker not in normalized_odds:
            normalized_odds[bookmaker] = simulated_data[bookmaker]
    
    return normalized_odds

# API key management
def display_api_key_form():
    """Display form for managing API keys"""
    st.subheader("API Key Management")
    
    st.markdown("""
    Enter your API keys for the bookmakers you want to integrate with.
    These keys will be stored securely in the session and not saved permanently.
    """)
    
    # Initialize session state for API keys if they don't exist
    for bookmaker in API_CONFIG.keys():
        key_name = f"{bookmaker}_api_key"
        if key_name not in st.session_state:
            st.session_state[key_name] = ""
    
    # Create columns for API key inputs
    col1, col2 = st.columns(2)
    
    bookmakers = list(API_CONFIG.keys())
    half = len(bookmakers) // 2
    
    with col1:
        for bookmaker in bookmakers[:half]:
            key_name = f"{bookmaker}_api_key"
            st.session_state[key_name] = st.text_input(
                f"{bookmaker.capitalize()} API Key",
                type="password",
                value=st.session_state[key_name]
            )
    
    with col2:
        for bookmaker in bookmakers[half:]:
            key_name = f"{bookmaker}_api_key"
            st.session_state[key_name] = st.text_input(
                f"{bookmaker.capitalize()} API Key",
                type="password",
                value=st.session_state[key_name]
            )
    
    # Add toggle for using real APIs vs simulated data
    if "use_real_apis" not in st.session_state:
        st.session_state.use_real_apis = False
    
    st.session_state.use_real_apis = st.toggle(
        "Use Real API Data (if available)",
        value=st.session_state.use_real_apis
    )
    
    if st.session_state.use_real_apis:
        # Check which bookmakers have API keys
        active_bookmakers = [b for b in API_CONFIG.keys() if api_key_exists(b)]
        
        if not active_bookmakers:
            st.warning("No API keys found. Add at least one API key to use real data.")
            st.session_state.use_real_apis = False
        else:
            st.success(f"Using real data from: {', '.join([b.capitalize() for b in active_bookmakers])}")
    else:
        st.info("Using simulated data for all bookmakers.")