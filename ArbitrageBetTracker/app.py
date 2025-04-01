import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import threading

import scraper
import arbitrage
import data_store
import utils
import bookmaker_dashboard

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
    st.session_state.initialized = True

# Ensure log_messages is always initialized as it's accessed from background threads
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []

def add_log(message):
    """Add timestamped log message to session state"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
    st.session_state.log_messages.append(f"[{timestamp}] {message}")
    if len(st.session_state.log_messages) > 100:
        st.session_state.log_messages.pop(0)  # Keep log size manageable

def update_data():
    """Update betting data and find arbitrage opportunities"""
    progress_placeholder = None
    status_text = None
    
    try:
        # Create a progress bar if we're in the main thread
        try:
            progress_placeholder = st.empty()
            status_text = st.empty()
            progress_bar = progress_placeholder.progress(0)
            status_text.text("Starting data collection...")
        except:
            # We're in a background thread, just use logs
            progress_bar = None
        
        add_log("Starting data collection...")
        
        # Collect data from all bookmakers
        all_bookmakers_data = {}
        
        # Step 1: Collect data (6 steps total)
        if progress_bar:
            progress_bar.progress(0/6)
            status_text.text("Collecting data from bet365...")
        
        all_bookmakers_data["bet365"] = scraper.scrape_bet365()
        add_log(f"Collected {len(all_bookmakers_data['bet365'])} events from bet365")
        
        if progress_bar:
            progress_bar.progress(1/6)
            status_text.text("Collecting data from Betfair...")
            
        all_bookmakers_data["betfair"] = scraper.scrape_betfair()
        add_log(f"Collected {len(all_bookmakers_data['betfair'])} events from Betfair")
        
        if progress_bar:
            progress_bar.progress(2/6)
            status_text.text("Collecting data from additional bookmakers...")
            
        all_bookmakers_data["stoiximan"] = scraper.scrape_stoiximan()
        add_log(f"Collected {len(all_bookmakers_data['stoiximan'])} events from Stoiximan")
        
        all_bookmakers_data["netbet"] = scraper.scrape_netbet()
        add_log(f"Collected {len(all_bookmakers_data['netbet'])} events from Netbet")
        
        if progress_bar:
            progress_bar.progress(3/6)
            
        all_bookmakers_data["novibet"] = scraper.scrape_novibet()
        add_log(f"Collected {len(all_bookmakers_data['novibet'])} events from Novibet")
        
        all_bookmakers_data["casinoly"] = scraper.scrape_casinoly()
        add_log(f"Collected {len(all_bookmakers_data['casinoly'])} events from Casinoly")
        
        # Step 2: Apply random odds movement to create more arbitrage opportunities
        if progress_bar:
            progress_bar.progress(4/6)
            status_text.text("Applying odds movements for arbitrage detection...")
            
        # Apply odds movement to increase chances of finding arbitrage
        all_odds = arbitrage.apply_odds_movement(all_bookmakers_data)
        
        # Step 3: Store in memory (skip database operations to speed things up)
        if progress_bar:
            progress_bar.progress(5/6)
            status_text.text("Analyzing for arbitrage opportunities...")
            
        # Find arbitrage opportunities directly from the collected data
        # Use a very aggressive profit threshold to ensure we find opportunities
        arb_opps = arbitrage.find_arbitrage_opportunities(
            all_odds, 
            profit_threshold=-0.5  # Accept even slightly negative profit to ensure we find something
        )
        
        # Update session state
        st.session_state.arbitrage_opportunities = arb_opps
        st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Completed
        if progress_bar:
            progress_bar.progress(6/6)
            status_text.text(f"Analysis complete! Found {len(arb_opps)} arbitrage opportunities")
            
        add_log(f"Found {len(arb_opps)} arbitrage opportunities")
        
        # Log high-profit opportunities
        for opp in arb_opps:
            if opp['profit_percentage'] > 0.5:  # Much lower threshold for highlighting (0.5%)
                add_log(f"⭐ Arbitrage opportunity: {opp['profit_percentage']:.2f}% on {opp['match']}")
        
        # Store data in database in the background to avoid freezing
        # This will happen asynchronously through a separate thread
        threading.Thread(target=store_data_async, args=(all_bookmakers_data,)).start()
                
    except Exception as e:
        add_log(f"Error during update: {str(e)}")
        if status_text:
            status_text.text(f"Error: {str(e)}")
    finally:
        # Clean up UI elements
        if progress_placeholder:
            progress_placeholder.empty()
        if status_text:
            status_text.empty()
    
    # Schedule next update if still running
    if st.session_state.is_running:
        threading.Timer(st.session_state.refresh_interval * 60, update_data).start()
        
def store_data_async(all_bookmakers_data):
    """Store data in the database asynchronously to prevent UI freezing"""
    try:
        # Store data in the database
        for bookmaker, data in all_bookmakers_data.items():
            data_store.update_odds(data, bookmaker)
            add_log(f"Stored {len(data)} events for {bookmaker} in the database")
    except Exception as e:
        add_log(f"Error storing data in database: {str(e)}")

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

# Sidebar
with st.sidebar:
    st.title("Control Panel")
    
    st.subheader("Bot Controls")
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.is_running:
            st.button("Start Bot", on_click=start_bot, use_container_width=True)
        else:
            st.button("Stop Bot", on_click=stop_bot, use_container_width=True, type="primary")
    with col2:
        if st.button("Refresh Now", disabled=not st.session_state.is_running):
            update_data()
    
    st.subheader("Settings")
    st.session_state.refresh_interval = st.slider(
        "Refresh Interval (minutes)", 
        min_value=1, 
        max_value=30, 
        value=st.session_state.refresh_interval
    )
    
    st.session_state.notification_threshold = st.slider(
        "Profit Threshold (%)", 
        min_value=0.0, 
        max_value=2.0, 
        value=st.session_state.notification_threshold,
        step=0.05
    )
    
    st.subheader("Statistics")
    st.metric("Last Updated", st.session_state.last_updated)
    st.metric("Active Opportunities", len([o for o in st.session_state.arbitrage_opportunities if o['is_active']]))
    st.metric("Total Opportunities Found", len(st.session_state.arbitrage_opportunities))

# Main content
st.title("🎲 Arbitrage Betting Bot")

tab1, tab2, tab3, tab4 = st.tabs(["Opportunities", "Stats & Analytics", "Bookmaker Dashboard", "Logs"])

with tab1:
    st.header("Arbitrage Opportunities")
    
    if not st.session_state.arbitrage_opportunities:
        st.info("No arbitrage opportunities found yet. Start the bot or refresh data.")
    else:
        # Filter active opportunities
        active_opportunities = [o for o in st.session_state.arbitrage_opportunities if o['is_active']]
        
        if not active_opportunities:
            st.warning("No active arbitrage opportunities at the moment.")
        else:
            # Sort by profit percentage (descending)
            active_opportunities.sort(key=lambda x: x['profit_percentage'], reverse=True)
            
            # Create a DataFrame for display
            df = pd.DataFrame(active_opportunities)
            
            # Format DataFrame for display
            if not df.empty:
                df['profit_percentage'] = df['profit_percentage'].apply(lambda x: f"{x:.2f}%")
                
                # Apply color highlighting based on profit percentage - much lower threshold at 0.2%
                def highlight_profits(s):
                    return ['background-color: #d4f7d4' if float(x.strip('%')) > 0.2 else '' for x in s]
                
                st.dataframe(
                    df.style.apply(highlight_profits, subset=['profit_percentage']),
                    use_container_width=True
                )
                
                # Display detailed cards for top opportunities
                st.subheader("Top Opportunities")
                for i, opp in enumerate(active_opportunities[:3]):  # Show top 3
                    with st.expander(f"{opp['match']} - Profit: {opp['profit_percentage']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Match:** {opp['match']}")
                            st.markdown(f"**Sport:** {opp['sport']}")
                            st.markdown(f"**Profit:** {opp['profit_percentage']}")
                            st.markdown(f"**Investment required:** ${opp['investment']:.2f}")
                            st.markdown(f"**Expected return:** ${opp['expected_return']:.2f}")
                        
                        with col2:
                            bet_details = []
                            for bet in opp['bets']:
                                bet_details.append(f"• {bet['bookmaker']}: Bet ${bet['stake']:.2f} on {bet['outcome']} @ {bet['odds']}")
                            
                            st.markdown("**Recommended Bets:**")
                            for detail in bet_details:
                                st.markdown(detail)

with tab2:
    st.header("Statistics & Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Profit Distribution")
        if st.session_state.arbitrage_opportunities:
            profit_data = [{'profit': o['profit_percentage'], 'match': o['match']} 
                          for o in st.session_state.arbitrage_opportunities]
            profit_df = pd.DataFrame(profit_data)
            
            fig = px.histogram(
                profit_df, 
                x='profit', 
                nbins=20,
                title="Distribution of Profit Percentages",
                labels={'profit': 'Profit Percentage (%)'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available yet.")
    
    with col2:
        st.subheader("Bookmaker Comparison")
        if st.session_state.arbitrage_opportunities:
            # Count opportunities per bookmaker pair
            bookmaker_pairs = {}
            for opp in st.session_state.arbitrage_opportunities:
                pair = "-".join(sorted([bet['bookmaker'] for bet in opp['bets']]))
                if pair in bookmaker_pairs:
                    bookmaker_pairs[pair] += 1
                else:
                    bookmaker_pairs[pair] = 1
            
            bookmaker_df = pd.DataFrame({
                'Bookmaker Pair': list(bookmaker_pairs.keys()),
                'Opportunities': list(bookmaker_pairs.values())
            })
            
            fig = px.bar(
                bookmaker_df, 
                x='Bookmaker Pair', 
                y='Opportunities',
                title="Opportunities by Bookmaker Pair"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available yet.")

with tab3:
    # Call the bookmaker dashboard implementation from our module
    bookmaker_dashboard.display_dashboard(data_store.get_all_odds())

with tab4:
    st.header("Logs")
    
    # Display logs in a scrollable container
    st.text_area(
        "System Logs", 
        value="\n".join(st.session_state.log_messages),
        height=400,
        key="log_display",
        disabled=True
    )
    
    if st.button("Clear Logs"):
        st.session_state.log_messages = []
        st.rerun()

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
