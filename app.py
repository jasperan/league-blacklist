import streamlit as st
import pandas as pd
import time
from blacklist_manager import BlacklistManager
from config import save_config, load_config
from pprint import PrettyPrinter

# Configure page - must be the first st command
st.set_page_config(
    page_title="League of Legends Blacklist",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# League of Legends Blacklist System\nTrack and manage players you want to avoid in your games."
    }
)

# Enable auto-reload
if not st.session_state.get("auto_reload_enabled"):
    st.cache_data.clear()
    st.session_state.auto_reload_enabled = True

# Create pretty printer
pp = PrettyPrinter(indent=2, width=80, depth=None, sort_dicts=False)
print = pp.pprint

# Initialize session state variables
if 'blacklist_manager' not in st.session_state:
    st.session_state.blacklist_manager = None
if 'summoner' not in st.session_state:
    st.session_state.summoner = None
if 'match_history' not in st.session_state:
    st.session_state.match_history = None
if 'selected_match' not in st.session_state:
    st.session_state.selected_match = None

# Initialize session state for tracking blacklist forms
if 'blacklist_forms' not in st.session_state:
    st.session_state.blacklist_forms = {}

# Functions for search and display
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_match_details_cached(_blacklist_manager, match_id):
    """Get cached match details with the blacklist_manager object excluded from hashing.
    
    Parameters:
        _blacklist_manager: BlacklistManager instance (not hashed by Streamlit)
        match_id: The match ID to retrieve details for
        
    Returns:
        tuple: (match_data, participants)
    """
    return _blacklist_manager.get_match_details(match_id)

def search_summoner(manager, name, tag, save=True, api_key=None, region=None):
    """Search for a summoner and their match history"""
    with st.spinner("Fetching summoner data..."):
        st.session_state.summoner = manager.get_summoner(name, tag)
        
        # Save last used summoner info if preferences are set to save
        if save and api_key and region:
            save_config(api_key, region, name, tag)
    
    with st.spinner("Retrieving match history..."):
        # Get the 5 most recent matches
        matches = manager.get_match_history(
            st.session_state.summoner,
            limit=5,
            start=0
        )
        st.session_state.match_history = matches
        return matches

def display_players(players, team_name):
    st.subheader(f"{team_name} Team")
    
    # Debug information - show first player's data
    if players and len(players) > 0:
        st.text(f"Debug - First player data: {players[0]}")
    
    # Create a table for all players
    for i, player in enumerate(players):
        # Ensure we have the summoner name
        summoner_name = player.get('summoner_name', 'Unknown Player')
        tagline = player.get('tagline', '')
        champion = player.get('champion', 'Unknown')
        
        # Build the display text
        tag_display = f"#{tagline}" if tagline else ""
        display_text = f"{summoner_name}{tag_display} - {champion}"
        
        # Create a simple container for this player
        with st.container():
            # Display player info and buttons side by side
            left, middle, right = st.columns([3, 1, 1])
            
            # Display player info
            left.markdown(f"**{display_text}**")
            
            # Blacklist/Remove buttons
            player_id = player.get('summoner_id', '')
            blacklist_manager = st.session_state.blacklist_manager
            
            if player_id and not blacklist_manager.is_blacklisted(player_id):
                if middle.button("Blacklist", key=f"blacklist_{player_id}"):
                    st.session_state.player_to_blacklist = {
                        'id': player_id,
                        'name': summoner_name,
                        'tagline': tagline
                    }
                    st.rerun()
            
            # Remove button if already blacklisted
            elif player_id and blacklist_manager.is_blacklisted(player_id):
                if right.button("Remove", key=f"remove_{player_id}"):
                    blacklist_manager.remove_from_blacklist(player_id)
                    st.success(f"Removed {summoner_name} from blacklist")
                    st.rerun()

def add_to_blacklist(summoner_id, summoner_name, tagline, reason):
    """Add a player to blacklist and show success message"""
    success, message = st.session_state.blacklist_manager.add_to_blacklist(
        summoner_id=summoner_id,
        summoner_name=summoner_name,
        reason=reason,
        tagline=tagline
    )
    if success:
        st.success(message)
        return True
    else:
        st.warning(message)  # Use warning instead of error for already blacklisted
        return False

