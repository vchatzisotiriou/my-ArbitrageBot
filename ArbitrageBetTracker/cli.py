#!/usr/bin/env python3

import argparse
import time
import logging
import sys
import os
import threading
from datetime import datetime

import scraper
import arbitrage
import data_store
import utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('arbitrage_bot.log')
    ]
)
logger = logging.getLogger('cli')

# Global flag for controlling the bot
running = False

def start_bot(refresh_interval, profit_threshold, max_runtime=None):
    """
    Start the arbitrage betting bot
    
    Args:
        refresh_interval (int): Interval in minutes to refresh data
        profit_threshold (float): Minimum profit percentage to alert
        max_runtime (int, optional): Maximum runtime in minutes. Defaults to None.
    """
    global running
    running = True
    
    start_time = time.time()
    
    print(f"\n{'='*80}")
    print(f"🎲 ARBITRAGE BETTING BOT STARTED")
    print(f"{'='*80}")
    print(f"Settings:")
    print(f"  - Refresh Interval: {refresh_interval} minutes")
    print(f"  - Profit Threshold: {profit_threshold}%")
    if max_runtime:
        print(f"  - Maximum Runtime: {max_runtime} minutes")
    print(f"{'='*80}\n")
    
    try:
        while running:
            # Check if max runtime is reached
            if max_runtime and (time.time() - start_time) / 60 >= max_runtime:
                logger.info(f"Maximum runtime of {max_runtime} minutes reached. Stopping bot.")
                print(f"\n{'='*80}")
                print(f"Maximum runtime of {max_runtime} minutes reached. Stopping bot.")
                print(f"{'='*80}\n")
                running = False
                break
            
            # Update data
            update_data(profit_threshold)
            
            # Sleep until next update
            if running:
                logger.info(f"Sleeping for {refresh_interval} minutes until next update")
                for i in range(refresh_interval * 60):
                    if not running:
                        break
                    time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print(f"\n{'='*80}")
        print(f"BOT STOPPED BY USER")
        print(f"{'='*80}\n")
        running = False
    
    except Exception as e:
        logger.error(f"Error in bot execution: {str(e)}")
        print(f"\n{'='*80}")
        print(f"ERROR: {str(e)}")
        print(f"{'='*80}\n")
        running = False

