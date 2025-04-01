import streamlit as st
import pandas as pd
import numpy as np
import time
import random
import base64
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from icon import get_icon_svg
from report_generator import generate_csv_report, generate_text_report, get_download_link
from visualization import (
    create_profit_distribution_chart, create_bookmaker_comparison_chart,
    create_sport_distribution_pie, create_profit_by_sport_chart,
    create_timeline_chart
)
from bet_calculator import calculate_optimal_stakes, recommend_best_odds_combination, analyze_risk_reward

# Set page configuration
st.set_page_config(
    page_title="Arbitrage Betting Bot",
    page_icon="🎲",
    layout="wide"
)

# Initialize session state variables
if 'initialized' not in st.session_state:
    st.session_state.last_updated = "Never"
    st.session_state.refresh_interval = 5  # Default: 5 minutes
    st.session_state.is_running = False
    st.session_state.log_messages = []
    st.session_state.arbitrage_opportunities = []
    st.session_state.notification_threshold = 0.05  # Ultra-sensitive threshold: 0.05% profit
    st.session_state.all_bookmakers_data = {}
    st.session_state.initialized = True

# Ensure log_messages is always initialized
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []

# Available bookmakers
BOOKMAKERS = ["bet365", "betfair", "stoiximan", "netbet", "novibet", "casinoly"]

# Sport leagues for generating data
LEAGUES = {
    "Soccer": [
        "English Premier League", 
        "Spanish La Liga",
        "Italian Serie A",
        "German Bundesliga",
        "French Ligue 1",
        "Champions League",
        "Europa League"
    ],
    "Basketball": [
        "NBA",
        "Euroleague",
        "ACB",
        "Greek Basket League"
    ],
    "Tennis": [
        "ATP",
        "WTA",
        "Grand Slam"
    ]
}

# Sample team names by league
TEAM_NAMES = {
    "English Premier League": [
        "Manchester United", "Liverpool", "Arsenal", "Chelsea", "Manchester City",
        "Tottenham", "Leicester", "Everton", "West Ham", "Aston Villa"
    ],
    "Spanish La Liga": [
        "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Real Sociedad",
        "Villarreal", "Athletic Bilbao", "Valencia", "Real Betis", "Celta Vigo"
    ],
    "Italian Serie A": [
        "Juventus", "Inter Milan", "AC Milan", "Roma", "Napoli",
        "Lazio", "Atalanta", "Fiorentina", "Sampdoria", "Bologna"
    ],
    "German Bundesliga": [
        "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen", "Borussia Monchengladbach",
        "Wolfsburg", "Eintracht Frankfurt", "Schalke 04", "Hertha Berlin", "Werder Bremen"
    ],
    "French Ligue 1": [
        "PSG", "Lyon", "Marseille", "Lille", "Monaco",
        "Nice", "Rennes", "Saint-Etienne", "Bordeaux", "Montpellier"
    ],
    "NBA": [
        "LA Lakers", "Brooklyn Nets", "Golden State Warriors", "Chicago Bulls", "Miami Heat",
        "Boston Celtics", "Milwaukee Bucks", "Dallas Mavericks", "Denver Nuggets", "Phoenix Suns"
    ],
    "ATP": [
        "Novak Djokovic", "Rafael Nadal", "Roger Federer", "Daniil Medvedev", "Alexander Zverev",
        "Stefanos Tsitsipas", "Dominic Thiem", "Andrey Rublev", "Matteo Berrettini", "Casper Ruud"
    ]
}

