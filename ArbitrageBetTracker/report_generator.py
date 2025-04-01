import pandas as pd
import io
import base64
from datetime import datetime

def generate_csv_report(opportunities):
    """
    Generate a CSV report of arbitrage opportunities
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        str: CSV content as string
    """
    # Create a DataFrame from opportunities
    data = []
    for opp in opportunities:
        bookmakers = ", ".join(set([bet['bookmaker'] for bet in opp['bets']]))
        
        data.append({
            'Match': opp['match'],
            'Sport': opp['sport'],
            'League': opp['league'],
            'Profit %': f"{opp['profit_percentage']:.2f}%",
            'Investment': f"${opp['investment']:.2f}",
            'Expected Return': f"${opp['expected_return']:.2f}",
            'Bookmakers': bookmakers,
            'Start Time': opp['start_time'],
            'Discovered': opp['discovered_at']
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert to CSV
    csv = df.to_csv(index=False)
    
    return csv

def generate_text_report(opportunities):
    """
    Generate a text report of arbitrage opportunities
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        str: Text report content
    """
    report = "ARBITRAGE BETTING OPPORTUNITIES REPORT\n"
    report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Add each opportunity
    for i, opp in enumerate(opportunities, 1):
        report += f"Opportunity #{i}\n"
        report += f"Match: {opp['match']}\n"
        report += f"Sport/League: {opp['sport']} / {opp['league']}\n"
        report += f"Profit: {opp['profit_percentage']:.2f}%\n"
        report += f"Investment: ${opp['investment']:.2f}\n"
        report += f"Expected Return: ${opp['expected_return']:.2f}\n"
        report += "Bets:\n"
        
        for bet in opp['bets']:
            report += f"  • {bet['bookmaker']}: ${bet['stake']:.2f} on {bet['outcome']} @ {bet['odds']}\n"
            
        report += f"Match starts at: {opp['start_time']}\n"
        report += f"Found at: {opp['discovered_at']}\n"
        report += "=" * 40 + "\n\n"
        
    return report

def get_download_link(content, filename, link_text):
    """
    Generate a download link for a file with the given content
    
    Args:
        content (str): Content of the file
        filename (str): Name of the file to download
        link_text (str): Text to display for the download link
    
    Returns:
        str: HTML for the download link
    """
    # Determine the MIME type based on file extension
    if filename.endswith('.csv'):
        mime = "text/csv"
    else:
        mime = "text/plain"
        
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}">{link_text}</a>'
    return href