import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

def get_bookmaker_stats(all_odds):
    """
    Calculate statistics for each bookmaker
    
    Args:
        all_odds (dict): Dictionary of all odds from different bookmakers
    
    Returns:
        pd.DataFrame: DataFrame with bookmaker statistics
    """
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
    """
    Find matches that are available across multiple bookmakers
    
    Args:
        all_odds (dict): Dictionary of all odds from different bookmakers
    
    Returns:
        list: List of dictionaries with common match data
    """
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
    """
    Create a bar chart comparing odds across bookmakers for a match
    
    Args:
        match_data (dict): Dictionary with match data including odds
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with odds comparison
    """
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
    """
    Create a heatmap showing odds correlations between bookmakers
    
    Args:
        all_odds (dict): Dictionary of all odds from different bookmakers
    
    Returns:
        plotly.graph_objects.Figure: Plotly figure with heatmap
    """
    common_matches = get_common_matches(all_odds)
    bookmakers = list(all_odds.keys())
    
    # Build a DataFrame of odds differences between bookmakers
    # Use float dtype explicitly to avoid dtype warnings
    odds_differences = pd.DataFrame(0.0, index=bookmakers, columns=bookmakers, dtype=float)
    counts = pd.DataFrame(0, index=bookmakers, columns=bookmakers, dtype=float)
    
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

def display_dashboard(all_odds):
    """
    Display the interactive bookmaker comparison dashboard
    
    Args:
        all_odds (dict): Dictionary of all odds from different bookmakers
    """
    st.subheader("Bookmaker Comparison Dashboard")
    
    if not all_odds:
        st.info("No data available yet. Start the bot to collect odds data.")
        return
        
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Bookmaker Stats", "Odds Comparison", "Correlation Analysis"])
    
    with tab1:
        st.subheader("Bookmaker Statistics")
        
        stats_df = get_bookmaker_stats(all_odds)
        
        if not stats_df.empty:
            # Format for display
            display_df = stats_df.copy()
            for col in ['avg_odds', 'min_odds', 'max_odds', 'median_odds', 'std_dev']:
                display_df[col] = display_df[col].round(2)
                
            st.dataframe(display_df, use_container_width=True)
            
            # Create bar chart for average odds
            fig = px.bar(
                stats_df,
                x='bookmaker',
                y='avg_odds',
                error_y='std_dev',
                title="Average Odds by Bookmaker",
                labels={'bookmaker': 'Bookmaker', 'avg_odds': 'Average Odds Value'},
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Create chart for odds range
            fig = go.Figure()
            
            for i, row in stats_df.iterrows():
                fig.add_trace(go.Box(
                    name=row['bookmaker'],
                    y=[row['min_odds'], row['median_odds'], row['max_odds']],
                    boxpoints=False,
                    marker_color=px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
                ))
                
            fig.update_layout(
                title="Odds Range by Bookmaker",
                yaxis_title="Odds Value",
                showlegend=False,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No statistics available yet.")
            
    with tab2:
        st.subheader("Odds Comparison for Common Matches")
        
        common_matches = get_common_matches(all_odds)
        
        if common_matches:
            # Create a selection widget for matches
            match_options = [m['match'] for m in common_matches]
            selected_match = st.selectbox(
                "Select a match:",
                match_options
            )
            
            # Find the selected match data
            selected_data = next(
                (m for m in common_matches if m['match'] == selected_match), 
                None
            )
            
            if selected_data:
                # Show which bookmakers have this match
                st.write(f"Available on {len(selected_data['bookmakers'])} bookmakers: {', '.join(selected_data['bookmakers'])}")
                
                # Create the comparison chart
                fig = create_odds_comparison_chart(selected_data)
                st.plotly_chart(fig, use_container_width=True)
                
                # Calculate potential arbitrage
                outcomes = list(selected_data['odds_data'].keys())
                if len(outcomes) >= 2:  # Need at least 2 outcomes for arbitrage
                    st.subheader("Best Odds Analysis")
                    
                    best_odds = {}
                    best_bookmakers = {}
                    
                    for outcome in outcomes:
                        if selected_data['odds_data'][outcome]:
                            best_odds[outcome] = max(selected_data['odds_data'][outcome].values())
                            best_bookmakers[outcome] = max(
                                selected_data['odds_data'][outcome].items(),
                                key=lambda x: x[1]
                            )[0]
                    
                    # Calculate arbitrage opportunity
                    if best_odds:
                        implied_probs = [1/odds for odds in best_odds.values()]
                        total_implied_prob = sum(implied_probs)
                        profit_margin = (1 - total_implied_prob) * 100
                        
                        # Show potential arbitrage
                        if profit_margin > 0:
                            st.success(f"Potential arbitrage opportunity detected! Profit margin: {profit_margin:.2f}%")
                        else:
                            st.info(f"No arbitrage opportunity found. Margin: {profit_margin:.2f}%")
                        
                        # Show best odds for each outcome
                        best_odds_df = pd.DataFrame({
                            'Outcome': list(best_odds.keys()),
                            'Best Odds': list(best_odds.values()),
                            'Bookmaker': list(best_bookmakers.values()),
                            'Implied Probability': [f"{p*100:.2f}%" for p in implied_probs]
                        })
                        
                        st.dataframe(best_odds_df, use_container_width=True)
        else:
            st.info("No common matches found across bookmakers yet.")
            
    with tab3:
        st.subheader("Bookmaker Correlation Analysis")
        
        if len(all_odds) >= 2:
            # Create a heatmap showing differences between bookmakers
            fig = create_bookmaker_heatmap(all_odds)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("""
            **How to interpret this chart:**
            - Darker colors indicate larger average percentage differences in odds between bookmakers
            - Pairs with higher differences are more likely to offer arbitrage opportunities
            - Look for consistently dark squares to identify bookmaker pairs with high arbitrage potential
            """)
        else:
            st.info("Need data from at least 2 bookmakers for correlation analysis.")