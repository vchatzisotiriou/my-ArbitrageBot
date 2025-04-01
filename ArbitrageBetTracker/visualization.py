import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

def create_profit_distribution_chart(opportunities):
    """
    Create a histogram showing the distribution of profit percentages
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with histogram
    """
    if not opportunities:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="No data available for profit distribution",
            xaxis_title="Profit Percentage (%)",
            yaxis_title="Number of Opportunities"
        )
        return fig
    
    # Extract profit percentages
    profit_data = [{'profit': opp['profit_percentage'], 'match': opp['match']} 
                  for opp in opportunities]
    profit_df = pd.DataFrame(profit_data)
    
    # Create histogram
    fig = px.histogram(
        profit_df, 
        x='profit', 
        nbins=20,
        title="Distribution of Profit Percentages",
        labels={'profit': 'Profit Percentage (%)'}
    )
    
    # Customize layout
    fig.update_layout(
        xaxis_title="Profit Percentage (%)",
        yaxis_title="Number of Opportunities",
        bargap=0.1
    )
    
    return fig

def create_bookmaker_comparison_chart(opportunities):
    """
    Create a bar chart showing which bookmakers appear most frequently
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with bar chart
    """
    if not opportunities:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="No data available for bookmaker comparison",
            xaxis_title="Bookmaker",
            yaxis_title="Appearances in Opportunities"
        )
        return fig
    
    # Count bookmaker occurrences
    bookmaker_counts = {}
    for opp in opportunities:
        for bet in opp['bets']:
            bookmaker = bet['bookmaker']
            if bookmaker in bookmaker_counts:
                bookmaker_counts[bookmaker] += 1
            else:
                bookmaker_counts[bookmaker] = 1
    
    # Create DataFrame
    bk_df = pd.DataFrame({
        'Bookmaker': list(bookmaker_counts.keys()),
        'Count': list(bookmaker_counts.values())
    })
    
    # Sort by count
    bk_df = bk_df.sort_values('Count', ascending=False)
    
    # Create bar chart
    fig = px.bar(
        bk_df,
        x='Bookmaker',
        y='Count',
        title="Bookmaker Frequency in Arbitrage Opportunities",
        color='Count',
        color_continuous_scale=px.colors.sequential.Blues
    )
    
    # Customize layout
    fig.update_layout(
        xaxis_title="Bookmaker",
        yaxis_title="Appearances in Opportunities",
    )
    
    return fig

def create_sport_distribution_pie(opportunities):
    """
    Create a pie chart showing the distribution of sports
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with pie chart
    """
    if not opportunities:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="No data available for sport distribution"
        )
        return fig
    
    # Count sport occurrences
    sport_counts = {}
    for opp in opportunities:
        sport = opp['sport']
        if sport in sport_counts:
            sport_counts[sport] += 1
        else:
            sport_counts[sport] = 1
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=list(sport_counts.keys()),
        values=list(sport_counts.values()),
        hole=0.4,
        marker_colors=px.colors.qualitative.Pastel
    )])
    
    # Customize layout
    fig.update_layout(
        title="Distribution of Sports in Arbitrage Opportunities"
    )
    
    return fig

def create_profit_by_sport_chart(opportunities):
    """
    Create a box plot showing profit percentages by sport
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with box plot
    """
    if not opportunities:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="No data available for profit by sport analysis",
            xaxis_title="Sport",
            yaxis_title="Profit Percentage (%)"
        )
        return fig
    
    # Create DataFrame
    data = []
    for opp in opportunities:
        data.append({
            'Sport': opp['sport'],
            'Profit': opp['profit_percentage']
        })
    df = pd.DataFrame(data)
    
    # Create box plot
    fig = px.box(
        df,
        x='Sport',
        y='Profit',
        title="Profit Percentages by Sport",
        color='Sport',
        color_discrete_sequence=px.colors.qualitative.G10
    )
    
    # Customize layout
    fig.update_layout(
        xaxis_title="Sport",
        yaxis_title="Profit Percentage (%)"
    )
    
    return fig

def create_timeline_chart(opportunities):
    """
    Create a timeline chart showing when matches with arbitrage opportunities start
    
    Args:
        opportunities (list): List of arbitrage opportunities
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with timeline
    """
    if not opportunities:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(
            title="No data available for match timeline"
        )
        return fig
    
    # Create DataFrame
    data = []
    for opp in opportunities:
        try:
            # Parse the start time string to datetime
            start_time = datetime.strptime(opp['start_time'], "%Y-%m-%d %H:%M:%S")
            
            data.append({
                'Match': opp['match'],
                'Sport': opp['sport'],
                'Start Time': start_time,
                'Profit': opp['profit_percentage']
            })
        except (ValueError, TypeError):
            # Skip if date parsing fails
            continue
    
    # Return empty figure if no valid dates
    if not data:
        fig = go.Figure()
        fig.update_layout(
            title="No valid date data available for match timeline"
        )
        return fig
        
    df = pd.DataFrame(data)
    
    # Sort by start time
    df = df.sort_values('Start Time')
    
    # Create scatter plot
    fig = px.scatter(
        df,
        x='Start Time',
        y='Profit',
        color='Sport',
        hover_name='Match',
        size='Profit',
        title="Upcoming Matches with Arbitrage Opportunities",
        labels={'Start Time': 'Match Start Time', 'Profit': 'Profit Percentage (%)'}
    )
    
    # Add line connecting points to show timeline
    fig.add_trace(go.Scatter(
        x=df['Start Time'],
        y=df['Profit'],
        mode='lines',
        line=dict(color='rgba(0,0,0,0.3)', width=1),
        showlegend=False
    ))
    
    # Customize layout
    fig.update_layout(
        xaxis_title="Match Start Time",
        yaxis_title="Profit Percentage (%)"
    )
    
    return fig