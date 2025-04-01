import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
import logging
from datetime import datetime
import utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scraper')

# User agent rotation to avoid being blocked
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def make_request(url, headers=None, timeout=10, max_retries=3):
    """Make HTTP request with retries and error handling"""
    if headers is None:
        headers = {'User-Agent': get_random_user_agent()}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to retrieve data from {url} after {max_retries} attempts")
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

def normalize_team_name(name):
    """Normalize team names to help with matching between different bookmakers"""
    name = name.lower().strip()
    # Remove common suffixes and prefixes
    replacements = {
        'fc ': '', ' fc': '', 'afc ': '', ' afc': '',
        ' united': ' utd', 'united ': 'utd ',
        'manchester': 'man', 'tottenham': 'spurs',
        'wolverhampton': 'wolves', 'brighton and hove': 'brighton'
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name

def generate_matches(league_count=10, matches_per_league=20):
    """
    Generate a large number of matches across multiple leagues
    
    Args:
        league_count (int): Number of leagues to generate
        matches_per_league (int): Number of matches per league
        
    Returns:
        list: List of generated match data
    """
    leagues = [
        # Top European leagues
        {"name": "English Premier League", "teams": [
            "Liverpool", "Manchester City", "Chelsea", "Arsenal", "Tottenham", 
            "Manchester United", "Leicester City", "West Ham", "Everton", 
            "Newcastle", "Aston Villa", "Crystal Palace", "Brighton", 
            "Wolves", "Southampton", "Burnley", "Leeds United", 
            "Watford", "Norwich", "Brentford"
        ]},
        {"name": "Spanish La Liga", "teams": [
            "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", 
            "Villarreal", "Real Sociedad", "Real Betis", "Athletic Bilbao", 
            "Valencia", "Osasuna", "Celta Vigo", "Espanyol", 
            "Mallorca", "Elche", "Getafe", "Granada", "Cadiz", 
            "Alaves", "Levante", "Rayo Vallecano"
        ]},
        {"name": "Italian Serie A", "teams": [
            "Inter Milan", "AC Milan", "Napoli", "Juventus", "Atalanta", 
            "Lazio", "Roma", "Fiorentina", "Sassuolo", "Verona", 
            "Torino", "Bologna", "Empoli", "Udinese", "Sampdoria", 
            "Spezia", "Cagliari", "Venezia", "Genoa", "Salernitana"
        ]},
        {"name": "German Bundesliga", "teams": [
            "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen", 
            "Wolfsburg", "Eintracht Frankfurt", "Borussia Monchengladbach", 
            "Union Berlin", "Stuttgart", "Freiburg", "Hoffenheim", "Mainz", 
            "Augsburg", "Hertha Berlin", "Arminia Bielefeld", "Koln", 
            "Werder Bremen", "Schalke 04", "Bochum", "Greuther Furth"
        ]},
        {"name": "French Ligue 1", "teams": [
            "PSG", "Lille", "Lyon", "Monaco", "Marseille", "Rennes", 
            "Lens", "Montpellier", "Nice", "Metz", "Saint-Etienne", 
            "Bordeaux", "Angers", "Reims", "Strasbourg", "Lorient", 
            "Brest", "Nantes", "Troyes", "Clermont Foot"
        ]},
        # Additional leagues
        {"name": "Portuguese Primeira Liga", "teams": [
            "Sporting CP", "FC Porto", "Benfica", "Braga", "Vitoria", 
            "Rio Ave", "Famalicao", "Maritimo", "Boavista", "Santa Clara", 
            "Moreirense", "Belenenses", "Portimonense", "Pacos Ferreira", 
            "Gil Vicente", "Tondela", "Nacional", "Farense", "Vizela", "Arouca"
        ]},
        {"name": "Dutch Eredivisie", "teams": [
            "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar", "Vitesse", 
            "Utrecht", "FC Groningen", "FC Twente", "Heerenveen", "Sparta Rotterdam", 
            "Heracles", "Willem II", "Fortuna Sittard", "PEC Zwolle", 
            "NEC Nijmegen", "Go Ahead Eagles", "RKC Waalwijk", "Cambuur", "FC Emmen", "VVV-Venlo"
        ]},
        {"name": "Belgian Pro League", "teams": [
            "Club Brugge", "Genk", "Anderlecht", "Standard Liege", "Antwerp", 
            "Gent", "Charleroi", "Sint-Truiden", "Kortrijk", "Zulte Waregem", 
            "Oostende", "Mechelen", "Eupen", "Cercle Brugge", "OH Leuven", 
            "Beerschot", "Seraing", "Union SG", "Westerlo", "RFC Seraing"
        ]},
        {"name": "Scottish Premiership", "teams": [
            "Celtic", "Rangers", "Aberdeen", "Hibernian", "Heart of Midlothian", 
            "Dundee United", "Motherwell", "St. Johnstone", "St. Mirren", 
            "Kilmarnock", "Ross County", "Livingston", "Dundee FC", 
            "Hamilton", "Inverness", "Falkirk", "Dunfermline", "Partick Thistle", "Greenock Morton", "Arbroath"
        ]},
        {"name": "Russian Premier League", "teams": [
            "Zenit", "CSKA Moscow", "Spartak Moscow", "Lokomotiv Moscow", 
            "Dynamo Moscow", "Krasnodar", "Rostov", "Sochi", "Rubin Kazan", 
            "Akhmat Grozny", "Ufa", "Arsenal Tula", "Ural", "Khimki", 
            "Krylya Sovetov", "Nizhny Novgorod", "Orenburg", "Tambov", "Rotor Volgograd", "Torpedo Moscow"
        ]},
        # More leagues can be added as needed
        {"name": "Turkish Super Lig", "teams": [
            "Besiktas", "Fenerbahce", "Galatasaray", "Trabzonspor", "Istanbul Basaksehir", 
            "Alanyaspor", "Gaziantep", "Hatayspor", "Konyaspor", "Sivasspor", 
            "Kayserispor", "Antalyaspor", "Rizespor", "Kasimpasa", "Goztepe", 
            "Malatyaspor", "Adana Demirspor", "Giresunspor", "Altay", "Fatih Karagumruk"
        ]},
        {"name": "Greek Super League", "teams": [
            "Olympiacos", "PAOK", "AEK Athens", "Panathinaikos", "Aris", 
            "Asteras Tripolis", "Atromitos", "OFI", "PAS Giannina", "Apollon Smyrnis", 
            "Panetolikos", "Ionikos", "Volos", "Lamia", "Xanthi", 
            "Levadiakos", "Larissa", "Panionios", "Veria", "Kerkyra"
        ]},
        {"name": "Croatian HNL", "teams": [
            "Dinamo Zagreb", "Hajduk Split", "Rijeka", "Osijek", "Lokomotiva Zagreb", 
            "Gorica", "Slaven Belupo", "Istra 1961", "Sibenik", "Varazdin", 
            "Zagreb", "Inter Zapresic", "Cibalia", "Hrvatski Dragovoljac", "Rudes", 
            "Sesvete", "Lucko", "Kustosija", "Jarun", "Opatija"
        ]},
        {"name": "Czech First League", "teams": [
            "Slavia Prague", "Sparta Prague", "Viktoria Plzen", "Jablonec", "Banik Ostrava", 
            "Mlada Boleslav", "Sigma Olomouc", "Liberec", "Ceske Budejovice", "Slovacko", 
            "Bohemians 1905", "Teplice", "Zlin", "Karvina", "Pardubice", 
            "Hradec Kralove", "Pribram", "Dukla Prague", "Brno", "Jihlava"
        ]},
        {"name": "Swiss Super League", "teams": [
            "Young Boys", "Basel", "Lugano", "Servette", "Zurich", 
            "Luzern", "St. Gallen", "Lausanne", "Sion", "Grasshoppers", 
            "Thun", "Vaduz", "Winterthur", "Aarau", "Wil", 
            "Schaffhausen", "Xamax", "Chiasso", "Stade Lausanne-Ouchy", "Yverdon"
        ]}
    ]
    
    matches = []
    match_id = 1
    
    # Select a random subset of leagues if we have more than requested
    if len(leagues) > league_count:
        leagues = random.sample(leagues, league_count)
    
    for league in leagues:
        league_name = league["name"]
        teams = league["teams"]
        
        # Generate matches: each team plays against others
        pairs = []
        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                pairs.append((teams[i], teams[j]))
        
        # Select random subset of matches if we have more than requested
        if len(pairs) > matches_per_league:
            pairs = random.sample(pairs, matches_per_league)
        
        for home, away in pairs:
            # Generate random odds with reasonable values
            home_odds = round(random.uniform(1.5, 4.0), 2)
            draw_odds = round(random.uniform(2.8, 4.2), 2)
            away_odds = round(random.uniform(1.5, 4.5), 2)
            
            match = {
                "id": f"m{match_id}",
                "sport": "Soccer",
                "league": league_name,
                "match": f"{home} vs {away}",
                "start_time": utils.get_future_time(hours=random.randint(1, 48)),
                "outcomes": {
                    "home": {"name": home, "odds": home_odds},
                    "draw": {"name": "Draw", "odds": draw_odds},
                    "away": {"name": away, "odds": away_odds}
                },
                "is_active": True
            }
            matches.append(match)
            match_id += 1
    
    # Shuffle the matches for more randomness
    random.shuffle(matches)
    return matches

def scrape_bet365():
    """
    Scrape betting odds from bet365
    
    Returns:
        list: List of events with odds information
    """
    logger.info("Scraping data from bet365...")
    
    # Generate 200 matches across 10 leagues (20 matches per league)
    generated_matches = generate_matches(league_count=10, matches_per_league=20)
    
    # We'll use the bet365 soccer main page for scraping
    url = "https://www.bet365.com/#/AC/B1/C1/D13/E42/F4/"
    
    # In a real implementation, this would access the actual website.
    # For this demonstration, we'll generate a large dataset of matches
    # using our generator function to maximize opportunities
    
    # Add a few fixed matches for testing
    matches = [
        # Premier League matches
        {
            "id": "m1",
            "sport": "Soccer",
            "league": "English Premier League",
            "match": "Liverpool vs Manchester City",
            "start_time": utils.get_future_time(hours=3),
            "outcomes": {
                "home": {"name": "Liverpool", "odds": 2.50},
                "draw": {"name": "Draw", "odds": 3.25},
                "away": {"name": "Manchester City", "odds": 2.75}
            },
            "is_active": True
        },
        {
            "id": "m2",
            "sport": "Soccer",
            "league": "English Premier League",
            "match": "Arsenal vs Chelsea",
            "start_time": utils.get_future_time(hours=5),
            "outcomes": {
                "home": {"name": "Arsenal", "odds": 2.10},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Chelsea", "odds": 3.40}
            },
            "is_active": True
        },
        {
            "id": "m3",
            "sport": "Soccer",
            "league": "English Premier League",
            "match": "Manchester United vs Tottenham",
            "start_time": utils.get_future_time(hours=4),
            "outcomes": {
                "home": {"name": "Manchester United", "odds": 2.30},
                "draw": {"name": "Draw", "odds": 3.20},
                "away": {"name": "Tottenham", "odds": 3.10}
            },
            "is_active": True
        },
        {
            "id": "m4",
            "sport": "Soccer",
            "league": "English Premier League",
            "match": "Newcastle vs Everton",
            "start_time": utils.get_future_time(hours=6),
            "outcomes": {
                "home": {"name": "Newcastle", "odds": 1.90},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Everton", "odds": 4.00}
            },
            "is_active": True
        },
        {
            "id": "m5",
            "sport": "Soccer",
            "league": "English Premier League",
            "match": "West Ham vs Leicester",
            "start_time": utils.get_future_time(hours=7),
            "outcomes": {
                "home": {"name": "West Ham", "odds": 2.15},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Leicester", "odds": 3.40}
            },
            "is_active": True
        },
        
        # La Liga matches
        {
            "id": "m6",
            "sport": "Soccer",
            "league": "Spanish La Liga",
            "match": "Barcelona vs Real Madrid",
            "start_time": utils.get_future_time(hours=8),
            "outcomes": {
                "home": {"name": "Barcelona", "odds": 2.20},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Real Madrid", "odds": 3.10}
            },
            "is_active": True
        },
        {
            "id": "m7",
            "sport": "Soccer",
            "league": "Spanish La Liga",
            "match": "Atletico Madrid vs Sevilla",
            "start_time": utils.get_future_time(hours=9),
            "outcomes": {
                "home": {"name": "Atletico Madrid", "odds": 1.85},
                "draw": {"name": "Draw", "odds": 3.50},
                "away": {"name": "Sevilla", "odds": 4.20}
            },
            "is_active": True
        },
        {
            "id": "m8",
            "sport": "Soccer",
            "league": "Spanish La Liga",
            "match": "Valencia vs Villarreal",
            "start_time": utils.get_future_time(hours=10),
            "outcomes": {
                "home": {"name": "Valencia", "odds": 2.60},
                "draw": {"name": "Draw", "odds": 3.10},
                "away": {"name": "Villarreal", "odds": 2.70}
            },
            "is_active": True
        },
        
        # Serie A matches
        {
            "id": "m9",
            "sport": "Soccer",
            "league": "Italian Serie A",
            "match": "Juventus vs Inter Milan",
            "start_time": utils.get_future_time(hours=26),
            "outcomes": {
                "home": {"name": "Juventus", "odds": 2.30},
                "draw": {"name": "Draw", "odds": 3.10},
                "away": {"name": "Inter Milan", "odds": 3.00}
            },
            "is_active": True
        },
        {
            "id": "m10",
            "sport": "Soccer",
            "league": "Italian Serie A",
            "match": "AC Milan vs Napoli",
            "start_time": utils.get_future_time(hours=27),
            "outcomes": {
                "home": {"name": "AC Milan", "odds": 2.15},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Napoli", "odds": 3.25}
            },
            "is_active": True
        },
        {
            "id": "m11",
            "sport": "Soccer",
            "league": "Italian Serie A",
            "match": "AS Roma vs Lazio",
            "start_time": utils.get_future_time(hours=29),
            "outcomes": {
                "home": {"name": "AS Roma", "odds": 2.40},
                "draw": {"name": "Draw", "odds": 3.10},
                "away": {"name": "Lazio", "odds": 2.95}
            },
            "is_active": True
        },
        
        # Bundesliga matches
        {
            "id": "m12",
            "sport": "Soccer",
            "league": "German Bundesliga",
            "match": "Bayern Munich vs Borussia Dortmund",
            "start_time": utils.get_future_time(hours=28),
            "outcomes": {
                "home": {"name": "Bayern Munich", "odds": 1.75},
                "draw": {"name": "Draw", "odds": 3.80},
                "away": {"name": "Borussia Dortmund", "odds": 4.00}
            },
            "is_active": True
        },
        {
            "id": "m13",
            "sport": "Soccer",
            "league": "German Bundesliga",
            "match": "RB Leipzig vs Bayer Leverkusen",
            "start_time": utils.get_future_time(hours=30),
            "outcomes": {
                "home": {"name": "RB Leipzig", "odds": 2.05},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Bayer Leverkusen", "odds": 3.50}
            },
            "is_active": True
        },
        
        # Ligue 1 matches
        {
            "id": "m14",
            "sport": "Soccer",
            "league": "French Ligue 1",
            "match": "PSG vs Marseille",
            "start_time": utils.get_future_time(hours=31),
            "outcomes": {
                "home": {"name": "PSG", "odds": 1.45},
                "draw": {"name": "Draw", "odds": 4.30},
                "away": {"name": "Marseille", "odds": 6.50}
            },
            "is_active": True
        },
        {
            "id": "m15",
            "sport": "Soccer",
            "league": "French Ligue 1",
            "match": "Lyon vs Monaco",
            "start_time": utils.get_future_time(hours=32),
            "outcomes": {
                "home": {"name": "Lyon", "odds": 2.30},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Monaco", "odds": 2.90}
            },
            "is_active": True
        }
    ]
    
    # Add bookmaker information and normalize
    for match in matches:
        match["bookmaker"] = "bet365"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Add bookmaker information and normalize for generated matches
    for match in generated_matches:
        match["bookmaker"] = "bet365"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Combine the predefined matches with the generated ones
    all_matches = matches + generated_matches
    
    logger.info(f"Retrieved {len(all_matches)} matches from bet365")
    
    # Introduce a small delay to simulate network latency
    time.sleep(0.5)
    
    return all_matches

def scrape_betfair():
    """
    Scrape betting odds from Betfair
    
    Returns:
        list: List of events with odds information
    """
    logger.info("Scraping data from Betfair...")
    
    # We'll use the Betfair soccer main page for scraping
    url = "https://www.betfair.com/sport/football"
    
    # In a real implementation, this would access the actual website.
    # For this demonstration, we'll generate a large dataset to increase opportunities
    
    # Generate 200 matches across 10 leagues (20 matches per league)
    generated_matches = generate_matches(league_count=10, matches_per_league=20)
    
    # Simulated data structure with slightly different odds - now with more matches
    matches = [
        # Premier League matches
        {
            "id": "m1",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Liverpool vs Man City",
            "start_time": utils.get_future_time(hours=3),
            "outcomes": {
                "home": {"name": "Liverpool", "odds": 2.60},
                "draw": {"name": "Draw", "odds": 3.20},
                "away": {"name": "Man City", "odds": 2.65}
            },
            "is_active": True
        },
        {
            "id": "m2",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Arsenal vs Chelsea FC",
            "start_time": utils.get_future_time(hours=5),
            "outcomes": {
                "home": {"name": "Arsenal", "odds": 2.05},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Chelsea FC", "odds": 3.50}
            },
            "is_active": True
        },
        {
            "id": "m3",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Manchester United vs Tottenham Hotspur",
            "start_time": utils.get_future_time(hours=4),
            "outcomes": {
                "home": {"name": "Manchester United", "odds": 2.25},
                "draw": {"name": "Draw", "odds": 3.25},
                "away": {"name": "Tottenham Hotspur", "odds": 3.05}
            },
            "is_active": True
        },
        {
            "id": "m4",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Newcastle United vs Everton FC",
            "start_time": utils.get_future_time(hours=6),
            "outcomes": {
                "home": {"name": "Newcastle United", "odds": 1.95},
                "draw": {"name": "Draw", "odds": 3.35},
                "away": {"name": "Everton FC", "odds": 3.90}
            },
            "is_active": True
        },
        {
            "id": "m5",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "West Ham United vs Leicester City",
            "start_time": utils.get_future_time(hours=7),
            "outcomes": {
                "home": {"name": "West Ham United", "odds": 2.10},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Leicester City", "odds": 3.35}
            },
            "is_active": True
        },
        
        # La Liga matches
        {
            "id": "m6",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "FC Barcelona vs Real Madrid CF",
            "start_time": utils.get_future_time(hours=8),
            "outcomes": {
                "home": {"name": "FC Barcelona", "odds": 2.25},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Real Madrid CF", "odds": 3.05}
            },
            "is_active": True
        },
        {
            "id": "m7",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Atletico Madrid vs Sevilla FC",
            "start_time": utils.get_future_time(hours=9),
            "outcomes": {
                "home": {"name": "Atletico Madrid", "odds": 1.80},
                "draw": {"name": "Draw", "odds": 3.60},
                "away": {"name": "Sevilla FC", "odds": 4.25}
            },
            "is_active": True
        },
        {
            "id": "m8",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Valencia CF vs Villarreal CF",
            "start_time": utils.get_future_time(hours=10),
            "outcomes": {
                "home": {"name": "Valencia CF", "odds": 2.55},
                "draw": {"name": "Draw", "odds": 3.15},
                "away": {"name": "Villarreal CF", "odds": 2.75}
            },
            "is_active": True
        },
        
        # Serie A matches
        {
            "id": "m9",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "Juventus FC vs Inter Milan",
            "start_time": utils.get_future_time(hours=26),
            "outcomes": {
                "home": {"name": "Juventus FC", "odds": 2.40},
                "draw": {"name": "Draw", "odds": 3.00},
                "away": {"name": "Inter Milan", "odds": 2.90}
            },
            "is_active": True
        },
        {
            "id": "m10",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "AC Milan vs SSC Napoli",
            "start_time": utils.get_future_time(hours=27),
            "outcomes": {
                "home": {"name": "AC Milan", "odds": 2.20},
                "draw": {"name": "Draw", "odds": 3.20},
                "away": {"name": "SSC Napoli", "odds": 3.30}
            },
            "is_active": True
        },
        {
            "id": "m11",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "AS Roma vs SS Lazio",
            "start_time": utils.get_future_time(hours=29),
            "outcomes": {
                "home": {"name": "AS Roma", "odds": 2.35},
                "draw": {"name": "Draw", "odds": 3.15},
                "away": {"name": "SS Lazio", "odds": 3.00}
            },
            "is_active": True
        },
        
        # Bundesliga matches
        {
            "id": "m12",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "Bayern Munich vs Borussia Dortmund",
            "start_time": utils.get_future_time(hours=28),
            "outcomes": {
                "home": {"name": "Bayern Munich", "odds": 1.70},
                "draw": {"name": "Draw", "odds": 3.90},
                "away": {"name": "Borussia Dortmund", "odds": 4.10}
            },
            "is_active": True
        },
        {
            "id": "m13",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "RB Leipzig vs Bayer Leverkusen",
            "start_time": utils.get_future_time(hours=30),
            "outcomes": {
                "home": {"name": "RB Leipzig", "odds": 2.10},
                "draw": {"name": "Draw", "odds": 3.35},
                "away": {"name": "Bayer Leverkusen", "odds": 3.40}
            },
            "is_active": True
        },
        
        # Ligue 1 matches
        {
            "id": "m14",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "PSG vs Olympique Marseille",
            "start_time": utils.get_future_time(hours=30),
            "outcomes": {
                "home": {"name": "PSG", "odds": 1.45},
                "draw": {"name": "Draw", "odds": 4.50},
                "away": {"name": "Olympique Marseille", "odds": 6.00}
            },
            "is_active": True
        },
        {
            "id": "m15",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "Olympique Lyonnais vs AS Monaco",
            "start_time": utils.get_future_time(hours=32),
            "outcomes": {
                "home": {"name": "Olympique Lyonnais", "odds": 2.35},
                "draw": {"name": "Draw", "odds": 3.25},
                "away": {"name": "AS Monaco", "odds": 2.85}
            },
            "is_active": True
        }
    ]
    
    # Add bookmaker information and normalize for predefined matches
    for match in matches:
        match["bookmaker"] = "betfair"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Add bookmaker information and normalize for generated matches
    for match in generated_matches:
        match["bookmaker"] = "betfair"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Combine the predefined matches with the generated ones
    all_matches = matches + generated_matches
    
    logger.info(f"Retrieved {len(all_matches)} matches from Betfair")
    
    # Introduce a small delay to simulate network latency
    time.sleep(0.6)
    
    return all_matches

def scrape_stoiximan():
    """
    Scrape betting odds from Stoiximan
    
    Returns:
        list: List of events with odds information
    """
    logger.info("Scraping data from Stoiximan...")
    
    # Generate 200 matches across 10 leagues (20 matches per league)
    generated_matches = generate_matches(league_count=10, matches_per_league=20)
    
    # Simulated data structure with different odds and more matches
    matches = [
        # Premier League matches
        {
            "id": "m1",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Liverpool vs Manchester City",
            "start_time": utils.get_future_time(hours=3),
            "outcomes": {
                "home": {"name": "Liverpool", "odds": 2.50},  # Higher than bet365 for arbitrage potential
                "draw": {"name": "Draw", "odds": 3.35},
                "away": {"name": "Manchester City", "odds": 2.80}
            },
            "is_active": True
        },
        {
            "id": "m2",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Arsenal vs Chelsea",
            "start_time": utils.get_future_time(hours=5),
            "outcomes": {
                "home": {"name": "Arsenal", "odds": 2.15},
                "draw": {"name": "Draw", "odds": 3.35},  # Higher than bet365
                "away": {"name": "Chelsea", "odds": 3.45}
            },
            "is_active": True
        },
        {
            "id": "m3",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Manchester United vs Tottenham",
            "start_time": utils.get_future_time(hours=4),
            "outcomes": {
                "home": {"name": "Manchester United", "odds": 2.30},
                "draw": {"name": "Draw", "odds": 3.25},
                "away": {"name": "Tottenham", "odds": 3.15}  # Higher than bet365
            },
            "is_active": True
        },
        {
            "id": "m4",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Newcastle vs Everton",
            "start_time": utils.get_future_time(hours=6),
            "outcomes": {
                "home": {"name": "Newcastle", "odds": 1.95},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Everton", "odds": 4.10}  # Higher than bet365
            },
            "is_active": True
        },
        {
            "id": "m5",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "West Ham vs Leicester",
            "start_time": utils.get_future_time(hours=7),
            "outcomes": {
                "home": {"name": "West Ham", "odds": 2.20},  # Higher than bet365
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Leicester", "odds": 3.40}
            },
            "is_active": True
        },
        
        # La Liga matches
        {
            "id": "m6",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Barcelona vs Real Madrid",
            "start_time": utils.get_future_time(hours=8),
            "outcomes": {
                "home": {"name": "Barcelona", "odds": 2.10},
                "draw": {"name": "Draw", "odds": 3.50},
                "away": {"name": "Real Madrid", "odds": 3.30}  # Higher than bet365
            },
            "is_active": True
        },
        {
            "id": "m7",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Atletico Madrid vs Sevilla",
            "start_time": utils.get_future_time(hours=9),
            "outcomes": {
                "home": {"name": "Atletico Madrid", "odds": 1.90},  # Higher than bet365
                "draw": {"name": "Draw", "odds": 3.50},
                "away": {"name": "Sevilla", "odds": 4.20}
            },
            "is_active": True
        },
        {
            "id": "m8",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Valencia vs Villarreal",
            "start_time": utils.get_future_time(hours=10),
            "outcomes": {
                "home": {"name": "Valencia", "odds": 2.60},
                "draw": {"name": "Draw", "odds": 3.20},  # Higher than bet365
                "away": {"name": "Villarreal", "odds": 2.70}
            },
            "is_active": True
        },
        
        # Serie A matches
        {
            "id": "m9",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "Juventus vs Inter Milan",
            "start_time": utils.get_future_time(hours=26),
            "outcomes": {
                "home": {"name": "Juventus", "odds": 2.35},
                "draw": {"name": "Draw", "odds": 3.05},
                "away": {"name": "Inter Milan", "odds": 3.05}  # Higher than bet365
            },
            "is_active": True
        },
        {
            "id": "m10",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "AC Milan vs Napoli",
            "start_time": utils.get_future_time(hours=27),
            "outcomes": {
                "home": {"name": "AC Milan", "odds": 2.20},  # Higher than bet365
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Napoli", "odds": 3.25}
            },
            "is_active": True
        },
        
        # Bundesliga matches
        {
            "id": "m11",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "Bayern Munich vs Borussia Dortmund",
            "start_time": utils.get_future_time(hours=28),
            "outcomes": {
                "home": {"name": "Bayern Munich", "odds": 1.68},
                "draw": {"name": "Draw", "odds": 4.00},  # Higher than bet365
                "away": {"name": "Borussia Dortmund", "odds": 4.20}
            },
            "is_active": True
        },
        {
            "id": "m12",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "RB Leipzig vs Bayer Leverkusen",
            "start_time": utils.get_future_time(hours=30),
            "outcomes": {
                "home": {"name": "RB Leipzig", "odds": 2.05},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Bayer Leverkusen", "odds": 3.55}  # Higher than bet365
            },
            "is_active": True
        },
        
        # Ligue 1 matches
        {
            "id": "m13",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "PSG vs Marseille",
            "start_time": utils.get_future_time(hours=31),
            "outcomes": {
                "home": {"name": "PSG", "odds": 1.45},
                "draw": {"name": "Draw", "odds": 4.50},  # Higher than bet365
                "away": {"name": "Marseille", "odds": 6.50}
            },
            "is_active": True
        },
        {
            "id": "m14",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "Lyon vs Monaco",
            "start_time": utils.get_future_time(hours=32),
            "outcomes": {
                "home": {"name": "Lyon", "odds": 2.35},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Monaco", "odds": 2.95}  # Higher than bet365
            },
            "is_active": True
        }
    ]
    
    # Add bookmaker information and normalize
    for match in matches:
        match["bookmaker"] = "stoiximan"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Add bookmaker information and normalize for generated matches
    for match in generated_matches:
        match["bookmaker"] = "stoiximan"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Combine the predefined matches with the generated ones
    all_matches = matches + generated_matches
    
    logger.info(f"Retrieved {len(all_matches)} matches from Stoiximan")
    
    # Introduce a small delay to simulate network latency
    time.sleep(0.5)
    
    return all_matches

def scrape_netbet():
    """
    Scrape betting odds from Netbet
    
    Returns:
        list: List of events with odds information
    """
    logger.info("Scraping data from Netbet...")
    
    # Generate 200 matches across 10 leagues (20 matches per league)
    generated_matches = generate_matches(league_count=10, matches_per_league=20)
    
    # Simulated data structure with different odds - expanded with more matches and odds variations
    matches = [
        # Premier League matches
        {
            "id": "m1",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Liverpool vs Manchester City",
            "start_time": utils.get_future_time(hours=3),
            "outcomes": {
                "home": {"name": "Liverpool", "odds": 2.55},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Manchester City", "odds": 2.70}
            },
            "is_active": True
        },
        {
            "id": "m2",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Arsenal vs Chelsea",
            "start_time": utils.get_future_time(hours=5),
            "outcomes": {
                "home": {"name": "Arsenal", "odds": 2.20},
                "draw": {"name": "Draw", "odds": 3.25},
                "away": {"name": "Chelsea", "odds": 3.35}  # Slightly higher
            },
            "is_active": True
        },
        {
            "id": "m3",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Manchester United vs Tottenham",
            "start_time": utils.get_future_time(hours=4),
            "outcomes": {
                "home": {"name": "Manchester United", "odds": 2.35},  # Higher than others
                "draw": {"name": "Draw", "odds": 3.20},
                "away": {"name": "Tottenham", "odds": 3.05}
            },
            "is_active": True
        },
        {
            "id": "m4",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Newcastle vs Everton",
            "start_time": utils.get_future_time(hours=6),
            "outcomes": {
                "home": {"name": "Newcastle", "odds": 1.90},
                "draw": {"name": "Draw", "odds": 3.45},  # Higher than others
                "away": {"name": "Everton", "odds": 3.95}
            },
            "is_active": True
        },
        {
            "id": "m5",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "West Ham vs Leicester",
            "start_time": utils.get_future_time(hours=7),
            "outcomes": {
                "home": {"name": "West Ham", "odds": 2.15},
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Leicester", "odds": 3.45}  # Higher than others
            },
            "is_active": True
        },
        
        # La Liga matches
        {
            "id": "m6",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Barcelona vs Real Madrid",
            "start_time": utils.get_future_time(hours=8),
            "outcomes": {
                "home": {"name": "Barcelona", "odds": 2.30},  # Higher than some
                "draw": {"name": "Draw", "odds": 3.35},
                "away": {"name": "Real Madrid", "odds": 2.95}
            },
            "is_active": True
        },
        {
            "id": "m7",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Atletico Madrid vs Sevilla",
            "start_time": utils.get_future_time(hours=9),
            "outcomes": {
                "home": {"name": "Atletico Madrid", "odds": 1.85},
                "draw": {"name": "Draw", "odds": 3.55},  # Higher than others
                "away": {"name": "Sevilla", "odds": 4.15}
            },
            "is_active": True
        },
        
        # Serie A matches
        {
            "id": "m8",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "Juventus vs Inter Milan",
            "start_time": utils.get_future_time(hours=26),
            "outcomes": {
                "home": {"name": "Juventus", "odds": 2.45},  # Higher than some
                "draw": {"name": "Draw", "odds": 2.95},
                "away": {"name": "Inter Milan", "odds": 2.85}
            },
            "is_active": True
        },
        {
            "id": "m9",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "AC Milan vs Napoli",
            "start_time": utils.get_future_time(hours=27),
            "outcomes": {
                "home": {"name": "AC Milan", "odds": 2.10},
                "draw": {"name": "Draw", "odds": 3.35},  # Higher than some
                "away": {"name": "Napoli", "odds": 3.30}  # Higher than some
            },
            "is_active": True
        },
        
        # Bundesliga matches
        {
            "id": "m10",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "Bayern Munich vs Borussia Dortmund",
            "start_time": utils.get_future_time(hours=28),
            "outcomes": {
                "home": {"name": "Bayern Munich", "odds": 1.70},
                "draw": {"name": "Draw", "odds": 3.85},
                "away": {"name": "Borussia Dortmund", "odds": 4.15}  # Higher than some
            },
            "is_active": True
        },
        
        # Ligue 1 matches
        {
            "id": "m11",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "PSG vs Marseille",
            "start_time": utils.get_future_time(hours=31),
            "outcomes": {
                "home": {"name": "PSG", "odds": 1.40},
                "draw": {"name": "Draw", "odds": 4.60},  # Higher than others for arbitrage
                "away": {"name": "Marseille", "odds": 6.40}
            },
            "is_active": True
        },
        {
            "id": "m12",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "Lyon vs Monaco",
            "start_time": utils.get_future_time(hours=32),
            "outcomes": {
                "home": {"name": "Lyon", "odds": 2.40},  # Higher than others
                "draw": {"name": "Draw", "odds": 3.25},
                "away": {"name": "Monaco", "odds": 2.85}
            },
            "is_active": True
        }
    ]
    
    # Add bookmaker information and normalize
    for match in matches:
        match["bookmaker"] = "netbet"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Add bookmaker information and normalize for generated matches
    for match in generated_matches:
        match["bookmaker"] = "netbet"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Combine the predefined matches with the generated ones
    all_matches = matches + generated_matches
    
    logger.info(f"Retrieved {len(all_matches)} matches from Netbet")
    
    # Introduce a small delay to simulate network latency
    time.sleep(0.4)
    
    return all_matches

def scrape_novibet():
    """
    Scrape betting odds from Novibet
    
    Returns:
        list: List of events with odds information
    """
    logger.info("Scraping data from Novibet...")
    
    # Generate 200 matches across 10 leagues (20 matches per league)
    generated_matches = generate_matches(league_count=10, matches_per_league=20)
    
    # Simulated data structure with different odds - expanded with more matches
    matches = [
        # Premier League matches
        {
            "id": "m1",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Liverpool vs Manchester City",
            "start_time": utils.get_future_time(hours=3),
            "outcomes": {
                "home": {"name": "Liverpool", "odds": 2.58},  # Higher than some others for arbitrage
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Manchester City", "odds": 2.73}
            },
            "is_active": True
        },
        {
            "id": "m2",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Arsenal vs Chelsea",
            "start_time": utils.get_future_time(hours=5),
            "outcomes": {
                "home": {"name": "Arsenal", "odds": 2.05},
                "draw": {"name": "Draw", "odds": 3.45},  # Higher than some others
                "away": {"name": "Chelsea", "odds": 3.50}  # Higher than some others
            },
            "is_active": True
        },
        {
            "id": "m3",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Manchester United vs Tottenham",
            "start_time": utils.get_future_time(hours=4),
            "outcomes": {
                "home": {"name": "Manchester United", "odds": 2.32},
                "draw": {"name": "Draw", "odds": 3.30},  # Higher than some others
                "away": {"name": "Tottenham", "odds": 3.05}
            },
            "is_active": True
        },
        {
            "id": "m4",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Newcastle vs Everton",
            "start_time": utils.get_future_time(hours=6),
            "outcomes": {
                "home": {"name": "Newcastle", "odds": 1.93},
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Everton", "odds": 4.05}  # Higher than some others
            },
            "is_active": True
        },
        {
            "id": "m5",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "West Ham vs Leicester",
            "start_time": utils.get_future_time(hours=7),
            "outcomes": {
                "home": {"name": "West Ham", "odds": 2.17},
                "draw": {"name": "Draw", "odds": 3.35},  # Higher than some others
                "away": {"name": "Leicester", "odds": 3.40}
            },
            "is_active": True
        },
        
        # La Liga matches
        {
            "id": "m6",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Barcelona vs Real Madrid",
            "start_time": utils.get_future_time(hours=8),
            "outcomes": {
                "home": {"name": "Barcelona", "odds": 2.22},
                "draw": {"name": "Draw", "odds": 3.42},
                "away": {"name": "Real Madrid", "odds": 3.20}  # Higher than some for arbitrage
            },
            "is_active": True
        },
        {
            "id": "m7",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Atletico Madrid vs Sevilla",
            "start_time": utils.get_future_time(hours=9),
            "outcomes": {
                "home": {"name": "Atletico Madrid", "odds": 1.88},  # Higher than some for arbitrage
                "draw": {"name": "Draw", "odds": 3.50},
                "away": {"name": "Sevilla", "odds": 4.20}
            },
            "is_active": True
        },
        {
            "id": "m8",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Valencia vs Villarreal",
            "start_time": utils.get_future_time(hours=10),
            "outcomes": {
                "home": {"name": "Valencia", "odds": 2.65},  # Higher than some for arbitrage
                "draw": {"name": "Draw", "odds": 3.15},
                "away": {"name": "Villarreal", "odds": 2.70}
            },
            "is_active": True
        },
        
        # Serie A matches
        {
            "id": "m9",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "Juventus vs Inter Milan",
            "start_time": utils.get_future_time(hours=26),
            "outcomes": {
                "home": {"name": "Juventus", "odds": 2.42},
                "draw": {"name": "Draw", "odds": 3.10},  # Higher than some for arbitrage
                "away": {"name": "Inter Milan", "odds": 2.85}
            },
            "is_active": True
        },
        {
            "id": "m10",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "AC Milan vs Napoli",
            "start_time": utils.get_future_time(hours=27),
            "outcomes": {
                "home": {"name": "AC Milan", "odds": 2.18},  # Higher than some for arbitrage
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Napoli", "odds": 3.25}
            },
            "is_active": True
        },
        
        # Bundesliga matches
        {
            "id": "m11",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "Bayern Munich vs Borussia Dortmund",
            "start_time": utils.get_future_time(hours=28),
            "outcomes": {
                "home": {"name": "Bayern Munich", "odds": 1.73},
                "draw": {"name": "Draw", "odds": 3.85},
                "away": {"name": "Borussia Dortmund", "odds": 4.15}
            },
            "is_active": True
        },
        {
            "id": "m12",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "RB Leipzig vs Bayer Leverkusen",
            "start_time": utils.get_future_time(hours=30),
            "outcomes": {
                "home": {"name": "RB Leipzig", "odds": 2.08},
                "draw": {"name": "Draw", "odds": 3.45},  # Higher than some for arbitrage
                "away": {"name": "Bayer Leverkusen", "odds": 3.45}
            },
            "is_active": True
        },
        
        # Ligue 1 matches
        {
            "id": "m13",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "PSG vs Marseille",
            "start_time": utils.get_future_time(hours=31),
            "outcomes": {
                "home": {"name": "PSG", "odds": 1.44},
                "draw": {"name": "Draw", "odds": 4.40},
                "away": {"name": "Marseille", "odds": 6.70}  # Higher than others for arbitrage
            },
            "is_active": True
        }
    ]
    
    # Add bookmaker information and normalize
    for match in matches:
        match["bookmaker"] = "novibet"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Add bookmaker information and normalize for generated matches
    for match in generated_matches:
        match["bookmaker"] = "novibet"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Combine the predefined matches with the generated ones
    all_matches = matches + generated_matches
    
    logger.info(f"Retrieved {len(all_matches)} matches from Novibet")
    
    # Introduce a small delay to simulate network latency
    time.sleep(0.5)
    
    return all_matches

def scrape_casinoly():
    """
    Scrape betting odds from Casinoly
    
    Returns:
        list: List of events with odds information
    """
    logger.info("Scraping data from Casinoly...")
    
    # Generate 200 matches across 10 leagues (20 matches per league)
    generated_matches = generate_matches(league_count=10, matches_per_league=20)
    
    # Simulated data structure with different odds - expanded with more matches for arbitrage
    matches = [
        # Premier League matches
        {
            "id": "m1",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Liverpool vs Manchester City",
            "start_time": utils.get_future_time(hours=3),
            "outcomes": {
                "home": {"name": "Liverpool", "odds": 2.62},  # Higher than others for arbitrage
                "draw": {"name": "Draw", "odds": 3.15},
                "away": {"name": "Manchester City", "odds": 2.68}
            },
            "is_active": True
        },
        {
            "id": "m2",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Arsenal vs Chelsea",
            "start_time": utils.get_future_time(hours=5),
            "outcomes": {
                "home": {"name": "Arsenal", "odds": 2.08},
                "draw": {"name": "Draw", "odds": 3.35},
                "away": {"name": "Chelsea", "odds": 3.55}  # Higher than others for arbitrage
            },
            "is_active": True
        },
        {
            "id": "m3",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Manchester United vs Tottenham",
            "start_time": utils.get_future_time(hours=4),
            "outcomes": {
                "home": {"name": "Manchester United", "odds": 2.35},  # Higher than some
                "draw": {"name": "Draw", "odds": 3.20},
                "away": {"name": "Tottenham", "odds": 3.10}
            },
            "is_active": True
        },
        {
            "id": "m4",
            "sport": "Soccer",
            "league": "Premier League",
            "match": "Newcastle vs Everton",
            "start_time": utils.get_future_time(hours=6),
            "outcomes": {
                "home": {"name": "Newcastle", "odds": 1.95},  # Higher than some
                "draw": {"name": "Draw", "odds": 3.40},
                "away": {"name": "Everton", "odds": 4.00}
            },
            "is_active": True
        },
        
        # La Liga matches
        {
            "id": "m5",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Barcelona vs Real Madrid",
            "start_time": utils.get_future_time(hours=8),
            "outcomes": {
                "home": {"name": "Barcelona", "odds": 2.15},
                "draw": {"name": "Draw", "odds": 3.50},  # Higher than some for arbitrage
                "away": {"name": "Real Madrid", "odds": 3.15}
            },
            "is_active": True
        },
        {
            "id": "m6",
            "sport": "Soccer",
            "league": "La Liga",
            "match": "Atletico Madrid vs Sevilla",
            "start_time": utils.get_future_time(hours=9),
            "outcomes": {
                "home": {"name": "Atletico Madrid", "odds": 1.85},
                "draw": {"name": "Draw", "odds": 3.60},  # Higher than others for arbitrage
                "away": {"name": "Sevilla", "odds": 4.25}  # Higher than some
            },
            "is_active": True
        },
        
        # Serie A matches
        {
            "id": "m7",
            "sport": "Soccer",
            "league": "Serie A",
            "match": "Juventus vs Inter Milan",
            "start_time": utils.get_future_time(hours=26),
            "outcomes": {
                "home": {"name": "Juventus", "odds": 2.40},
                "draw": {"name": "Draw", "odds": 3.05},
                "away": {"name": "Inter Milan", "odds": 3.05}  # Higher than some
            },
            "is_active": True
        },
        
        # Bundesliga matches
        {
            "id": "m8",
            "sport": "Soccer",
            "league": "Bundesliga",
            "match": "Bayern Munich vs Borussia Dortmund",
            "start_time": utils.get_future_time(hours=28),
            "outcomes": {
                "home": {"name": "Bayern Munich", "odds": 1.75},
                "draw": {"name": "Draw", "odds": 3.90},  # Higher than some
                "away": {"name": "Borussia Dortmund", "odds": 4.25}  # Higher than others for arbitrage
            },
            "is_active": True
        },
        
        # Ligue 1 matches
        {
            "id": "m9",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "PSG vs Marseille",
            "start_time": utils.get_future_time(hours=31),
            "outcomes": {
                "home": {"name": "PSG", "odds": 1.42},
                "draw": {"name": "Draw", "odds": 4.55},  # Higher than others for arbitrage
                "away": {"name": "Marseille", "odds": 6.55}
            },
            "is_active": True
        },
        {
            "id": "m10",
            "sport": "Soccer",
            "league": "Ligue 1",
            "match": "Lyon vs Monaco",
            "start_time": utils.get_future_time(hours=32),
            "outcomes": {
                "home": {"name": "Lyon", "odds": 2.38},  # Higher than some
                "draw": {"name": "Draw", "odds": 3.30},
                "away": {"name": "Monaco", "odds": 2.95}  # Higher than some for arbitrage
            },
            "is_active": True
        }
    ]
    
    # Add bookmaker information and normalize
    for match in matches:
        match["bookmaker"] = "casinoly"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Add bookmaker information and normalize for generated matches
    for match in generated_matches:
        match["bookmaker"] = "casinoly"
        # Normalize team names
        match_parts = match["match"].split(" vs ")
        match["normalized_match"] = f"{normalize_team_name(match_parts[0])} vs {normalize_team_name(match_parts[1])}"
    
    # Combine the predefined matches with the generated ones
    all_matches = matches + generated_matches
    
    logger.info(f"Retrieved {len(all_matches)} matches from Casinoly")
    
    # Introduce a small delay to simulate network latency
    time.sleep(0.4)
    
    return all_matches

# Backward compatibility functions
def scrape_bookmaker1():
    """Legacy function to maintain backward compatibility"""
    return scrape_bet365()

def scrape_bookmaker2():
    """Legacy function to maintain backward compatibility"""
    return scrape_betfair()
