import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

def setup_spotify():
    print("🔐 Starting Spotify authentication...")
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope='playlist-read-private playlist-read-collaborative user-read-private',
        cache_path='.spotify_cache'
    ))
    
    try:
        # This will open a browser for authentication
        user = sp.current_user()
        print(f"✅ Authenticated as: {user['display_name']}")
        
        # Test playlist access
        playlist = sp.playlist(os.getenv('SPOTIFY_PLAYLIST_ID'))
        print(f"🎵 Playlist: {playlist['name']}")
        print(f"📊 Total tracks: {playlist['tracks']['total']}")
        print("🎉 Authentication successful! You can now run the monitor.")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("Make sure your Client ID and Secret are correct.")

if __name__ == "__main__":
    setup_spotify()