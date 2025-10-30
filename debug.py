import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telegram import Bot

load_dotenv()

def debug_setup():
    print("🔍 DEBUG MODE")
    print("=" * 50)
    
    # Test Telegram
    try:
        bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        bot.send_message(
            chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            text="🔍 Debug test message - Telegram is working!"
        )
        print("✅ Telegram: OK")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return
    
    # Test Spotify
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope='playlist-read-private',
            cache_path='.spotify_cache'
        ))
        
        # Get current playlist state
        playlist_id = os.getenv('SPOTIFY_PLAYLIST_ID')
        playlist = sp.playlist_tracks(playlist_id)
        current_tracks = len(playlist['items'])
        
        print(f"✅ Spotify: OK")
        print(f"🎵 Playlist has {current_tracks} tracks")
        
        # Show recent tracks
        print("\n📋 Recent tracks:")
        for i, item in enumerate(playlist['items'][-5:]):  # Last 5 tracks
            if item['track']:
                track = item['track']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                print(f"  {i+1}. {track['name']} - {artists}")
                
    except Exception as e:
        print(f"❌ Spotify error: {e}")

if __name__ == "__main__":
    debug_setup()