def remove_from_blacklist(summoner_id, summoner_name):
    """Remove a player from blacklist and show success message"""
    if st.session_state.blacklist_manager.remove_from_blacklist(summoner_id):
        st.success(f"{summoner_name} removed from blacklist")
        st.rerun()
    else:
        st.error("Failed to remove from blacklist")

def cancel_blacklist(session_key):
    """Cancel the blacklist operation by removing the session state key"""
    if session_key in st.session_state:
        del st.session_state[session_key]
    st.rerun()

def main():
    st.title("League of Legends Blacklist System")
    
    # Load saved configuration values
    api_key, region, last_username, last_tagline = load_config()
    
    # Sidebar for user input
    with st.sidebar:
        with st.expander("API Settings", expanded=True):
            # API Key input
            api_key_input = st.text_input("Riot API Key", value=api_key if api_key else "", 
                                       type="password", help="Enter your Riot API Key")
            
            # Region selection
            region_options = {
                "NA1": "North America", 
                "EUW1": "Europe West",
                "EUN1": "Europe Nordic & East",
                "KR": "Korea",
                "BR1": "Brazil",
                "JP1": "Japan",
                "LA1": "Latin America North",
                "LA2": "Latin America South",
                "OC1": "Oceania",
                "TR1": "Turkey",
                "RU": "Russia"
            }
            
            region_input = st.selectbox(
                "Region", 
                options=list(region_options.keys()),
                format_func=lambda x: region_options.get(x, x),
                index=list(region_options.keys()).index(region) if region in region_options else 0
            )
            
            # Save preferences checkbox
            save_preferences = st.checkbox("Save preferences", value=True)
            
            # Save button
            if st.button("Save Settings", use_container_width=True, type="primary"):
                if api_key_input:
                    if save_preferences:
                        save_config(api_key_input, region_input, last_username, last_tagline)
                        st.success("Settings saved!")
                    
                    # Initialize blacklist manager
                    st.session_state.blacklist_manager = BlacklistManager(api_key=api_key_input, region=region_input)
                    st.success("Blacklist Manager initialized!")
                else:
                    st.error("Please enter your Riot API Key")
        
        st.divider()
        
        # Summoner search section
        st.subheader("Summoner Search")
        
        # Text inputs for summoner name and tagline
        with st.form(key="search_form"):
            summoner_name = st.text_input("Summoner Name", value=last_username if last_username else "",
                                       placeholder="Enter a summoner name")
            tagline = st.text_input("Tagline", value=last_tagline if last_tagline else "",
                                 placeholder="EUW, NA, etc.")
            
            search_button = st.form_submit_button("Search", use_container_width=True, type="primary")
        
        if search_button:
            if not st.session_state.blacklist_manager:
                if api_key_input:
                    st.session_state.blacklist_manager = BlacklistManager(api_key=api_key_input, region=region_input)
                else:
                    st.error("Please set up your API key first")
                    st.stop()
            
            if summoner_name:
                try:
                    matches = search_summoner(
                        st.session_state.blacklist_manager, 
                        summoner_name, 
                        tagline, 
                        save_preferences,
                        api_key_input,
                        region_input
                    )
                    
                    if not matches:
                        st.warning("No matches found. This might be because of API limitations or the account has no recent matches.")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.summoner = None
                    st.session_state.match_history = None
            else:
                st.error("Please enter a summoner name")
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Matches", "📑 Blacklist", "🔍 Live Game Checker", "ℹ️ Help"])
    
    with tab1:
        # Display summoner info and match history
        if st.session_state.summoner:
            summoner = st.session_state.summoner
            
            # Display summoner name (using different key based on the API response)
            if 'name' in summoner:
                summoner_name = summoner['name']
            elif 'gameName' in summoner:
                summoner_name = summoner['gameName']
            else:
                summoner_name = "Unknown"
            
            # Create a profile card for the summoner
            with st.container():
                col_profile, col_status, col_refresh = st.columns([3, 1, 1])
                
                with col_profile:
                    st.subheader(f"Summoner: {summoner_name}")
                    
                    # Display summoner details
                    if 'summonerLevel' in summoner:
                        st.markdown(f"**Level:** {summoner['summonerLevel']}")
                
                with col_status:
                    # Check if the summoner is blacklisted
                    if 'id' in summoner and st.session_state.blacklist_manager.is_blacklisted(summoner['id']):
                        st.warning("⚠️ This summoner is in your blacklist!")
                
                with col_refresh:
                    # Add refresh button
                    if st.button("🔄 Refresh Matches", use_container_width=True):
                        with st.spinner("Retrieving match history..."):
                            # Get the 5 most recent matches
                            matches = st.session_state.blacklist_manager.get_match_history(
                                st.session_state.summoner,
                                limit=5,
                                start=0
                            )
                            st.session_state.match_history = matches
                            st.rerun()
            
            # Display match history
            if st.session_state.get('match_history'):
                with st.spinner("Retrieving match details..."):
                    matches = st.session_state.match_history
                    
                    if matches:
                        st.subheader("Recent Matches")
                        
                        # Display each match in an expander
                        for i, match_id in enumerate(matches):
                            with st.expander(f"Match {i+1}: {match_id}", expanded=(i==0)):
                                try:
                                    # Get match details with participants using the cached function
                                    match, participants = get_match_details_cached(_blacklist_manager=st.session_state.blacklist_manager, match_id=match_id)
                                    
                                    # Group participants by team
                                    blue_team = [p for p in participants if p['team'] == 'Blue']
                                    red_team = [p for p in participants if p['team'] == 'Red']
                                    
                                    # Display match details
                                    st.markdown(f"### Match Participants")
                                    
                                    # Use columns for teams
                                    team_cols = st.columns(2)
                                    
                                    with team_cols[0]:
                                        st.markdown("#### Blue Team")
                                        for player in blue_team:
                                            # Get player info
                                            summoner_name = player.get('summoner_name', 'Unknown Player')
                                            tagline = player.get('tagline', '')
                                            champion = player.get('champion', 'Unknown')
                                            player_id = player.get('summoner_id', '')
                                            
                                            # Form key for this player
                                            form_key = f"form_{player_id}_{i}_blue"
                                            
                                            # Show if blacklisted
                                            is_blacklisted = st.session_state.blacklist_manager.is_blacklisted(player_id)
                                            prefix = "⚠️ " if is_blacklisted else ""
                                            tag_display = f"#{tagline}" if tagline else ""
                                            
                                            # Display player with action buttons
                                            col1, col2 = st.columns([3, 1])
                                            col1.markdown(f"{prefix}**{summoner_name}{tag_display}** - {champion}")
                                            
                                            if player_id and not is_blacklisted:
                                                # Show blacklist button or form
                                                if form_key not in st.session_state.blacklist_forms:
                                                    if col2.button("Blacklist", key=f"bl_{player_id}_{i}_blue"):
                                                        st.session_state.blacklist_forms[form_key] = True
                                                        st.rerun()
                                                else:
                                                    # Show form for adding to blacklist
                                                    reason = st.text_input("Reason for blacklisting:", key=f"reason_{player_id}_{i}_blue")
                                                    col_confirm, col_cancel = st.columns(2)
                                                    
                                                    if col_confirm.button("Confirm", key=f"confirm_{player_id}_{i}_blue"):
                                                        # Call the add_to_blacklist function with all required parameters
                                                        success, message = st.session_state.blacklist_manager.add_to_blacklist(
                                                            summoner_id=player_id,
                                                            summoner_name=summoner_name,
                                                            reason=reason,
                                                            tagline=tagline
                                                        )
                                                        
                                                        if success:
                                                            st.success(message)
                                                            # Remove form from session state
                                                            del st.session_state.blacklist_forms[form_key]
                                                            st.rerun()
                                                        else:
                                                            st.warning(message)
                                                            # Keep form open if there was an error
                                                    
                                                    if col_cancel.button("Cancel", key=f"cancel_{player_id}_{i}_blue"):
                                                        # Remove form from session state
                                                        del st.session_state.blacklist_forms[form_key]
                                                        st.rerun()
                                            
                                            elif is_blacklisted:
                                                if col2.button("Remove", key=f"rm_{player_id}_{i}_blue"):
                                                    st.session_state.blacklist_manager.remove_from_blacklist(player_id)
                                                    st.success(f"Removed {summoner_name} from blacklist")
                                                    st.rerun()
                                    
                                    with team_cols[1]:
                                        st.markdown("#### Red Team")
                                        for player in red_team:
                                            # Get player info
                                            summoner_name = player.get('summoner_name', 'Unknown Player')
                                            tagline = player.get('tagline', '')
                                            champion = player.get('champion', 'Unknown')
                                            player_id = player.get('summoner_id', '')
                                            
                                            # Form key for this player
                                            form_key = f"form_{player_id}_{i}_red"
                                            
                                            # Show if blacklisted
                                            is_blacklisted = st.session_state.blacklist_manager.is_blacklisted(player_id)
                                            prefix = "⚠️ " if is_blacklisted else ""
                                            tag_display = f"#{tagline}" if tagline else ""
                                            
                                            # Display player with action buttons
                                            col1, col2 = st.columns([3, 1])
                                            col1.markdown(f"{prefix}**{summoner_name}{tag_display}** - {champion}")
                                            
                                            if player_id and not is_blacklisted:
                                                # Show blacklist button or form
                                                if form_key not in st.session_state.blacklist_forms:
                                                    if col2.button("Blacklist", key=f"bl_{player_id}_{i}_red"):
                                                        st.session_state.blacklist_forms[form_key] = True
                                                        st.rerun()
                                                else:
                                                    # Show form for adding to blacklist
                                                    reason = st.text_input("Reason for blacklisting:", key=f"reason_{player_id}_{i}_red")
                                                    col_confirm, col_cancel = st.columns(2)
                                                    
                                                    if col_confirm.button("Confirm", key=f"confirm_{player_id}_{i}_red"):
                                                        # Call the add_to_blacklist function with all required parameters
                                                        success, message = st.session_state.blacklist_manager.add_to_blacklist(
                                                            summoner_id=player_id,
                                                            summoner_name=summoner_name,
                                                            reason=reason,
                                                            tagline=tagline
                                                        )
                                                        
                                                        if success:
                                                            st.success(message)
                                                            # Remove form from session state
                                                            del st.session_state.blacklist_forms[form_key]
                                                            st.rerun()
                                                        else:
                                                            st.warning(message)
                                                    
                                                    if col_cancel.button("Cancel", key=f"cancel_{player_id}_{i}_red"):
                                                        # Remove form from session state
                                                        del st.session_state.blacklist_forms[form_key]
                                                        st.rerun()
                                            
                                            elif is_blacklisted:
                                                if col2.button("Remove", key=f"rm_{player_id}_{i}_red"):
                                                    st.session_state.blacklist_manager.remove_from_blacklist(player_id)
                                                    st.success(f"Removed {summoner_name} from blacklist")
                                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error retrieving match details: {str(e)}")
                                    st.text(f"Error details: {type(e).__name__}")
                    else:
                        st.info("No match history found for this summoner.")
        else:
            # Empty state for match history
            st.info("Enter a summoner name and region in the sidebar to begin")
            
            # Show some instructions
            st.markdown("""
            ### Welcome to the League of Legends Blacklist System
            
            This tool helps you keep track of players you'd rather avoid in your games.
            
            To get started:
            1. Enter your Riot API key in the sidebar
            2. Select your region
            3. Search for a summoner
            4. View their match history and blacklist problematic players
            """)
    
    with tab2:
        # Dedicated Blacklist tab
        st.header("Blacklist Manager")
        st.markdown("View, search, and manage your blacklisted players")
        
        if st.session_state.blacklist_manager:
            blacklist = st.session_state.blacklist_manager.get_blacklist()
            
            # Add refresh button
            if st.button("Refresh Blacklist"):
                st.rerun()
            
            if len(blacklist) > 0:
                # Add a search box for filtering the blacklist
                search_term = st.text_input("Filter blacklist", placeholder="Search by name...")
                
                filtered_blacklist = blacklist
                if search_term:
                    filtered_blacklist = blacklist[blacklist['summoner_name'].str.contains(search_term, case=False)]
                
                # Display the blacklist as a table
                st.dataframe(
                    filtered_blacklist,
                    hide_index=True,
                    column_config={
                        "summoner_id": st.column_config.TextColumn("ID", width="small"),
                        "summoner_name": st.column_config.TextColumn("Name", width="medium"),
                        "tagline": st.column_config.TextColumn("Tagline", width="small"),
                        "reason": st.column_config.TextColumn("Reason", width="large"),
                        "date_added": st.column_config.DatetimeColumn("Added On", format="D MMM YYYY", width="medium"),
                    },
                    use_container_width=True
                )
                
                # Create a column with name#tagline for display
                player_display = []
                for _, row in filtered_blacklist.iterrows():
                    name = row['summoner_name']
                    tagline = row.get('tagline', '')
                    tag_display = f"#{tagline}" if tagline else ""
                    player_display.append(f"{name}{tag_display}")
                
                # Add bulk management section
                with st.expander("Manage Blacklist"):
                    selected_action = st.radio("Select Action", ["Remove Player", "Export Blacklist", "Import Blacklist"])
                    
                    if selected_action == "Remove Player":
                        selected_summoner_idx = st.selectbox(
                            "Select a player to remove",
                            options=range(len(player_display)),
                            format_func=lambda i: player_display[i],
                            index=None
                        )
                        
                        if selected_summoner_idx is not None:
                            summoner_id = filtered_blacklist.iloc[selected_summoner_idx]['summoner_id']
                            summoner_name = player_display[selected_summoner_idx]
                            if st.button(f"Remove {summoner_name}", type="primary"):
                                if st.session_state.blacklist_manager.remove_from_blacklist(summoner_id):
                                    st.success(f"{summoner_name} has been removed from the blacklist")
                                    st.rerun()
                                else:
                                    st.error("Failed to remove from blacklist")
                    
                    elif selected_action == "Export Blacklist":
                        # Convert the blacklist to CSV for download
                        csv = blacklist.to_csv(index=False)
                        st.download_button(
                            label="Download Blacklist CSV",
                            data=csv,
                            file_name="lol_blacklist.csv",
                            mime="text/csv",
                        )
                    
                    elif selected_action == "Import Blacklist":
                        st.warning("This will merge the imported blacklist with your current blacklist")
                        uploaded_file = st.file_uploader("Upload Blacklist CSV", type="csv")
                        if uploaded_file is not None:
                            try:
                                import_blacklist = pd.read_csv(uploaded_file)
                                required_columns = ['summoner_id', 'summoner_name', 'reason']
                                if all(col in import_blacklist.columns for col in required_columns):
                                    # TODO: Add merge functionality
                                    st.info("Import functionality coming soon")
                                else:
                                    st.error("Invalid blacklist format. CSV must contain summoner_id, summoner_name, and reason columns")
                            except Exception as e:
                                st.error(f"Error importing blacklist: {str(e)}")
            else:
                st.info("Your blacklist is empty")
                
                # Add example card for empty state
                with st.container():
                    st.markdown("### How to use the Blacklist")
                    st.markdown("""
                    1. Search for players in the Matches tab
                    2. Click 'Blacklist' on problematic players
                    3. Add a reason for blacklisting
                    4. Use this tab to manage your blacklist
                    """)
        else:
            st.warning("Please set up your API key in the sidebar first")
    
    with tab3:
        # Live Game Checker
        st.header("Live Game Checker")
        st.markdown("Check your current game for blacklisted players")
        
        # Form for live game search
        with st.form(key="live_game_form"):
            live_summoner_name = st.text_input("Summoner Name", 
                                           value=last_username if last_username else "",
                                           placeholder="Enter your summoner name")
            live_tagline = st.text_input("Tagline", 
                                      value=last_tagline if last_tagline else "",
                                      placeholder="EUW, NA, etc.")
            
            check_button = st.form_submit_button("Check Current Game", 
                                              use_container_width=True, 
                                              type="primary")
        
        # Auto-refresh option
        auto_refresh = st.checkbox("Auto refresh (every 30 seconds)")
        
        if check_button or (auto_refresh and 'last_live_search' in st.session_state):
            # Save the search parameters for auto-refresh
            if check_button:
                st.session_state.last_live_search = {
                    'name': live_summoner_name,
                    'tagline': live_tagline
                }
            
            # Get the search parameters (either new or from session state)
            if auto_refresh and 'last_live_search' in st.session_state:
                live_summoner_name = st.session_state.last_live_search['name']
                live_tagline = st.session_state.last_live_search['tagline']
            
            # Check if we have a blacklist manager
            if not st.session_state.blacklist_manager:
                if api_key_input:
                    st.session_state.blacklist_manager = BlacklistManager(api_key=api_key_input, region=region_input)
                else:
                    st.error("Please set up your API key first")
                    st.stop()
            
            # Perform the live game check
            if live_summoner_name:
                try:
                    with st.spinner("Checking live game..."):
                        # Get summoner info
                        live_summoner = st.session_state.blacklist_manager.get_summoner(
                            live_summoner_name, live_tagline)
                        
                        # Check current match
                        current_match = st.session_state.blacklist_manager.get_current_match(live_summoner)
                        
                        if current_match:
                            # Get all players and check against blacklist
                            blacklisted_players = st.session_state.blacklist_manager.check_current_match_for_blacklisted(live_summoner)
                            
                            # Display game info
                            st.success(f"Found active game! Queue type: {current_match.get('gameQueueConfigId', 'Unknown')}")
                            
                            # Log participant structure for debugging
                            if 'participants' in current_match and len(current_match['participants']) > 0:
                                st.session_state.live_game_debug = True
                                first_player = current_match['participants'][0]
                                st.text(f"Participant data structure: {list(first_player.keys())}")
                            
                            # Create two columns for blue and red team
                            team_cols = st.columns(2)
                            
                            # Group participants by team
                            blue_team = [p for p in current_match['participants'] if p.get('teamId', p.get('team', '')) == 100]
                            red_team = [p for p in current_match['participants'] if p.get('teamId', p.get('team', '')) == 200]
                            
                            # Show blue team
                            with team_cols[0]:
                                st.markdown("### 🔵 Blue Team")
                                for player in blue_team:
                                    # Check if blacklisted
                                    player_id = player.get('summonerId', player.get('id', ''))
                                    is_blacklisted = st.session_state.blacklist_manager.is_blacklisted(player_id)
                                    
                                    # Get summoner name using v5 API field names
                                    summoner_name = player.get('summonerName', 
                                                   player.get('name', 
                                                   player.get('riotIdGameName', 'Unknown Player')))
                                    
                                    # Get champion name if possible - otherwise use ID
                                    champion = player.get('championName', player.get('championId', 'Unknown'))
                                    
                                    # Get tagline if available from player data
                                    tagline = player.get('riotIdTagline', '')
                                    tag_display = f"#{tagline}" if tagline else ""
                                    
                                    # Display player info with blacklist indicator
                                    if is_blacklisted:
                                        st.markdown(f"⚠️ **{summoner_name}{tag_display}** - {champion}")
                                        
                                        # Get reason from blacklist
                                        blacklist = st.session_state.blacklist_manager.get_blacklist()
                                        player_info = blacklist[blacklist['summoner_id'] == player_id].iloc[0]
                                        reason = player_info['reason']
                                        st.caption(f"Reason: {reason}")
                                    else:
                                        st.markdown(f"**{summoner_name}{tag_display}** - {champion}")
                            
                            # Show red team
                            with team_cols[1]:
                                st.markdown("### 🔴 Red Team")
                                for player in red_team:
                                    # Check if blacklisted
                                    player_id = player.get('summonerId', player.get('id', ''))
                                    is_blacklisted = st.session_state.blacklist_manager.is_blacklisted(player_id)
                                    
                                    # Get summoner name using v5 API field names
                                    summoner_name = player.get('summonerName', 
                                                   player.get('name', 
                                                   player.get('riotIdGameName', 'Unknown Player')))
                                    
                                    # Get champion name if possible - otherwise use ID
                                    champion = player.get('championName', player.get('championId', 'Unknown'))
                                    
                                    # Get tagline if available from player data
                                    tagline = player.get('riotIdTagline', '')
                                    tag_display = f"#{tagline}" if tagline else ""
                                    
                                    # Display player info with blacklist indicator
                                    if is_blacklisted:
                                        st.markdown(f"⚠️ **{summoner_name}{tag_display}** - {champion}")
                                        
                                        # Get reason from blacklist
                                        blacklist = st.session_state.blacklist_manager.get_blacklist()
                                        player_info = blacklist[blacklist['summoner_id'] == player_id].iloc[0]
                                        reason = player_info['reason']
                                        st.caption(f"Reason: {reason}")
                                    else:
                                        st.markdown(f"**{summoner_name}{tag_display}** - {champion}")
                            
                            # Display summary of blacklisted players
                            if blacklisted_players:
                                st.markdown("### ⚠️ Blacklisted Players Summary")
                                for player in blacklisted_players:
                                    # The summoner_name already includes the tagline from our BlacklistManager changes
                                    st.warning(
                                        f"**{player['summoner_name']}** - {player['champion']}\n\n"
                                        f"Reason: {player['reason']}\n\n"
                                        f"Added: {player['date_added']}"
                                    )
                            else:
                                st.success("No blacklisted players found in this game! 👍")
                        else:
                            st.info(f"{live_summoner_name} is not currently in a game. Check again when they're in a match.")
                
                except Exception as e:
                    # Only show error if it's not a simple "not in game" issue
                    if "not in a game" not in str(e) and "Could not find summoner" not in str(e):
                        st.error(f"Error: {str(e)}")
                    else:
                        st.info(str(e))
            else:
                st.error("Please enter a summoner name")
            
            # Handle auto-refresh
            if auto_refresh:
                refresh_placeholder = st.empty()
                for seconds in range(30, 0, -1):
                    refresh_placeholder.info(f"Refreshing in {seconds} seconds...")
                    time.sleep(1)
                st.rerun()
    
    with tab4:
        # Help tab content
        st.markdown("""
        ## How to Use the Blacklist System
        
        ### Getting Started
        1. You need a valid Riot API key to use this application
        2. Enter your API key in the sidebar settings
        3. Select your region
        4. Save your settings
        
        ### Searching for Players
        1. Enter a summoner name (with or without tagline)
        2. If no tagline is provided, it will use your region's default
        3. Click search to view their profile and match history
        
        ### Managing Your Blacklist
        - Click "Blacklist" next to any player to add them to your blacklist
        - Add a reason to help you remember why they were blacklisted
        - Use the Blacklist tab to view and manage your blacklisted players
        - You can filter the blacklist by player name
        
        ### Using the Live Game Checker
        1. Go to the "Live Game Checker" tab
        2. Enter your summoner name (or any summoner you want to check)
        3. Click "Check Current Game" to see if anyone in your current game is blacklisted
        4. Enable "Auto refresh" to continuously check every 30 seconds (useful while in champion select)
        5. Players from your blacklist will be highlighted with reasons displayed
        
        ### API Limitations
        - The Riot API has rate limits that may affect how many requests you can make
        - Match history data may be limited based on your API key's permissions
        - Live game checking is only available for players who are currently in a game
        """)

if __name__ == "__main__":
    main() 