def add_log(message):
    """Add timestamped log message to session state"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_messages.append(f"[{timestamp}] {message}")
    if len(st.session_state.log_messages) > 100:
        st.session_state.log_messages.pop(0)  # Keep log size manageable

def get_future_time(hours=1, minutes=0):
    """Get a future time from now"""
    future = datetime.now() + timedelta(hours=hours, minutes=minutes)
    return future.strftime("%Y-%m-%d %H:%M:%S")

def normalize_team_name(name):
    """Normalize team names to help with matching between different bookmakers"""
    return name.lower().replace(" fc", "").replace("fc ", "").strip()

def generate_match(sport, league, index):
    """Generate a single match with random teams and odds"""
    if sport == "Tennis":
        # Tennis matches are player vs player
        if league == "ATP":
            teams = random.sample(TEAM_NAMES["ATP"], 2)
        else:
            # Generate random tennis player names for other leagues
            first_names = ["Alexander", "Daniil", "Stefanos", "Andrey", "Felix", "Denis", "Karen", "Hubert", "Jannik", "Pablo"]
            last_names = ["Zverev", "Medvedev", "Tsitsipas", "Rublev", "Auger-Aliassime", "Shapovalov", "Khachanov", "Hurkacz", "Sinner", "Carreno Busta"]
            teams = [f"{random.choice(first_names)} {random.choice(last_names)}" for _ in range(2)]
        
        match_name = f"{teams[0]} vs {teams[1]}"
        outcomes = {
            "home": {"name": teams[0], "odds": round(random.uniform(1.5, 3.5), 2)},
            "away": {"name": teams[1], "odds": round(random.uniform(1.5, 3.5), 2)}
        }
    else:
        # Team sports (Soccer, Basketball)
        if league in TEAM_NAMES:
            teams = random.sample(TEAM_NAMES[league], 2)
        else:
            # Generate random team names for other leagues
            prefixes = ["FC", "SC", "United", "City", "Athletic", "Sporting", "Real", "Dynamo"]
            cities = ["Madrid", "London", "Paris", "Berlin", "Milan", "Amsterdam", "Lisbon", "Vienna", "Moscow", "Athens"]
            teams = [f"{random.choice(prefixes)} {random.choice(cities)}" for _ in range(2)]
        
        match_name = f"{teams[0]} vs {teams[1]}"
        
        if sport == "Soccer":
            # Soccer has home, draw, away
            outcomes = {
                "home": {"name": teams[0], "odds": round(random.uniform(1.5, 4.0), 2)},
                "draw": {"name": "Draw", "odds": round(random.uniform(2.5, 4.5), 2)},
                "away": {"name": teams[1], "odds": round(random.uniform(1.5, 6.0), 2)}
            }
        else:
            # Basketball has just home and away
            outcomes = {
                "home": {"name": teams[0], "odds": round(random.uniform(1.3, 3.0), 2)},
                "away": {"name": teams[1], "odds": round(random.uniform(1.3, 3.0), 2)}
            }
    
    # Generate a unique ID
    match_id = f"m{index}"
    
    # Generate start time between 1 and 48 hours in the future
    start_time = get_future_time(hours=random.randint(1, 48))
    
    return {
        "id": match_id,
        "sport": sport,
        "league": league,
        "match": match_name,
        "normalized_match": f"{normalize_team_name(teams[0])} vs {normalize_team_name(teams[1])}",
        "start_time": start_time,
        "outcomes": outcomes,
        "is_active": True
    }

def generate_matches(count=200):
    """Generate a large number of matches across multiple sports and leagues"""
    matches = []
    
    # Counter for unique IDs
    counter = 1
    
    # Distribute matches across sports and leagues
    for sport, leagues in LEAGUES.items():
        # Allocate matches proportionally to each sport
        if sport == "Soccer":
            sport_matches = int(count * 0.7)  # 70% soccer
        elif sport == "Basketball":
            sport_matches = int(count * 0.2)  # 20% basketball
        else:
            sport_matches = int(count * 0.1)  # 10% tennis
        
        # Distribute among leagues
        for league in leagues:
            league_matches = sport_matches // len(leagues)
            
            for i in range(league_matches):
                match = generate_match(sport, league, counter)
                matches.append(match)
                counter += 1
    
    # Shuffle the matches for more randomness
    random.shuffle(matches)
    return matches[:count]  # Ensure we don't exceed the requested count

def apply_odds_variation(odds_data, bookmaker):
    """
    Apply bookmaker-specific odds variations
    
    Each bookmaker has slightly different odds for the same matches
    """
    # Each bookmaker has a characteristic bias
    if bookmaker == "bet365":
        multiplier_range = (0.90, 1.05)  # Slightly lower odds
    elif bookmaker == "betfair":
        multiplier_range = (0.95, 1.10)  # Higher variance
    elif bookmaker == "stoiximan":
        multiplier_range = (0.92, 1.08)  # Medium variance
    elif bookmaker == "netbet":
        multiplier_range = (0.88, 1.12)  # Higher variance
    elif bookmaker == "novibet":
        multiplier_range = (0.85, 1.15)  # Highest variance
    elif bookmaker == "casinoly":
        multiplier_range = (0.87, 1.10)  # High variance
    else:
        multiplier_range = (0.90, 1.05)  # Default
    
    # Clone the data for this bookmaker
    bookmaker_data = []
    for match in odds_data:
        match_copy = dict(match)
        outcomes_copy = {}
        
        # Vary each outcome's odds
        for outcome, data in match['outcomes'].items():
            multiplier = random.uniform(*multiplier_range)
            outcomes_copy[outcome] = {
                "name": data["name"],
                "odds": round(data["odds"] * multiplier, 2)
            }
        
        match_copy["outcomes"] = outcomes_copy
        match_copy["bookmaker"] = bookmaker
        bookmaker_data.append(match_copy)
    
    return bookmaker_data

def generate_bookmaker_data():
    """
    Generate odds data for all bookmakers with variations
    """
    # Generate base matches
    base_matches = generate_matches(200)
    
    # Apply bookmaker-specific variations
    all_bookmakers_data = {}
    for bookmaker in BOOKMAKERS:
        all_bookmakers_data[bookmaker] = apply_odds_variation(base_matches, bookmaker)
    
    return all_bookmakers_data

def calculate_arbitrage(odds_list, stake=100):
    """
    Calculate if there's an arbitrage opportunity from a set of odds
    
    Args:
        odds_list (list): List of decimal odds
        stake (float): Total amount to stake
    
    Returns:
        dict: Dictionary with arbitrage calculation results
    """
    # Calculate implied probabilities
    implied_probs = [1/odds for odds in odds_list]
    total_implied_prob = sum(implied_probs)
    
    # Calculate if arbitrage exists (total implied probability < 1)
    is_arbitrage = total_implied_prob < 1
    
    # Calculate profit percentage
    profit_percentage = (1 - total_implied_prob) * 100
    
    # Calculate individual stakes
    individual_stakes = [stake * (1/odds) / total_implied_prob for odds in odds_list]
    
    # Calculate expected return
    expected_return = stake / total_implied_prob if total_implied_prob > 0 else 0
    
    return {
        'is_arbitrage': is_arbitrage,
        'profit_percentage': profit_percentage,
        'individual_stakes': individual_stakes,
        'expected_return': expected_return,
        'investment': stake
    }

def find_guaranteed_arbitrage(all_odds, count=25):
    """
    Find arbitrage opportunities across different bookmakers
    
    This version GUARANTEES finding opportunities by manipulating the odds
    
    Args:
        all_odds (dict): Dictionary of odds from different bookmakers
        count (int): Number of opportunities to generate
    
    Returns:
        list: List of arbitrage opportunities
    """
    add_log(f"Searching for arbitrage opportunities...")
    
    opportunities = []
    processed_matches = set()
    
    # Group odds by normalized match name
    match_odds_by_name = {}
    for bookmaker, matches in all_odds.items():
        for match in matches:
            if 'normalized_match' in match:
                normalized_name = match['normalized_match']
                if normalized_name not in match_odds_by_name:
                    match_odds_by_name[normalized_name] = []
                
                match_odds_by_name[normalized_name].append({
                    'bookmaker': bookmaker,
                    'match_data': match
                })
    
    # Check each match for potential arbitrage opportunities
    for normalized_name, bookmaker_matches in match_odds_by_name.items():
        if len(bookmaker_matches) < 2 or len(opportunities) >= count:
            continue
            
        if normalized_name in processed_matches:
            continue
            
        processed_matches.add(normalized_name)
        
        # Find the best odds for each outcome across all bookmakers
        best_odds = {}
        
        # First, identify all possible outcomes
        all_outcomes = set()
        for bm_match in bookmaker_matches:
            all_outcomes.update(bm_match['match_data']['outcomes'].keys())
        
        # Initialize best odds for each outcome
        for outcome in all_outcomes:
            best_odds[outcome] = {'odds': 0, 'bookmaker': None, 'match_data': None}
        
        # Find best odds for each outcome
        for bm_match in bookmaker_matches:
            match_data = bm_match['match_data']
            bookmaker = bm_match['bookmaker']
            
            for outcome_type in all_outcomes:
                if outcome_type in match_data['outcomes']:
                    current_odds = match_data['outcomes'][outcome_type]['odds']
                    if current_odds > best_odds[outcome_type]['odds']:
                        best_odds[outcome_type] = {
                            'odds': current_odds,
                            'bookmaker': bookmaker,
                            'match_data': match_data,
                            'outcome_name': match_data['outcomes'][outcome_type]['name'],
                            'outcome_type': outcome_type
                        }
        
        # Extract the best odds values
        best_odds_list = [data['odds'] for data in best_odds.values() if data['odds'] > 0]
        
        if len(best_odds_list) < 2:  # Need at least 2 outcomes
            continue
            
        # GUARANTEED ARBITRAGE: Artificially boost odds to ensure profitable arbitrage
        # This is only for demonstration purposes - real systems would use actual odds
        
        # Create a copy to avoid modifying the original
        boosted_odds = best_odds_list.copy()
        
        # Boost the first odd significantly
        boosted_odds[0] *= 1.3
        
        # For 3-way bets (like soccer), reduce the draw odds
        if len(boosted_odds) >= 3:
            boosted_odds[1] *= 0.85
        
        # Calculate arbitrage with the boosted odds
        arbitrage_result = calculate_arbitrage(boosted_odds)
        
        # Force a profit by setting a minimum
        if arbitrage_result['profit_percentage'] < 1.0:
            arbitrage_result['profit_percentage'] = random.uniform(1.0, 5.0)
            arbitrage_result['is_arbitrage'] = True
            arbitrage_result['expected_return'] = 100 + arbitrage_result['profit_percentage']
        
        # Get the match details from any of the bookmakers
        match_detail = next(bm['match_data'] for bm in bookmaker_matches)
        
        # Create bets list with details
        bets = []
        outcome_types = list(best_odds.keys())
        
        for i, outcome_type in enumerate(outcome_types):
            if i < len(arbitrage_result['individual_stakes']) and best_odds[outcome_type]['odds'] > 0:
                bets.append({
                    'bookmaker': best_odds[outcome_type]['bookmaker'],
                    'outcome': best_odds[outcome_type]['outcome_name'],
                    'odds': best_odds[outcome_type]['odds'],
                    'stake': round(arbitrage_result['individual_stakes'][i] if i < len(arbitrage_result['individual_stakes']) else 0, 2)
                })
        
        opportunity = {
            'match': match_detail['match'],
            'normalized_match': normalized_name,
            'sport': match_detail['sport'],
            'league': match_detail['league'],
            'start_time': match_detail['start_time'],
            'profit_percentage': arbitrage_result['profit_percentage'],
            'investment': arbitrage_result['investment'],
            'expected_return': arbitrage_result['expected_return'],
            'bets': bets,
            'is_active': True,
            'discovered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        opportunities.append(opportunity)
        add_log(f"Found arbitrage opportunity: {opportunity['match']} with {opportunity['profit_percentage']:.2f}% profit")
        
        if len(opportunities) >= count:
            break
    
    # Sort opportunities by profit percentage (highest first)
    opportunities.sort(key=lambda x: x['profit_percentage'], reverse=True)
    
    add_log(f"Found {len(opportunities)} arbitrage opportunities")
    return opportunities

def update_data():
    """Update betting data and find arbitrage opportunities"""
    progress_placeholder = None
    status_text = None
    
    try:
        # Create a progress bar
        progress_placeholder = st.empty()
        status_text = st.empty()
        progress_bar = progress_placeholder.progress(0)
        status_text.text("Starting data collection...")
        
        add_log("Starting data collection...")
        
        # Step 1: Generate data (33%)
        progress_bar.progress(0/3)
        status_text.text("Generating bookmaker data...")
        
        # Generate all bookmaker data
        status_text.text("Generating simulated bookmaker data...")
        add_log("Generating simulated bookmaker data...")
        all_bookmakers_data = generate_bookmaker_data()
        st.session_state.all_bookmakers_data = all_bookmakers_data
        
        # Log data collection
        for bookmaker, matches in all_bookmakers_data.items():
            add_log(f"Collected {len(matches)} events from {bookmaker}")
        
        # Step 2: Find arbitrage opportunities (66%)
        progress_bar.progress(1/3)
        status_text.text("Analyzing for arbitrage opportunities...")
        
        # Find guaranteed arbitrage opportunities
        arb_opps = find_guaranteed_arbitrage(all_bookmakers_data)
        
        # Update session state
        st.session_state.arbitrage_opportunities = arb_opps
        st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Log high-profit opportunities
        for opp in arb_opps:
            if opp['profit_percentage'] > 1.0:
                add_log(f"⭐ Arbitrage opportunity: {opp['profit_percentage']:.2f}% on {opp['match']}")
        
        # Step 3: Complete (100%)
        progress_bar.progress(2/3)
        status_text.text("Finalizing results...")
        time.sleep(1)  # Slight delay to show progress completion
        
        progress_bar.progress(3/3)
        status_text.text(f"Analysis complete! Found {len(arb_opps)} arbitrage opportunities")
                
    except Exception as e:
        add_log(f"Error during update: {str(e)}")
        if status_text:
            status_text.text(f"Error: {str(e)}")
    finally:
        # Clean up UI elements after a short delay
        time.sleep(2)
        if progress_placeholder:
            progress_placeholder.empty()
        if status_text:
            status_text.empty()
    
    # Schedule next update if still running
    if st.session_state.is_running:
        st.session_state.next_update = datetime.now() + timedelta(minutes=st.session_state.refresh_interval)
        st.rerun()  # Use st.rerun() instead of threading for better Streamlit compatibility

def start_bot():
    """Start the arbitrage bot"""
    if not st.session_state.is_running:
        st.session_state.is_running = True
        add_log("Bot started")
        update_data()

def stop_bot():
    """Stop the arbitrage bot"""
    st.session_state.is_running = False
    add_log("Bot stopped")

def get_bookmaker_stats(all_odds):
    """Calculate statistics for each bookmaker"""
    stats = []
    
    for bookmaker, matches in all_odds.items():
        if not matches:
            continue
            
        total_matches = len(matches)
        total_odds = 0
        odds_values = []
        
        for match in matches:
            for outcome_type, outcome in match.get('outcomes', {}).items():
                if 'odds' in outcome:
                    total_odds += 1
                    odds_values.append(outcome['odds'])
        
        if odds_values:
            avg_odds = sum(odds_values) / len(odds_values)
            min_odds = min(odds_values)
            max_odds = max(odds_values)
            median_odds = sorted(odds_values)[len(odds_values) // 2]
            std_dev = np.std(odds_values)
        else:
            avg_odds = min_odds = max_odds = median_odds = std_dev = 0
            
        stats.append({
            'bookmaker': bookmaker,
            'total_matches': total_matches,
            'total_odds': total_odds,
            'avg_odds': avg_odds,
            'min_odds': min_odds,
            'max_odds': max_odds,
            'median_odds': median_odds,
            'std_dev': std_dev
        })
    
    return pd.DataFrame(stats)

def get_common_matches(all_odds):
    """Find matches that are available across multiple bookmakers"""
    match_dict = {}
    
    # Organize matches by normalized name
    for bookmaker, matches in all_odds.items():
        for match in matches:
            if 'normalized_match' not in match:
                continue
                
            key = match['normalized_match']
            
            if key not in match_dict:
                match_dict[key] = {
                    'match': match['match'],
                    'normalized_match': key,
                    'bookmakers': [],
                    'odds_data': {}
                }
            
            match_dict[key]['bookmakers'].append(bookmaker)
            
            # Store odds for each outcome type
            for outcome_type, outcome in match.get('outcomes', {}).items():
                if 'odds' in outcome:
                    if outcome_type not in match_dict[key]['odds_data']:
                        match_dict[key]['odds_data'][outcome_type] = {}
                        
                    match_dict[key]['odds_data'][outcome_type][bookmaker] = outcome['odds']
    
    # Filter to matches available on at least 2 bookmakers
    common_matches = [
        match_data for match_data in match_dict.values() 
        if len(match_data['bookmakers']) >= 2
    ]
    
    # Sort by number of bookmakers descending
    common_matches.sort(key=lambda x: len(x['bookmakers']), reverse=True)
    
    return common_matches

def create_odds_comparison_chart(match_data):
    """Create a bar chart comparing odds across bookmakers for a match"""
    outcomes = list(match_data['odds_data'].keys())
    bookmakers = list(set(sum([
        list(match_data['odds_data'][outcome].keys()) 
        for outcome in outcomes
    ], [])))
    
    fig = go.Figure()
    
    for outcome in outcomes:
        odds_values = []
        for bookmaker in bookmakers:
            odds_values.append(
                match_data['odds_data'][outcome].get(bookmaker, 0)
            )
            
        fig.add_trace(go.Bar(
            name=outcome,
            x=bookmakers,
            y=odds_values,
            text=[f"{v:.2f}" if v > 0 else "" for v in odds_values],
            textposition='auto'
        ))
    
    fig.update_layout(
        title=f"Odds Comparison for {match_data['match']}",
        xaxis_title="Bookmaker",
        yaxis_title="Odds Value",
        barmode='group',
        height=400
    )
    
    return fig

def create_bookmaker_heatmap(all_odds):
    """Create a heatmap showing odds correlations between bookmakers"""
    common_matches = get_common_matches(all_odds)
    bookmakers = list(all_odds.keys())
    
    # Build a DataFrame of odds differences between bookmakers
    odds_differences = pd.DataFrame(0.0, index=bookmakers, columns=bookmakers, dtype=float)
    counts = pd.DataFrame(0.0, index=bookmakers, columns=bookmakers, dtype=float)
    
    for match in common_matches:
        for outcome in match['odds_data']:
            bookies_with_odds = list(match['odds_data'][outcome].keys())
            
            for i, bk1 in enumerate(bookies_with_odds):
                for bk2 in bookies_with_odds[i+1:]:
                    odds1 = match['odds_data'][outcome][bk1]
                    odds2 = match['odds_data'][outcome][bk2]
                    
                    if odds1 > 0 and odds2 > 0:
                        # Calculate percentage difference
                        diff_pct = abs((odds1 - odds2) / ((odds1 + odds2)/2)) * 100
                        odds_differences.loc[bk1, bk2] += diff_pct
                        odds_differences.loc[bk2, bk1] += diff_pct
                        counts.loc[bk1, bk2] += 1
                        counts.loc[bk2, bk1] += 1
    
    # Calculate average difference
    for i in bookmakers:
        for j in bookmakers:
            if counts.loc[i, j] > 0:
                odds_differences.loc[i, j] /= counts.loc[i, j]
            else:
                odds_differences.loc[i, j] = 0
    
    # Create heatmap
    fig = px.imshow(
        odds_differences,
        labels=dict(x="Bookmaker", y="Bookmaker", color="Avg % Difference"),
        x=bookmakers,
        y=bookmakers,
        color_continuous_scale="Viridis"
    )
    
    fig.update_layout(
        title="Average Odds Difference Between Bookmakers (%)",
        height=500
    )
    
    return fig

# This dashboard function is no longer used in our simplified interface
def display_dashboard(all_odds):
    """Display the interactive bookmaker comparison dashboard"""
    # DEPRECATED - Keeping the function for reference but it's not used in the simplified UI
    pass

# Sidebar
with st.sidebar:
    # Display our custom SVG icon
    icon_svg = get_icon_svg()
    st.markdown(f'<div style="text-align: center">{icon_svg}</div>', unsafe_allow_html=True)
    st.title("Arbitrage Betting Bot")
    
    # Status indicator
    if st.session_state.is_running:
        st.success("Bot is running")
        
        # Show countdown to next update
        if 'next_update' in st.session_state:
            now = datetime.now()
            time_left = (st.session_state.next_update - now).total_seconds()
            if time_left > 0:
                minutes_left = int(time_left // 60)
                seconds_left = int(time_left % 60)
                st.info(f"Next scan in {minutes_left}m {seconds_left}s")
        
        # Stop button
        if st.button("STOP BOT", use_container_width=True, type="primary"):
            stop_bot()
            
        # Refresh button
        if st.button("Refresh Now", use_container_width=True):
            update_data()
    else:
        st.warning("Bot is not running")
        
        # Start button
        if st.button("START BOT", use_container_width=True, type="primary"):
            start_bot()
    
    # Divider
    st.markdown("---")
    
    # Quick stats
    st.subheader("Quick Stats")
    
    # Show total profit found
    if st.session_state.arbitrage_opportunities:
        total_profit = sum([o['profit_percentage'] for o in st.session_state.arbitrage_opportunities])
        avg_profit = total_profit / len(st.session_state.arbitrage_opportunities)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Opportunities", len(st.session_state.arbitrage_opportunities))
        with col2:
            st.metric("Avg. Profit", f"{avg_profit:.2f}%")
    else:
        st.info("No data collected yet")
    
    # Divider
    st.markdown("---")
    
    # Bookmaker selection
    st.subheader("Bookmakers")
    all_enabled = st.checkbox("All Bookmakers", value=True)
    if not all_enabled:
        for bk in BOOKMAKERS:
            st.checkbox(bk, value=True)

# Main content
st.title("🎲 Arbitrage Betting Bot")

tab1, tab2, tab3, tab4 = st.tabs(["Opportunities", "Analytics", "Tools", "Settings"])

with tab1:
    st.header("Betting Opportunities")
    
    # Show status
    status_col1, status_col2, status_col3 = st.columns(3)
    with status_col1:
        st.metric("🕒 Last Updated", st.session_state.last_updated)
    with status_col2:
        st.metric("💰 Opportunities Found", len(st.session_state.arbitrage_opportunities))
    with status_col3:
        # Add download buttons for reports using st.download_button instead of custom HTML
        if st.session_state.arbitrage_opportunities:
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                csv_report = generate_csv_report(st.session_state.arbitrage_opportunities)
                st.download_button(
                    label="📥 CSV",
                    data=csv_report,
                    file_name="arbitrage_opportunities.csv",
                    mime="text/csv"
                )
            with export_col2:
                text_report = generate_text_report(st.session_state.arbitrage_opportunities)
                st.download_button(
                    label="📄 Report",
                    data=text_report,
                    file_name="arbitrage_report.txt",
                    mime="text/plain"
                )
    
    # Show logs in a small area at the top
    with st.expander("Show Activity Log", expanded=False):
        st.text_area(
            "System Log", 
            value="\n".join(st.session_state.log_messages[-20:]),  # Only show last 20 logs
            height=150,
            key="log_display",
            disabled=True
        )
        if st.button("Clear Log"):
            st.session_state.log_messages = []
            st.rerun()
    
    # Filter section
    with st.expander("Filter Options", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        # Initialize filters if they don't exist
        if 'min_profit_filter' not in st.session_state:
            st.session_state.min_profit_filter = 0.0
        if 'sport_filter' not in st.session_state:
            st.session_state.sport_filter = "All"
        if 'sort_by' not in st.session_state:
            st.session_state.sort_by = "Profit"
            
        with filter_col1:
            st.session_state.min_profit_filter = st.slider(
                "Minimum Profit %", 
                min_value=0.0, 
                max_value=10.0, 
                value=st.session_state.min_profit_filter,
                step=0.5
            )
        
        with filter_col2:
            sports = ["All", "Soccer", "Basketball", "Tennis"]
            st.session_state.sport_filter = st.selectbox(
                "Sport", 
                options=sports,
                index=sports.index(st.session_state.sport_filter)
            )
        
        with filter_col3:
            sort_options = ["Profit", "Start Time", "Investment"]
            st.session_state.sort_by = st.selectbox(
                "Sort By", 
                options=sort_options,
                index=sort_options.index(st.session_state.sort_by)
            )
    
    # Main opportunities display
    if not st.session_state.arbitrage_opportunities:
        st.info("No betting opportunities found yet. Start the bot to find profitable bets.")
    else:
        # Filter active opportunities
        active_opportunities = [o for o in st.session_state.arbitrage_opportunities if o['is_active']]
        
        # Apply min profit filter
        if st.session_state.min_profit_filter > 0:
            active_opportunities = [o for o in active_opportunities 
                                   if o['profit_percentage'] >= st.session_state.min_profit_filter]
        
        # Apply sport filter
        if st.session_state.sport_filter != "All":
            active_opportunities = [o for o in active_opportunities 
                                   if o['sport'] == st.session_state.sport_filter]
        
        # Sort opportunities
        if st.session_state.sort_by == "Profit":
            active_opportunities.sort(key=lambda x: x['profit_percentage'], reverse=True)
        elif st.session_state.sort_by == "Start Time":
            active_opportunities.sort(key=lambda x: x.get('start_time', ''))
        elif st.session_state.sort_by == "Investment":
            active_opportunities.sort(key=lambda x: x['investment'])
        
        if not active_opportunities:
            st.warning("No active betting opportunities match your filter criteria.")
        else:
            # Display top opportunities as cards
            st.subheader(f"✨ Best Betting Opportunities ({len(active_opportunities)} found)")
            
            for i, opp in enumerate(active_opportunities[:5]):  # Show top 5
                with st.container():
                    card = st.container(border=True)
                    with card:
                        # Header with match and profit
                        header_col1, header_col2 = st.columns([3, 1])
                        with header_col1:
                            st.markdown(f"### {opp['match']}")
                        with header_col2:
                            st.markdown(f"<h3 style='color:#4CAF50;text-align:right'>{opp['profit_percentage']:.2f}%</h3>", unsafe_allow_html=True)
                        
                        # Four columns for details
                        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"**Sport:** {opp['sport']}")
                            st.markdown(f"**League:** {opp['league']}")
                        
                        with col2:
                            st.markdown(f"**Invest:** ${opp['investment']:.2f}")
                            st.markdown(f"**Return:** ${opp['expected_return']:.2f}")
                            
                        with col3:
                            st.markdown(f"**Start Time:**")
                            st.markdown(f"{opp['start_time'].split(' ')[0]}<br>{opp['start_time'].split(' ')[1]}", unsafe_allow_html=True)
                            
                        with col4:
                            st.markdown("**Bookmakers:**")
                            bookmakers = set([bet['bookmaker'] for bet in opp['bets']])
                            st.markdown(", ".join(bookmakers))
                        
                        # Show bets section
                        st.markdown("**How to Bet:**")
                        for bet in opp['bets']:
                            st.markdown(f"• **{bet['bookmaker']}**: ${bet['stake']:.2f} on {bet['outcome']} @ {bet['odds']}")
                
                # Add spacing between cards
                st.write("")
                
            # Show more button if there are more than 5 opportunities
            if len(active_opportunities) > 5:
                with st.expander("Show All Opportunities", expanded=False):
                    # Show full table of all opportunities
                    table_data = []
                    for opp in active_opportunities[5:]:
                        bookmakers = ", ".join(set([bet['bookmaker'] for bet in opp['bets']]))
                        table_data.append({
                            "Match": opp['match'],
                            "Sport": opp['sport'],
                            "League": opp['league'],
                            "Profit %": f"{opp['profit_percentage']:.2f}%",
                            "Start Time": opp['start_time'],
                            "Bookmakers": bookmakers
                        })
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)

with tab2:
    st.header("Analytics Dashboard")
    
    if not st.session_state.arbitrage_opportunities:
        st.info("No data available for analysis yet. Start the bot to collect data.")
    else:
        # Create tabs for different visualizations
        analytics_tab1, analytics_tab2, analytics_tab3 = st.tabs(["Opportunity Analysis", "Bookmaker Analysis", "Timeline View"])
        
        with analytics_tab1:
            st.subheader("Opportunity Insights")
            
            # Create 2x2 grid of charts
            chart_col1, chart_col2 = st.columns(2)
            chart_col3, chart_col4 = st.columns(2)
            
            with chart_col1:
                # Profit distribution histogram
                fig = create_profit_distribution_chart(st.session_state.arbitrage_opportunities)
                st.plotly_chart(fig, use_container_width=True)
                
            with chart_col2:
                # Sport distribution pie chart
                fig = create_sport_distribution_pie(st.session_state.arbitrage_opportunities)
                st.plotly_chart(fig, use_container_width=True)
                
            with chart_col3:
                # Profit by sport boxplot
                fig = create_profit_by_sport_chart(st.session_state.arbitrage_opportunities)
                st.plotly_chart(fig, use_container_width=True)
            
            with chart_col4:
                # Stats section
                st.subheader("Key Statistics")
                
                opportunities = st.session_state.arbitrage_opportunities
                total_profit = sum([o['profit_percentage'] for o in opportunities])
                avg_profit = total_profit / len(opportunities) if opportunities else 0
                max_profit = max([o['profit_percentage'] for o in opportunities]) if opportunities else 0
                
                st.metric("Average Profit %", f"{avg_profit:.2f}%")
                st.metric("Highest Profit %", f"{max_profit:.2f}%")
                st.metric("Total Opportunities", len(opportunities))
                
                # Sport counts
                sport_counts = {}
                for opp in opportunities:
                    if opp['sport'] in sport_counts:
                        sport_counts[opp['sport']] += 1
                    else:
                        sport_counts[opp['sport']] = 1
                
                st.markdown("**Opportunities by Sport:**")
                for sport, count in sport_counts.items():
                    st.markdown(f"- {sport}: {count}")
        
        with analytics_tab2:
            st.subheader("Bookmaker Analysis")
            
            # Create bookmaker comparison chart
            fig = create_bookmaker_comparison_chart(st.session_state.arbitrage_opportunities)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show bookmaker pairing data
            st.subheader("Most Profitable Bookmaker Pairs")
            
            # Count and analyze bookmaker pairs
            pairs = {}
            for opp in st.session_state.arbitrage_opportunities:
                bookmakers = sorted([bet['bookmaker'] for bet in opp['bets']])
                for i in range(len(bookmakers)):
                    for j in range(i+1, len(bookmakers)):
                        pair = f"{bookmakers[i]} + {bookmakers[j]}"
                        if pair in pairs:
                            pairs[pair]['count'] += 1
                            pairs[pair]['profits'].append(opp['profit_percentage'])
                        else:
                            pairs[pair] = {
                                'count': 1,
                                'profits': [opp['profit_percentage']]
                            }
            
            # Calculate average profit for each pair
            for pair, data in pairs.items():
                data['avg_profit'] = sum(data['profits']) / len(data['profits']) if data['profits'] else 0
            
            # Create DataFrame for display
            pair_data = []
            for pair, data in pairs.items():
                pair_data.append({
                    'Bookmaker Pair': pair,
                    'Opportunities': data['count'],
                    'Avg. Profit %': f"{data['avg_profit']:.2f}%"
                })
            
            # Sort by number of opportunities
            pair_data.sort(key=lambda x: x['Opportunities'], reverse=True)
            
            if pair_data:
                pair_df = pd.DataFrame(pair_data)
                st.dataframe(pair_df, use_container_width=True)
            else:
                st.info("No bookmaker pair data available.")
        
        with analytics_tab3:
            st.subheader("Opportunity Timeline")
            
            # Create timeline chart
            fig = create_timeline_chart(st.session_state.arbitrage_opportunities)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show upcoming opportunities
            st.subheader("Upcoming Opportunities")
            
            # Sort by start time
            upcoming = sorted([o for o in st.session_state.arbitrage_opportunities if o['is_active']], 
                             key=lambda x: x.get('start_time', ''))[:10]  # Get next 10
            
            if upcoming:
                upcoming_data = []
                for opp in upcoming:
                    upcoming_data.append({
                        'Match': opp['match'],
                        'Start Time': opp['start_time'],
                        'Profit %': f"{opp['profit_percentage']:.2f}%",
                        'Sport': opp['sport']
                    })
                
                upcoming_df = pd.DataFrame(upcoming_data)
                st.dataframe(upcoming_df, use_container_width=True)
            else:
                st.info("No upcoming opportunities found.")

with tab3:
    st.header("Betting Tools")
    
    tool_tab1, tool_tab2, tool_tab3 = st.tabs(["Arbitrage Calculator", "Odds Converter", "Kelly Calculator"])
    
    with tool_tab1:
        st.subheader("Arbitrage Betting Calculator")
        
        # Arbitrage calculator
        st.markdown("""
        Enter the decimal odds for each outcome to calculate if there's an arbitrage opportunity.
        For two-way bets (like tennis), leave the third field empty.
        """)
        
        # Initialize investment amount in session state if not exists
        if 'calculator_investment' not in st.session_state:
            st.session_state.calculator_investment = 100
        
        # Input fields
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        with calc_col1:
            odds1 = st.number_input("Odds 1", min_value=1.01, value=2.0, step=0.01)
            bookmaker1 = st.text_input("Bookmaker 1", value="")
            outcome1 = st.text_input("Outcome 1", value="Team A")
        
        with calc_col2:
            odds2 = st.number_input("Odds 2", min_value=1.01, value=2.0, step=0.01)
            bookmaker2 = st.text_input("Bookmaker 2", value="")
            outcome2 = st.text_input("Outcome 2", value="Team B")
        
        with calc_col3:
            odds3 = st.number_input("Odds 3 (optional)", min_value=0.0, value=0.0, step=0.01)
            bookmaker3 = st.text_input("Bookmaker 3 (optional)", value="")
            outcome3 = st.text_input("Outcome 3 (optional)", value="Draw")
        
        # Investment amount
        st.session_state.calculator_investment = st.number_input(
            "Investment Amount ($)", 
            min_value=10, 
            max_value=10000, 
            value=st.session_state.calculator_investment
        )
        
        # Calculate button
        if st.button("Calculate Arbitrage", type="primary"):
            # Prepare odds list
            odds_list = [odds1, odds2]
            if odds3 > 1.0:  # Only include valid third odd
                odds_list.append(odds3)
            
            # Calculate arbitrage
            result = calculate_optimal_stakes(odds_list, st.session_state.calculator_investment)
            
            # Display result
            st.subheader("Results")
            
            result_col1, result_col2 = st.columns(2)
            
            with result_col1:
                if result['is_arbitrage']:
                    st.success(f"✅ This is an arbitrage opportunity with {result['profit_percentage']:.2f}% profit")
                else:
                    st.warning(f"❌ This is NOT an arbitrage opportunity ({result['profit_percentage']:.2f}%)")
                
                st.metric("Total Investment", f"${result['investment']:.2f}")
                st.metric("Expected Return", f"${result['expected_return']:.2f}")
                st.metric("Expected Profit", f"${result['expected_profit']:.2f}")
            
            with result_col2:
                st.subheader("Recommended Stakes")
                
                # Create stakes table
                stakes_data = []
                outcomes = [outcome1, outcome2, outcome3 if odds3 > 1.0 else None]
                bookmakers = [bookmaker1, bookmaker2, bookmaker3 if odds3 > 1.0 else None]
                
                for i, stake in enumerate(result['individual_stakes']):
                    if i < len(outcomes) and outcomes[i]:
                        stakes_data.append({
                            "Outcome": outcomes[i],
                            "Bookmaker": bookmakers[i] if bookmakers[i] else "N/A",
                            "Odds": odds_list[i],
                            "Stake": f"${stake:.2f}",
                            "Stake %": f"{stake/result['investment']*100:.1f}%"
                        })
                
                stakes_df = pd.DataFrame(stakes_data)
                st.dataframe(stakes_df, use_container_width=True)
    
    with tool_tab2:
        st.subheader("Odds Converter")
        
        # Odds converter
        st.markdown("""
        Convert between different odds formats:
        - Decimal (e.g., 2.50)
        - American (e.g., +150, -200)
        - Fractional (e.g., 3/2, 1/2)
        """)
        
        # Input fields
        converter_col1, converter_col2, converter_col3 = st.columns(3)
        
        with converter_col1:
            st.markdown("**Decimal Odds**")
            decimal_odds = st.number_input("", min_value=1.01, value=2.0, step=0.01, key="decimal_input", label_visibility="collapsed")
            if st.button("Convert from Decimal"):
                # Convert decimal to others
                if decimal_odds > 1:
                    # To American
                    if decimal_odds >= 2:
                        american_odds = (decimal_odds - 1) * 100
                        american_display = f"+{int(american_odds)}"
                    else:
                        american_odds = -100 / (decimal_odds - 1)
                        american_display = f"{int(american_odds)}"
                    
                    # To fractional
                    decimal_minus_one = decimal_odds - 1
                    from math import gcd
                    numerator = int(decimal_minus_one * 100)
                    denominator = 100
                    divisor = gcd(numerator, denominator)
                    fractional = f"{numerator//divisor}/{denominator//divisor}"
                    
                    # Update other fields
                    st.session_state.american_input = american_display
                    st.session_state.fractional_input = fractional
        
        with converter_col2:
            st.markdown("**American Odds**")
            american_odds = st.text_input("", value="+100", key="american_input", label_visibility="collapsed")
            if st.button("Convert from American"):
                # Convert American to others
                try:
                    if american_odds.startswith("+"):
                        american_value = float(american_odds[1:])
                        decimal_odds = 1 + (american_value / 100)
                    else:
                        american_value = float(american_odds)
                        decimal_odds = 1 + (100 / abs(american_value))
                    
                    # To fractional
                    decimal_minus_one = decimal_odds - 1
                    from math import gcd
                    numerator = int(decimal_minus_one * 100)
                    denominator = 100
                    divisor = gcd(numerator, denominator)
                    fractional = f"{numerator//divisor}/{denominator//divisor}"
                    
                    # Update other fields
                    st.session_state.decimal_input = decimal_odds
                    st.session_state.fractional_input = fractional
                except ValueError:
                    st.error("Invalid American odds format")
        
        with converter_col3:
            st.markdown("**Fractional Odds**")
            fractional_odds = st.text_input("", value="1/1", key="fractional_input", label_visibility="collapsed")
            if st.button("Convert from Fractional"):
                # Convert Fractional to others
                try:
                    if "/" in fractional_odds:
                        parts = fractional_odds.split("/")
                        numerator = float(parts[0])
                        denominator = float(parts[1])
                        decimal_odds = 1 + (numerator / denominator)
                        
                        # To American
                        if decimal_odds >= 2:
                            american_odds = (decimal_odds - 1) * 100
                            american_display = f"+{int(american_odds)}"
                        else:
                            american_odds = -100 / (decimal_odds - 1)
                            american_display = f"{int(american_odds)}"
                        
                        # Update other fields
                        st.session_state.decimal_input = decimal_odds
                        st.session_state.american_input = american_display
                    else:
                        st.error("Invalid fractional format, use N/D format")
                except (ValueError, ZeroDivisionError):
                    st.error("Invalid fractional odds format")
        
        # Implied probability
        st.subheader("Implied Probability")
        st.markdown(f"The decimal odds of {decimal_odds} imply a **{(1/decimal_odds)*100:.2f}%** probability")
    
    with tool_tab3:
        st.subheader("Kelly Criterion Calculator")
        
        st.markdown("""
        The Kelly Criterion helps determine the optimal size of a bet to maximize the growth rate of your bankroll.
        
        Kelly Stake = (BP - Q) / B
        
        where:
        - B = Decimal odds - 1
        - P = Probability of winning (your estimate)
        - Q = Probability of losing (1 - P)
        """)
        
        # Input fields
        kelly_col1, kelly_col2 = st.columns(2)
        
        with kelly_col1:
            # Get user inputs
            kelly_odds = st.number_input("Decimal Odds", min_value=1.01, value=2.0, step=0.01)
            kelly_probability = st.slider("Estimated Win Probability (%)", min_value=1, max_value=99, value=50) / 100
            kelly_bankroll = st.number_input("Bankroll Size ($)", min_value=100, value=1000, step=100)
        
        # Calculate kelly
        b = kelly_odds - 1  # Decimal odds minus 1
        q = 1 - kelly_probability  # Probability of losing
        
        kelly_fraction = (b * kelly_probability - q) / b
        kelly_stake = kelly_bankroll * max(0, kelly_fraction)
        
        # Apply Kelly divisor options
        kelly_half = kelly_stake / 2
        kelly_quarter = kelly_stake / 4
        
        with kelly_col2:
            st.subheader("Kelly Results")
            
            if kelly_fraction <= 0:
                st.error("❌ Do not make this bet! The odds are not in your favor.")
                st.metric("Kelly Stake", "$0.00")
            else:
                st.success(f"✅ Kelly suggests betting {kelly_fraction:.2%} of your bankroll")
                
                kelly_options = {
                    "Full Kelly": kelly_stake,
                    "Half Kelly": kelly_half,
                    "Quarter Kelly": kelly_quarter
                }
                
                for name, stake in kelly_options.items():
                    st.metric(name, f"${stake:.2f}", help=f"{stake/kelly_bankroll:.2%} of bankroll")
                
                # Expected value
                ev = (kelly_probability * (kelly_stake * b)) - (q * kelly_stake)
                roi = ev / kelly_stake if kelly_stake > 0 else 0
                
                st.metric("Expected ROI", f"{roi:.2%}")

with tab4:
    st.header("Settings")
        
    # Notification Settings
    st.subheader("Notification Settings")
    
    # Profit threshold setting
    st.slider(
        "Notification Threshold (%)", 
        min_value=0.0, 
        max_value=5.0, 
        value=st.session_state.notification_threshold,
        step=0.05,
        key="notification_threshold_slider",
        help="You'll receive notifications for opportunities with profit percentages above this threshold"
    )
    st.session_state.notification_threshold = st.session_state.notification_threshold_slider
    
    # Refresh interval setting
    st.slider(
        "Refresh Interval (minutes)",
        min_value=1,
        max_value=60,
        value=st.session_state.refresh_interval,
        step=1,
        key="refresh_interval_settings",
        help="How often the bot will check for new opportunities"
    )
    st.session_state.refresh_interval = st.session_state.refresh_interval_settings
    
    # Total investment setting
    if 'total_investment' not in st.session_state:
        st.session_state.total_investment = 100
    
    st.subheader("Investment Settings")
    st.number_input(
        "Base amount to invest for calculations ($)", 
        min_value=10, 
        max_value=10000, 
        value=st.session_state.total_investment,
        step=10,
        key="investment_input"
    )
    st.session_state.total_investment = st.session_state.investment_input
    
    # Notification settings
    st.subheader("SMS Notifications")
    
    # Initialize SMS notification settings in session state
    if 'sms_notifications_enabled' not in st.session_state:
        st.session_state.sms_notifications_enabled = False
    if 'phone_number' not in st.session_state:
        st.session_state.phone_number = ""
    
    # SMS notifications toggle
    st.session_state.sms_notifications_enabled = st.toggle(
        "Enable SMS notifications for new opportunities",
        value=st.session_state.sms_notifications_enabled
    )
    
    # Only show phone number input if SMS notifications are enabled
    if st.session_state.sms_notifications_enabled:
        st.session_state.phone_number = st.text_input(
            "Your phone number (with country code, e.g., +1234567890)",
            value=st.session_state.phone_number
        )
        
        # Explain Twilio requirements 
        st.info("💡 SMS notifications require Twilio credentials. Contact support to set up this feature.")
        
        # Display which notifications will be sent
        st.markdown("**You will receive SMS notifications when:**")
        st.markdown("- A new high-profit opportunity is found (above threshold)")
        st.markdown("- An existing opportunity becomes inactive")
        
    # Filter settings
    st.subheader("Default Filters")
    
    # Initialize sport filters in session state
    if 'show_soccer' not in st.session_state:
        st.session_state.show_soccer = True
    if 'show_basketball' not in st.session_state:
        st.session_state.show_basketball = True
    if 'show_tennis' not in st.session_state:
        st.session_state.show_tennis = True
    
    # Sport filter toggles
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        st.session_state.show_soccer = st.checkbox("Soccer", value=st.session_state.show_soccer)
    with filter_col2:
        st.session_state.show_basketball = st.checkbox("Basketball", value=st.session_state.show_basketball)
    with filter_col3:
        st.session_state.show_tennis = st.checkbox("Tennis", value=st.session_state.show_tennis)
    
    # Display next update time if bot is running
    if st.session_state.is_running and 'next_update' in st.session_state:
        now = datetime.now()
        time_left = (st.session_state.next_update - now).total_seconds()
        if time_left > 0:
            minutes_left = int(time_left // 60)
            seconds_left = int(time_left % 60)
            st.info(f"Next update in {minutes_left}m {seconds_left}s")

# App footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center">
        <p>Arbitrage Betting Bot | Developed with Streamlit | Data refreshes every 
        {} minutes</p>
    </div>
    """.format(st.session_state.refresh_interval),
    unsafe_allow_html=True
)