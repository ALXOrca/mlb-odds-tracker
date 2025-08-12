import requests

# --- CONFIG ---
API_KEY = "87303cebb91e55cec0eea9aedb0ea50a"  # ← Replace with your exact key (keep quotes!)
SPORT = "mma_mixed_martial_arts"
REGION = "us"

# --- TEST CALL ---
def test_api():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGION,
        "markets": "h2h"
    }
    
    print(f"🔍 Testing API Key: '{API_KEY[:5]}...{API_KEY[-5:]}'")  # Show partial key
    print(f"🌐 Request URL: {url}?apiKey=***®ions={REGION}&markets=h2h")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"🔄 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success! API Key is valid.")
            print(f"📊 Response Preview: {response.json()[0]['home_team']} vs {response.json()[0]['away_team']}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"🚨 Critical Error: {e}")

if __name__ == "__main__":
    test_api()