def update_data(profit_threshold):
    """
    Update betting data and find arbitrage opportunities
    
    Args:
        profit_threshold (float): Minimum profit percentage to alert
    """
    logger.info("Starting data collection...")
    print(f"\n📊 Collecting data at {datetime.now().strftime('%H:%M:%S')}...")
    
    try:
        # Collect data from bookmakers
        bet365_data = scraper.scrape_bet365()
        logger.info(f"Collected {len(bet365_data)} events from bet365")
        print(f"✓ Collected {len(bet365_data)} events from bet365")
        
        betfair_data = scraper.scrape_betfair()
        logger.info(f"Collected {len(betfair_data)} events from Betfair")
        print(f"✓ Collected {len(betfair_data)} events from Betfair")
        
        stoiximan_data = scraper.scrape_stoiximan()
        logger.info(f"Collected {len(stoiximan_data)} events from Stoiximan")
        print(f"✓ Collected {len(stoiximan_data)} events from Stoiximan")
        
        netbet_data = scraper.scrape_netbet()
        logger.info(f"Collected {len(netbet_data)} events from Netbet")
        print(f"✓ Collected {len(netbet_data)} events from Netbet")
        
        novibet_data = scraper.scrape_novibet()
        logger.info(f"Collected {len(novibet_data)} events from Novibet")
        print(f"✓ Collected {len(novibet_data)} events from Novibet")
        
        casinoly_data = scraper.scrape_casinoly()
        logger.info(f"Collected {len(casinoly_data)} events from Casinoly")
        print(f"✓ Collected {len(casinoly_data)} events from Casinoly")
        
        # Store data
        data_store.update_odds(bet365_data, "bet365")
        data_store.update_odds(betfair_data, "betfair")
        data_store.update_odds(stoiximan_data, "stoiximan")
        data_store.update_odds(netbet_data, "netbet")
        data_store.update_odds(novibet_data, "novibet")
        data_store.update_odds(casinoly_data, "casinoly")
        
        # Find arbitrage opportunities
        arb_opps = arbitrage.find_arbitrage_opportunities(
            data_store.get_all_odds(), 
            profit_threshold
        )
        
        # Update stored opportunities
        data_store.update_arbitrage_opportunities(arb_opps)
        
        print(f"🔍 Analysis complete: Found {len(arb_opps)} arbitrage opportunities")
        
        # Display opportunities
        if arb_opps:
            print(f"\n{'='*80}")
            print(f"💰 ARBITRAGE OPPORTUNITIES FOUND")
            print(f"{'='*80}")
            
            for i, opp in enumerate(arb_opps[:5]):  # Show top 5 opportunities
                print(f"\nOpportunity #{i+1}: {opp['match']}")
                print(f"  Sport/League: {opp['sport']} / {opp['league']}")
                print(f"  Profit: {opp['profit_percentage']:.2f}%")
                print(f"  Required Investment: ${opp['investment']:.2f}")
                print(f"  Expected Return: ${opp['expected_return']:.2f}")
                print(f"  Start Time: {opp['start_time']}")
                print(f"  Recommended Bets:")
                
                for bet in opp['bets']:
                    print(f"    • {bet['bookmaker']}: Bet ${bet['stake']:.2f} on {bet['outcome']} @ {bet['odds']}")
            
            if len(arb_opps) > 5:
                print(f"\n... and {len(arb_opps) - 5} more opportunities")
            
            print(f"{'='*80}")
        else:
            print("No arbitrage opportunities found above the profit threshold")
    
    except Exception as e:
        logger.error(f"Error during update: {str(e)}")
        print(f"❌ Error during update: {str(e)}")

def stop_bot():
    """Stop the arbitrage betting bot"""
    global running
    running = False
    logger.info("Bot stopped")

def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="Arbitrage Betting Bot CLI")
    parser.add_argument("--interval", type=int, default=5, help="Refresh interval in minutes (default: 5)")
    parser.add_argument("--threshold", type=float, default=1.0, help="Profit threshold percentage (default: 1.0)")
    parser.add_argument("--runtime", type=int, help="Maximum runtime in minutes (optional)")
    parser.add_argument("--dashboard", action="store_true", help="Launch the Streamlit dashboard")
    args = parser.parse_args()
    
    if args.dashboard:
        try:
            import subprocess
            print(f"\n{'='*80}")
            print(f"Launching Streamlit Dashboard...")
            print(f"{'='*80}\n")
            subprocess.Popen(["streamlit", "run", "app.py", "--server.port", "5000"])
            return
        except Exception as e:
            logger.error(f"Error launching dashboard: {str(e)}")
            print(f"Error launching dashboard: {str(e)}")
            print("Falling back to CLI mode")
    
    # Print welcome message
    print(f"\n{'='*80}")
    print(f"🎲 ARBITRAGE BETTING BOT CLI")
    print(f"{'='*80}")
    print("Welcome to the Arbitrage Betting Bot!")
    print("This bot identifies risk-free betting opportunities across multiple bookmakers.")
    print(f"{'='*80}\n")
    
    # Start the bot
    bot_thread = threading.Thread(
        target=start_bot,
        args=(args.interval, args.threshold, args.runtime)
    )
    bot_thread.daemon = True
    bot_thread.start()
    
    try:
        while bot_thread.is_alive():
            bot_thread.join(1)
    except KeyboardInterrupt:
        stop_bot()
        print("\nBot stopped. Exiting...")

if __name__ == "__main__":
    main()
