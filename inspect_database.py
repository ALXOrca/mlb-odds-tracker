import sqlite3
import pandas as pd

def inspect_database():
    try:
        # Connect to the database
        conn = sqlite3.connect("mlb_odds.db")
        
        # 1. List all tables
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        print("📊 Database Tables:")
        print(tables)
        
        # 2. Show sample odds data
        if 'mlb_odds' in tables['name'].values:
            print("\n⚾ Recent MLB Odds:")
            odds = pd.read_sql("""
                SELECT home_team, away_team, bookmaker, odds, timestamp 
                FROM mlb_odds 
                WHERE market_type = 'h2h'
                ORDER BY timestamp DESC 
                LIMIT 5
            """, conn)
            print(odds)
        
        # 3. Show value bets
        if 'mispricings' in tables['name'].values:
            print("\n💰 Top Value Bets Found:")
            value_bets = pd.read_sql("""
                SELECT home_team, away_team, home_odds, away_odds, edge, timestamp
                FROM mispricings
                ORDER BY edge DESC
                LIMIT 5
            """, conn)
            print(value_bets)
            
    except Exception as e:
        print(f"⚠️ Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    inspect_database()