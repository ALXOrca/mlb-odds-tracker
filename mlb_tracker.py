import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import numpy as np

#CONFIG
API_KEY = "87303cebb91e55cec0eea9aedb0ea50a"
SPORT = "baseball_mlb"
REGION = "us"
MARKETS = ["h2h", "totals", "spreads"]  # Moneyline, run totals, and run lines
POLL_INTERVAL = 300  # 5 minutes
MIN_EDGE = 0.05  # Minimum value edge for mispricing alerts

def ensure_db_schema(conn):
    """Ensure all tables have the correct schema"""
    # MLB Odds table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS mlb_odds (
        event_id TEXT,
        sport TEXT,
        commence_time TEXT,
        home_team TEXT,
        away_team TEXT,
        bookmaker TEXT,
        market_type TEXT,
        team_type TEXT,
        odds TEXT,
        point REAL,
        timestamp TEXT,
        PRIMARY KEY (event_id, bookmaker, market_type, team_type, timestamp)
    )
    """)
    
    # Mispricings table with all required columns
    conn.execute("""
    CREATE TABLE IF NOT EXISTS mispricings (
        timestamp TEXT,
        game_id TEXT,
        market_type TEXT,
        home_team TEXT,
        away_team TEXT,
        home_odds TEXT,
        away_odds TEXT,
        edge REAL,
        PRIMARY KEY (game_id, market_type, timestamp)
    )
    """)
    conn.commit()

def fetch_mlb_odds():
    """Fetch MLB odds with error handling"""
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGION,
        "markets": ",".join(MARKETS),
        "oddsFormat": "american"
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print(f"⚾ Found {len(data)} MLB games")
        return data
    except Exception as e:
        print(f"⚠️ API Error: {str(e)}")
        return None

def calculate_implied_probability(odds):
    """Convert American odds to implied probability"""
    if isinstance(odds, str):
        try:
            odds = int(odds)
        except ValueError:
            return None
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def find_mispricings(df):
    """Identify value betting opportunities"""
    mispricings = []

    for (game_id, market), group in df.groupby(['event_id', 'market_type']):
        if market == "h2h":
            home_odds = group[group['team_type'] == 'home']['odds']
            away_odds = group[group['team_type'] == 'away']['odds']
            
            if len(home_odds) > 0 and len(away_odds) > 0:
                best_home = home_odds.max()
                best_away = away_odds.max()
                
                home_prob = calculate_implied_probability(best_home)
                away_prob = calculate_implied_probability(best_away)
                
                if home_prob and away_prob:
                    total_prob = home_prob + away_prob
                    if total_prob < 1 - MIN_EDGE:
                        mispricings.append({
                            'game_id': game_id,
                            'market_type': market,
                            'home_team': group['home_team'].iloc[0],
                            'away_team': group['away_team'].iloc[0],
                            'home_odds': best_home,
                            'away_odds': best_away,
                            'edge': round((1 - total_prob) * 100, 2)
                        })
    
    return pd.DataFrame(mispricings)

def process_mlb_odds(data):
    if not data:
        return pd.DataFrame()
    
    processed = []
    for game in data:
        try:
            game_time = datetime.strptime(game["commence_time"], "%Y-%m-%dT%H:%M:%SZ")
            if game_time < datetime.now() - timedelta(hours=4):  # Skip completed games
                continue
        except:
            game_time = game.get("commence_time", "N/A")
        
        base_info = {
            "event_id": game["id"],
            "sport": "MLB",
            "commence_time": game_time.strftime("%Y-%m-%d %H:%M") if isinstance(game_time, datetime) else game_time,
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        for bookmaker in game.get("bookmakers", []):
            bookmaker_name = bookmaker.get("title", "Unknown")
            
            for market in bookmaker.get("markets", []):
                market_type = market["key"]
                
                for outcome in market["outcomes"]:
                    odds = outcome.get("price", "N/A")
                    
                    # Handle different market types
                    if market_type == "h2h":
                        record = {
                            **base_info,
                            "bookmaker": bookmaker_name,
                            "market_type": market_type,
                            "team_type": "home" if outcome["name"] == game["home_team"] else "away",
                            "odds": odds,
                            "point": None
                        }
                        processed.append(record)
                    
                    elif market_type == "totals":
                        record = {
                            **base_info,
                            "bookmaker": bookmaker_name,
                            "market_type": market_type,
                            "team_type": outcome["name"].lower(),  # over/under
                            "odds": odds,
                            "point": outcome.get("point")
                        }
                        processed.append(record)
                    
                    elif market_type == "spreads":
                        record = {
                            **base_info,
                            "bookmaker": bookmaker_name,
                            "market_type": market_type,
                            "team_type": "home" if outcome["name"] == game["home_team"] else "away",
                            "odds": odds,
                            "point": outcome.get("point")
                        }
                        processed.append(record)
    
    return pd.DataFrame(processed)

def simulate_bookmaker_risk(df):
    """Simulate bookmaker risk management"""
    risk_report = {}
    
    # Calculate exposure by game
    for game_id, group in df.groupby('event_id'):
        home_bets = group[(group['market_type'] == 'h2h') & (group['team_type'] == 'home')]
        away_bets = group[(group['market_type'] == 'h2h') & (group['team_type'] == 'away')]
        
        if not home_bets.empty and not away_bets.empty:
            risk_report[game_id] = {
                "game": f"{group['home_team'].iloc[0]} vs {group['away_team'].iloc[0]}",
                "home_exposure": len(home_bets),
                "away_exposure": len(away_bets),
                "net_exposure": len(home_bets) - len(away_bets),
                "worst_case_loss": calculate_worst_case(home_bets, away_bets)
            }
    
    return pd.DataFrame.from_dict(risk_report, orient='index')

def calculate_worst_case(home_bets, away_bets):
    """Calculate worst-case scenario loss"""
    max_home_odds = home_bets['odds'].max()
    max_away_odds = away_bets['odds'].max()
    
    if isinstance(max_home_odds, str) and max_home_odds.startswith('+'):
        home_payout = int(max_home_odds[1:])
    else:
        home_payout = 100
    
    if isinstance(max_away_odds, str) and max_away_odds.startswith('+'):
        away_payout = int(max_away_odds[1:])
    else:
        away_payout = 100
    
    return max(home_payout, away_payout)

def main():
    print("🚀 Starting MLB Odds Tracker with Bookmaker Simulation (Ctrl+C to stop)")
    conn = sqlite3.connect("mlb_odds.db")
    ensure_db_schema(conn)  # Ensure tables exist with correct schema
    
    try:
        while True:
            print(f"\n🔄 Checking for MLB odds at {datetime.now().strftime('%H:%M:%S')}...")
            data = fetch_mlb_odds()
            
            if data is None:
                print("🛑 Failed to fetch data. Will retry...")
                time.sleep(60)
                continue
                
            df = process_mlb_odds(data)
            
            if not df.empty:
                mispricings = find_mispricings(df)
                
                print("\n⚾ Current MLB Odds:")
                print("="*70)
                print(df[df['market_type'] == 'h2h'][['home_team', 'away_team', 'bookmaker', 'odds']]
                      .drop_duplicates().head(10).to_string(index=False))
                
                if not mispricings.empty:
                    print("\n💰 Value Betting Opportunities:")
                    print(mispricings[['home_team', 'away_team', 'home_odds', 'away_odds', 'edge']]
                          .to_string(index=False))
                    
                    # Add timestamp to mispricings before saving
                    mispricings['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    mispricings.to_sql("mispricings", conn, if_exists="append", index=False)
                
                df.to_sql("mlb_odds", conn, if_exists="append", index=False)
                print(f"\n✅ Saved {len(df)} odds entries to database")
            else:
                print("ℹ️ No MLB games with odds currently available")
            
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Tracker stopped by user")
    finally:
        conn.close()

if __name__ == "__main__":
    main()