import requests
import os
import json

url = "https://sportsbook.fanduel.com/cache/psmg/US/en/filters/888.json"
response = requests.get(url)
data = response.json()


# Let's inspect the first MMA event
mma_events = [
    event for event in data["events"] if "MMA" in event["eventGroup"]
]

print(json.dumps(mma_events[0], indent=2))  # Print the first event


ODDS_API_KEY = os.getenv("ODDS_API_KEY") or "87303cebb91e55cec0eea9aedb0ea50a"  # Replace with your actual API key if not using env var
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"

params = {
    "regions": "us",
    "markets": "h2h",
    "apiKey": ODDS_API_KEY,
    "bookmakers": "fanduel"
}

response = requests.get(ODDS_API_URL, params=params)

if response.status_code != 200:
    print(f"Failed to fetch odds: {response.status_code} - {response.text}")
else:
    data = response.json()
    print("Upcoming MMA fighters listed in FanDuel odds:\n")
    for event in data:
        fighters = event["fighters"]
        print(f"- Event: {event['home_team']} vs {event['away_team']}")
        print(f"  Fighters: {fighters}")
        print()
