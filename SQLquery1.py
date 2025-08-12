import sqlite3
import pandas as pd


conn = sqlite3.connect("mlb_odds.db")

#Show all tables
print(pd.read_sql("SELECT name FROM sqlite_master WHERE type='table", conn))

#Sample query
df = pd.read_sql("""
SELECT home_team, away_team, bookmaker, odds, timestamp 
FROM mlb_odds 
WHERE market_type = 'h2h' 
ORDER BY timestamp DESC 
LIMIT 10
""", conn)
print(df)

conn.close()

