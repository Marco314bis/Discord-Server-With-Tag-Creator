import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Optional, List
from threading import Lock

from curl_cffi import requests # Using curl_cffi because discord doesn't allow guild creation with the requests library because of its flagged TLS

FOUND_FILE = 'found_guilds.json'
TOKENS = [] # Put your tokens here. Don't use tokens with 2FA enabled, it won't work
MIN_DELAY, MAX_DELAY = (8, 15) # Delay between requests to avoid rate limits. You can change the delay to a lower value if you want but be careful with rate limits and bans

file_lock = Lock()


def load_found() -> List[Dict]:
    try:
        with open(FOUND_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_found(entry: Dict):
    with file_lock:
        data = load_found()
        data.append(entry)
        with open(FOUND_FILE, 'w') as f:
            json.dump(data, f, indent=2)


def murmurhash_v3(key, seed=0):
    """Implementation of MurmurHash v3 algorithm (thanks to Claude for this)"""
    c1 = 0xcc9e2d51
    c2 = 0x1b873593

    h1 = seed

    key_bytes = key.encode('utf-8')
    length = len(key_bytes)
    blocks = length // 4

    for i in range(blocks):
        k1 = (key_bytes[i*4] |
              (key_bytes[i*4 + 1] << 8) |
              (key_bytes[i*4 + 2] << 16) |
              (key_bytes[i*4 + 3] << 24))

        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff

        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xffffffff
        h1 = (h1 * 5 + 0xe6546b64) & 0xffffffff

    k1 = 0
    remaining = length % 4

    if remaining >= 3:
        k1 ^= key_bytes[blocks*4 + 2] << 16
    if remaining >= 2:
        k1 ^= key_bytes[blocks*4 + 1] << 8
    if remaining >= 1:
        k1 ^= key_bytes[blocks*4]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1

    h1 ^= length
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85ebca6b) & 0xffffffff
    h1 ^= h1 >> 13
    h1 = (h1 * 0xc2b2ae35) & 0xffffffff
    h1 ^= h1 >> 16

    return h1 & 0xffffffff


class DiscordServerCreator:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0", # Static user agent and super properties because this doesn't really matter, but you can improve that if you want to
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRmlyZWZveCIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJmciIsImhhc19jbGllbnRfbW9kcyI6ZmFsc2UsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQ7IHJ2OjEzOC4wKSBHZWNrby8yMDEwMDEwMSBGaXJlZm94LzEzOC4wIiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTM4LjAiLCJvc192ZXJzaW9uIjoiMTAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6Mzk2ODU4LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJjbGllbnRfbGF1bmNoX2lkIjoiMjY3NTAxZjYtYmViNS00NjY5LTllMmQtZWY1ZjA4NzdlMTUxIiwiY2xpZW50X2hlYXJ0YmVhdF9zZXNzaW9uX2lkIjoiM2FkMzI4OWEtNDRlNC00YWJjLWIyNjMtZjExM2I0MTU5MmQzIn0="
        }
        self.api_url = "https://discord.com/api/v9"

    def log(self, message: str):
        print(f"[{self.token.split('.')[0]}] [{datetime.now().strftime('%H:%M:%S')}] {message}")

    def create_server(self, name: str) -> Optional[Dict]:
        resp = requests.post(
            url=f"{self.api_url}/guilds",
            headers=self.headers,
            data=json.dumps({
                "channels": [],
                "guild_template_code": "2TffvPucqHkN",
                "icon": None,
                "name": name,
                "system_channel_id": None
                }
            )
        )
        resp.raise_for_status()
        if resp.status_code == 201:
            return resp.json()

    def delete_server(self, server_id: str) -> bool:
        url = f"{self.api_url}/guilds/{server_id}"
        resp = requests.delete(url, headers=self.headers)
        resp.raise_for_status()
        return resp.status_code == 204


def find_guild_for_token(token: str, max_attempts: int = None) -> Optional[Dict]:
    creator = DiscordServerCreator(token)
    attempts = 0
    time.sleep(random.randint(1, 15))

    while True:
        attempts += 1
        if max_attempts and attempts > max_attempts:
            break

        name = f"Server-{random.randint(1000,9999)}"
        server = creator.create_server(name)
        if not server:
            creator.log("Can't create guilds, exiting.") # No error handling because i didn't care about it, but you can improve that if you want to
            return

        sid = server['id']
        experiment_key = f"2025-02_skill_trees:{sid}"
        hash_value = murmurhash_v3(experiment_key) % 10000
        if 10 <= hash_value < 20:
            entry = {'token': token, 'server_id': sid, 'name': name}
            save_found(entry)
            return entry # if you prefer to continue trying with this token, you can remove this line

        time.sleep(4)

        if creator.delete_server(sid):
            creator.log(f"Created and deleted server without tag feature {sid}")
            time.sleep(random.randint(MIN_DELAY, MAX_DELAY))
        else:
            creator.log("Can't delete guilds, exiting.") # Still no error handling here
            return


def main(tokens: List[str]):
    results = []
    with ThreadPoolExecutor(max_workers=len(tokens)) as executor:
        futures = {executor.submit(find_guild_for_token, tok): tok for tok in tokens}
        for future in as_completed(futures):
            tok = futures[future]
            try:
                res = future.result()
                if res:
                    print(f"Token {tok} found guild {res['server_id']}")
                    results.append(res)
            except Exception as e:
                print(f"Error for token {tok}: {e}")
    print("All tasks completed.")
    return results


if __name__ == '__main__':
    found = main(TOKENS)
    print(json.dumps(found, indent=2))
