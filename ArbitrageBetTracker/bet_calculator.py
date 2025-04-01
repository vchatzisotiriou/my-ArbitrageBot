import numpy as np

def calculate_optimal_stakes(odds_list, total_investment=100):
    """
    Calculate the optimal stakes for a set of odds to guarantee profit
    
    Args:
        odds_list (list): List of decimal odds
        total_investment (float): Total amount to invest
    
    Returns:
        dict: Dictionary with calculation results
    """
    # Calculate implied probabilities
    implied_probs = [1/odds for odds in odds_list]
    total_implied_prob = sum(implied_probs)
    
    # Calculate if arbitrage exists (total implied probability < 1)
    is_arbitrage = total_implied_prob < 1
    
    # Calculate profit percentage
    profit_percentage = (1 - total_implied_prob) * 100 if is_arbitrage else 0
    
    # Calculate individual stakes
    individual_stakes = [total_investment * (1/odds) / total_implied_prob for odds in odds_list]
    
    # Calculate expected return
    expected_return = total_investment / total_implied_prob if total_implied_prob > 0 else 0
    expected_profit = expected_return - total_investment
    
    # Calculate ROI (Return on Investment)
    roi = (expected_profit / total_investment) * 100 if total_investment > 0 else 0
    
    return {
        'is_arbitrage': is_arbitrage,
        'profit_percentage': profit_percentage,
        'individual_stakes': individual_stakes,
        'sum_stakes': sum(individual_stakes),
        'expected_return': expected_return,
        'expected_profit': expected_profit,
        'roi': roi,
        'investment': total_investment
    }

def recommend_best_odds_combination(odds_data):
    """
    Recommend the best combination of odds for arbitrage betting
    
    Args:
        odds_data (dict): Dictionary mapping outcomes to lists of available odds
        
    Returns:
        dict: Best combination and calculation results
    """
    # Convert odds_data to list of lists format
    # e.g., {'home': [1.5, 1.6], 'away': [2.5, 2.7]} -> [[1.5, 2.5], [1.5, 2.7], [1.6, 2.5], [1.6, 2.7]]
    outcomes = list(odds_data.keys())
    combinations = []
    
    # Generate all possible combinations recursively
    def generate_combinations(current_combo, outcome_index):
        if outcome_index >= len(outcomes):
            combinations.append(current_combo.copy())
            return
            
        outcome = outcomes[outcome_index]
        for odds in odds_data[outcome]:
            current_combo.append(odds)
            generate_combinations(current_combo, outcome_index + 1)
            current_combo.pop()
    
    generate_combinations([], 0)
    
    # Find the combination with the highest expected profit
    best_combination = None
    best_result = None
    highest_profit = 0
    
    for combo in combinations:
        result = calculate_optimal_stakes(combo)
        if result['is_arbitrage'] and result['expected_profit'] > highest_profit:
            highest_profit = result['expected_profit']
            best_combination = combo
            best_result = result
    
    # If no arbitrage found, find the combination with the lowest loss
    if best_combination is None:
        lowest_loss = float('inf')
        for combo in combinations:
            result = calculate_optimal_stakes(combo)
            profit_loss = -result['profit_percentage']
            if profit_loss < lowest_loss:
                lowest_loss = profit_loss
                best_combination = combo
                best_result = result
    
    # Prepare results with outcome labels
    results = {
        'combination': dict(zip(outcomes, best_combination)) if best_combination else {},
        'calculations': best_result
    }
    
    return results

def analyze_risk_reward(stake, odds, probability):
    """
    Analyze the risk/reward of a single bet
    
    Args:
        stake (float): Amount to bet
        odds (float): Decimal odds
        probability (float): True probability of the outcome (0-1)
        
    Returns:
        dict: Risk/reward analysis
    """
    # Expected value
    win_amount = stake * (odds - 1)
    ev = (win_amount * probability) - (stake * (1 - probability))
    
    # Kelly criterion calculation
    if odds > 1 and probability > 0:
        kelly_fraction = ((odds * probability) - 1) / (odds - 1)
        # Cap kelly at reasonable values
        kelly_fraction = max(0, min(kelly_fraction, 0.25))
    else:
        kelly_fraction = 0
    
    # Kelly recommended stake
    kelly_stake = kelly_fraction * stake
    
    return {
        'expected_value': ev,
        'kelly_fraction': kelly_fraction,
        'kelly_stake': kelly_stake,
        'win_amount': win_amount,
        'stake': stake,
        'odds': odds
    }