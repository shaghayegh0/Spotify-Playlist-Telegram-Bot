import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime

load_dotenv()

def parse_spotify_date(date_string):
    """Parse Spotify date strings that can have two different formats"""
    try:
        # Try format with milliseconds first
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        # Try format without milliseconds
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')

def check_playlist_order():
    print("🔍 Checking playlist track order...")
    print("=" * 60)
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope='playlist-read-private',
        cache_path='.spotify_cache'
    ))
    
    playlist_id = os.getenv('SPOTIFY_PLAYLIST_ID')
    
    try:
        # Get playlist details
        playlist = sp.playlist(playlist_id)
        print(f"🎵 Playlist: {playlist['name']}")
        print(f"📊 Total tracks: {playlist['tracks']['total']}")
        print("\n")
        
        # Get all tracks with pagination
        all_tracks = []
        results = sp.playlist_tracks(playlist_id)
        
        while results:
            for item in results['items']:
                if item['track']:
                    track = item['track']
                    added_date = parse_spotify_date(item['added_at'])
                    all_tracks.append({
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'added_at': item['added_at'],
                        'added_date': added_date
                    })
            
            if results['next']:
                results = sp.next(results)
            else:
                break
        
        # Sort by added date (newest first)
        all_tracks.sort(key=lambda x: x['added_date'], reverse=True)
        
        print("🆕 TOP 10 MOST RECENTLY ADDED TRACKS:")
        print("-" * 80)
        for i, track in enumerate(all_tracks[:10]):
            artists = ", ".join(track['artists'])
            date_str = track['added_date'].strftime('%Y-%m-%d %H:%M')
            print(f"{i+1:2d}. {track['name'][:45]:45} | {artists[:20]:20} | {date_str}")
        
        print(f"\n📅 Oldest track: {all_tracks[-1]['added_date'].strftime('%Y-%m-%d')}")
        print(f"📅 Newest track: {all_tracks[0]['added_date'].strftime('%Y-%m-%d')}")
        
        # Show when each track was added relative to now
        print(f"\n⏰ Time since added:")
        now = datetime.now()
        for i, track in enumerate(all_tracks[:5]):
            time_diff = now - track['added_date']
            days = time_diff.days
            hours = time_diff.seconds // 3600
            print(f"   {i+1}. {track['name'][:30]:30} - {days} days, {hours} hours ago")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_playlist_order()