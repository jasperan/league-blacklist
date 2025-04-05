import pandas as pd
import os
import json
from riotwatcher import LolWatcher, ApiError
from datetime import datetime
from pprint import PrettyPrinter

# Create a PrettyPrinter instance with custom settings
pp = PrettyPrinter(indent=2, width=80, depth=None, sort_dicts=False)
# Override print with our pretty printer
print = pp.pprint

class BlacklistManager:
    def __init__(self, api_key=None, region="na1"):
        self.api_key = api_key
        self.region = region.lower()
        
        # Map region to platform and continent
        self.region_to_platform = {
            "na1": "na1", "euw1": "euw1", "eun1": "eun1", "kr": "kr",
            "br1": "br1", "jp1": "jp1", "la1": "la1", "la2": "la2",
            "oc1": "oc1", "tr1": "tr1", "ru": "ru"
        }
        
        self.region_to_continent = {
            "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
            "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
            "kr": "asia", "jp1": "asia", "oc1": "sea"
        }
        
        self.platform = self.region_to_platform.get(self.region, "na1")
        self.continent = self.region_to_continent.get(self.region, "americas")
        
        self.blacklist_file = "blacklist.csv"
        self.puuid_cache_file = "puuid_cache.json"
        
        # Initialize Riot Watcher
        if api_key:
            self.watcher = LolWatcher(api_key)
        else:
            self.watcher = None
            
        # Create blacklist file if it doesn't exist
        if not os.path.exists(self.blacklist_file):
            # Initialize empty blacklist dataframe
            self.blacklist_df = pd.DataFrame(columns=['summoner_id', 'summoner_name', 'reason', 'date_added', 'tagline'])
            # Save to file
            self.blacklist_df.to_csv(self.blacklist_file, index=False)
        else:
            # Load existing blacklist
            try:
                self.blacklist_df = pd.read_csv(self.blacklist_file)
                print(f"Loaded blacklist with {len(self.blacklist_df)} entries")
            except Exception as e:
                print(f"Error loading blacklist: {str(e)}")
                self.blacklist_df = pd.DataFrame(columns=['summoner_id', 'summoner_name', 'reason', 'date_added', 'tagline'])
        
        # Load or create PUUID cache
        if os.path.exists(self.puuid_cache_file):
            try:
                with open(self.puuid_cache_file, 'r') as f:
                    self.puuid_cache = json.load(f)
            except:
                self.puuid_cache = {}
        else:
            self.puuid_cache = {}
    
    def _save_puuid_cache(self):
        """Save the PUUID cache to file"""
        with open(self.puuid_cache_file, 'w') as f:
            json.dump(self.puuid_cache, f)
    
    def get_summoner(self, summoner_name, tagline):
        """Get summoner by name and tagline"""
        try:
            # Handle potential hashtag format
            if '#' in summoner_name:
                parts = summoner_name.split('#')
                summoner_name = parts[0]
                tagline = parts[1]
            
            # Default to region's default tagline if not provided
            if not tagline:
                region_to_tagline = {
                    "na1": "NA1", "euw1": "EUW1", "eun1": "EUN1", "kr": "KR",
                    "br1": "BR1", "jp1": "JP1", "la1": "LA1", "la2": "LA2",
                    "oc1": "OC1", "tr1": "TR1", "ru": "RU"
                }
                tagline = region_to_tagline.get(self.region, "NA1")
            
            # Check if summoner is in cache
            cache_key = f"{summoner_name.lower()}#{tagline.lower()}"
            if cache_key in self.puuid_cache:
                puuid = self.puuid_cache[cache_key]
                print(f"Using cached PUUID for {summoner_name}#{tagline}: {puuid}")
                
                # Get summoner by PUUID using Riot API
                summoner = self.watcher.summoner.by_puuid(self.platform, puuid)
                
                # Add additional info to summoner data
                summoner['tagline'] = tagline
                summoner['gameName'] = summoner_name
                summoner['name'] = summoner_name  # Ensure name field exists for backward compatibility
                
                print(f"Summoner data: {summoner.keys()}")
                return summoner
            
            # Use Riot account-v1 API to get account info
            endpoint = f"https://{self.continent}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}"
            print(f"Calling endpoint: {endpoint}")
            
            account = self.watcher.account.by_riot_id(self.continent, summoner_name, tagline)
            print(f"Found account: {account}")
            
            # Get summoner by PUUID
            endpoint = f"https://{self.platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{account['puuid']}"
            print(f"Calling endpoint: {endpoint}")
            
            summoner = self.watcher.summoner.by_puuid(self.platform, account['puuid'])
            
            # Add Riot ID info to summoner data
            summoner['tagline'] = tagline 
            summoner['gameName'] = summoner_name
            summoner['name'] = summoner_name  # Ensure name field exists for backward compatibility
            
            # Cache the PUUID for future use
            self.puuid_cache[cache_key] = account['puuid']
            self._save_puuid_cache()
            print(f"Cached PUUID for {summoner_name}#{tagline}: {account['puuid']}")
            
            print(f"Summoner data: {summoner.keys()}")
            return summoner
            
        except ApiError as e:
            print(f"API Error: {e.response.status_code}")
            raise Exception(f"Could not find summoner '{summoner_name}#{tagline}' in region {self.region}: {str(e)}")
        except Exception as e:
            print(f"Error getting summoner: {e}")
            raise Exception(f"Could not find summoner '{summoner_name}#{tagline}' in region {self.region}: {str(e)}")
    
    def get_match_history(self, summoner, limit=5, start=0):
        """Get match history for a summoner."""
        try:
            puuid = summoner['puuid']
            endpoint = f"https://{self.continent}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
            print(f"Calling endpoint: {endpoint}?start={start}&count={limit}")
            
            # Get match IDs
            match_ids = self.watcher.match.matchlist_by_puuid(
                region=self.continent,
                puuid=puuid,
                start=start,
                count=limit
            )
            
            print(f"Retrieved {len(match_ids)} matches: {match_ids}")
            return match_ids
            
        except ApiError as e:
            print(f"API Error: {e.response.status_code}")
            raise Exception(f"Error retrieving match history: {str(e)}")
        except Exception as e:
            print(f"Match history error: {str(e)}")
            raise Exception(f"Error retrieving match history: {str(e)}")
    
    def get_match_details(self, match_id):
        """Get match details by match ID"""
        try:
            endpoint = f"https://{self.continent}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            print(f"Calling endpoint: {endpoint}")
            
            # Get match details
            match = self.watcher.match.by_id(region=self.continent, match_id=match_id)
            
            # Extract participant information
            participants = []
            for participant in match['info']['participants']:
                # Extract summoner name - make sure it's not empty
                summoner_name = participant.get('summonerName', 'Unknown')
                if not summoner_name or summoner_name == 'Unknown':
                    # Try alternate fields that might contain the name
                    summoner_name = participant.get('riotIdGameName', 
                                    participant.get('playerName', 
                                    participant.get('name', 'Unknown Player')))
                
                # Create participant info with all required fields
                participant_info = {
                    'summoner_id': participant.get('summonerId', ''),
                    'summoner_name': summoner_name,  # Use the extracted name
                    'champion': participant.get('championName', participant.get('championId', 'Unknown')),
                    'team': 'Blue' if participant['teamId'] == 100 else 'Red',
                    'tagline': participant.get('riotIdTagline', '')
                }
                participants.append(participant_info)
            
            print(f"Retrieved details for match {match_id} with {len(participants)} participants")
            print(f"Participant names: {[p['summoner_name'] for p in participants]}")
            
            return match, participants
            
        except ApiError as e:
            print(f"API Error: {e.response.status_code}")
            raise Exception(f"Error retrieving match details: {str(e)}")
        except Exception as e:
            print(f"Match details error for {match_id}: {str(e)}")
            raise Exception(f"Error retrieving match details: {str(e)}")
    
    def get_current_match(self, summoner):
        """Get current match information for a summoner"""
        try:
            # Use PUUID to get current match (v5 API uses PUUID instead of summoner ID)
            puuid = summoner['puuid']
            endpoint = f"https://{self.platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
            print(f"Calling endpoint: {endpoint}")
            
            # Call the by_summoner method with PUUID
            current_match = self.watcher.spectator.by_summoner(self.platform, puuid)
            return current_match
        except ApiError as e:
            if e.response.status_code == 404:
                print(f"Summoner is not in an active game")
                return None
            elif e.response.status_code == 400:
                print(f"User is currently not in a game.")
                return None
            else:
                print(f"API Error: {e.response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting current match: {e}")
            return None
    
    def add_to_blacklist(self, summoner_id, summoner_name, reason="", tagline=""):
        """Add a player to the blacklist"""
        try:
            # First check if player is already blacklisted
            if self.is_blacklisted(summoner_id):
                print(f"Player {summoner_name} is already blacklisted")
                return False, "Player is already in your blacklist"
            
            # Create a new row with the blacklist data
            new_row = {
                'summoner_id': summoner_id,
                'summoner_name': summoner_name,
                'reason': reason,
                'date_added': pd.Timestamp.now(),
                'tagline': tagline
            }
            
            # Add the new row to the dataframe
            self.blacklist_df = pd.concat([self.blacklist_df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save the updated blacklist
            self._save_blacklist()
            
            print(f"Added {summoner_name} to blacklist")
            return True, f"Added {summoner_name} to blacklist"
        except Exception as e:
            print(f"Error adding to blacklist: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def remove_from_blacklist(self, summoner_id):
        """Remove a player from the blacklist"""
        try:
            # Get current blacklist
            if not self.is_blacklisted(summoner_id):
                print(f"Player with ID {summoner_id} is not in blacklist")
                return False
            
            # Use the in-memory dataframe
            self.blacklist_df = self.blacklist_df[self.blacklist_df['summoner_id'] != summoner_id]
            
            # Save changes to file
            success = self._save_blacklist()
            if success:
                print(f"Removed player with ID {summoner_id} from blacklist")
            return success
        except Exception as e:
            print(f"Error removing from blacklist: {str(e)}")
            return False
    
    def get_blacklist(self):
        """Get the entire blacklist"""
        # Make sure we have the most up-to-date blacklist data
        if not hasattr(self, 'blacklist_df') or self.blacklist_df is None:
            if not os.path.exists(self.blacklist_file) or os.stat(self.blacklist_file).st_size == 0:
                self.blacklist_df = pd.DataFrame(columns=['summoner_id', 'summoner_name', 'reason', 'date_added', 'tagline'])
            else:
                self.blacklist_df = pd.read_csv(self.blacklist_file)
        
        return self.blacklist_df
    
    def is_blacklisted(self, summoner_id):
        """Check if a player is blacklisted"""
        # Get current blacklist
        blacklist = self.get_blacklist()
        
        # Check if the summoner ID is in the blacklist
        is_in_blacklist = summoner_id in blacklist['summoner_id'].values
        return is_in_blacklist
    
    def check_current_match_for_blacklisted(self, summoner):
        """Check if any players in current match are blacklisted"""
        current_match = self.get_current_match(summoner)
        if not current_match:
            return []
        
        blacklisted_players = []
        blacklist = self.get_blacklist()
        
        # Debug: print participant fields
        if 'participants' in current_match and len(current_match['participants']) > 0:
            first_player = current_match['participants'][0]
            print(f"Live match participant fields: {list(first_player.keys())}")
        
        # Check all participants
        for participant in current_match['participants']:
            # Extract summoner ID - spectator v5 uses different field names
            summoner_id = participant.get('summonerId', participant.get('id', ''))
            
            # Get summoner name - spectator v5 uses different field names
            summoner_name = participant.get('summonerName', 
                           participant.get('name', 
                           participant.get('riotIdGameName', 'Unknown Player')))
            
            if summoner_id in blacklist['summoner_id'].values:
                blacklisted_info = blacklist[blacklist['summoner_id'] == summoner_id].iloc[0]
                
                # Get champion information - use name if available, otherwise ID
                champion = participant.get('championName', participant.get('championId', 'Unknown'))
                
                # Get tagline if available
                tagline = blacklisted_info.get('tagline', '')
                tag_display = f"#{tagline}" if tagline else ""
                
                blacklisted_players.append({
                    'summoner_id': summoner_id,
                    'summoner_name': f"{summoner_name}{tag_display}",
                    'champion': champion,
                    'reason': blacklisted_info['reason'],
                    'date_added': blacklisted_info['date_added']
                })
                
        return blacklisted_players
    
    def _save_blacklist(self):
        """Save the blacklist dataframe to file"""
        try:
            # Make sure the blacklist_df attribute exists, load it from file if not
            if not hasattr(self, 'blacklist_df') or self.blacklist_df is None:
                if os.path.exists(self.blacklist_file):
                    self.blacklist_df = pd.read_csv(self.blacklist_file)
                else:
                    self.blacklist_df = pd.DataFrame(columns=['summoner_id', 'summoner_name', 'reason', 'date_added', 'tagline'])
            
            # Save the dataframe to CSV
            self.blacklist_df.to_csv(self.blacklist_file, index=False)
            print(f"Blacklist saved to {self.blacklist_file}")
            return True
        except Exception as e:
            print(f"Error saving blacklist: {str(e)}")
            return False 