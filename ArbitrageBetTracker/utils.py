import time
from datetime import datetime, timedelta
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('utils')

def get_current_time():
    """Return the current time as a formatted string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_future_time(hours=1, minutes=0):
    """
    Get a future time from now
    
    Args:
        hours (int): Hours to add to current time
        minutes (int): Minutes to add to current time
    
    Returns:
        str: Formatted future time string
    """
    future_time = datetime.now() + timedelta(hours=hours, minutes=minutes)
    return future_time.strftime("%Y-%m-%d %H:%M:%S")

def time_difference_in_minutes(time_str):
    """
    Calculate the difference in minutes between given time and now
    
    Args:
        time_str (str): Time string in format "%Y-%m-%d %H:%M:%S"
    
    Returns:
        float: Difference in minutes
    """
    try:
        time_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        diff = time_obj - datetime.now()
        return diff.total_seconds() / 60
    except ValueError as e:
        logger.error(f"Error parsing time string: {e}")
        return 0

def format_currency(amount, currency='$'):
    """
    Format an amount as currency
    
    Args:
        amount (float): Amount to format
        currency (str): Currency symbol
    
    Returns:
        str: Formatted currency string
    """
    return f"{currency}{amount:.2f}"

def calculate_kelly_criterion(decimal_odds, estimated_probability):
    """
    Calculate optimal bet size using the Kelly Criterion
    
    Args:
        decimal_odds (float): Decimal odds for the bet
        estimated_probability (float): Estimated probability of winning (0-1)
    
    Returns:
        float: Optimal fraction of bankroll to bet
    """
    if decimal_odds <= 1 or estimated_probability <= 0 or estimated_probability >= 1:
        return 0
    
    q = 1 - estimated_probability
    b = decimal_odds - 1  # Convert to fractional odds
    
    kelly = (b * estimated_probability - q) / b
    
    # Limit to positive values only
    return max(0, kelly)

def log_execution_time(func):
    """
    Decorator to log execution time of functions
    
    Args:
        func: Function to be decorated
    
    Returns:
        function: Decorated function
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

def is_time_between(start_time_str, end_time_str, current_time=None):
    """
    Check if current time is between start and end time
    
    Args:
        start_time_str (str): Start time in format "%H:%M"
        end_time_str (str): End time in format "%H:%M"
        current_time (datetime, optional): Current time. Defaults to None (now).
    
    Returns:
        bool: True if current time is between start and end time
    """
    if current_time is None:
        current_time = datetime.now()
    
    current_time_str = current_time.strftime("%H:%M")
    
    return start_time_str <= current_time_str <= end_time_str

def generate_unique_id(prefix=''):
    """
    Generate a unique ID with timestamp and random component
    
    Args:
        prefix (str, optional): Prefix for the ID. Defaults to ''.
    
    Returns:
        str: Unique ID
    """
    timestamp = int(time.time() * 1000)
    random_component = random.randint(1000, 9999)
    return f"{prefix}{timestamp}{random_component}"

def safe_float_conversion(value, default=0.0):
    """
    Safely convert a value to float
    
    Args:
        value: Value to convert
        default (float, optional): Default value if conversion fails. Defaults to 0.0.
    
    Returns:
        float: Converted value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
