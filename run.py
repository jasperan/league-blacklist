#!/usr/bin/env python3
import subprocess
import sys
import os
import webbrowser
from time import sleep

def main():
    print("=== League of Legends Blacklist System ===")
    
    # Check for dependencies
    try:
        import streamlit
        import pandas
        import cassiopeia
    except ImportError:
        print("Some dependencies are missing. Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Checking if config.json exists
    config_exists = os.path.exists("config.json")
    
    if not config_exists:
        print("\nWelcome to the League of Legends Blacklist System!")
        print("Before we get started, you'll need a Riot API key.")
        print("You can get one at: https://developer.riotgames.com/")
        print("\nOnce you have your API key, you'll need to enter it in the app.")
        print("The app will save your API key locally so you don't need to enter it each time.")
    else:
        print("\nConfig file found! Your saved settings will be loaded automatically.")
    
    print("\nStarting the Streamlit app...")
    print("The app will open in your browser shortly.")
    
    # Open the browser
    sleep(2)  # Brief pause
    webbrowser.open('http://localhost:8501')
    
    # Start the Streamlit app
    run_streamlit()

def run_streamlit():
    """Run the Streamlit app with auto-reload enabled"""
    try:
        # Run streamlit with --reload flag
        subprocess.run([
            "streamlit", "run", 
            "app.py",
            "--reload",
            "--server.runOnSave=true"  # Also enable run on save
        ], check=True)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 