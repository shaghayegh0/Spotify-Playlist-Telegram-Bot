import os
import time
import asyncio
import schedule
from datetime import datetime
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

class SpotifyPlaylistMonitor:
    def __init__(self):
        # Telegram configuration
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = Bot(token=self.bot_token)
        
        # Spotify configuration
        self.playlist_id = os.getenv('SPOTIFY_PLAYLIST_ID')
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope='playlist-read-private playlist-read-collaborative',
            cache_path='.spotify_cache'
        ))
        
        # Track previous state
        self.state_file = 'playlist_state.json'
        self.previous_tracks = self.get_current_tracks()
        self.previous_count = len(self.previous_tracks)
        
        print(f"🎵 Starting monitoring for playlist with {self.previous_count} tracks")
        print(f"📋 Currently tracking {len(self.previous_tracks)} tracks by ID")

    def parse_spotify_date(self, date_string):
        """Parse Spotify date strings that can have two different formats"""
        try:
            # Try format with milliseconds first
            return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            # Try format without milliseconds
            return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
        
    def get_current_tracks(self):
        """Get current tracks from Spotify playlist, sorted by most recently added"""
        try:
            all_tracks = []
            results = self.sp.playlist_tracks(self.playlist_id)
            
            while results:
                for item in results['items']:
                    if item['track'] and item['track']['id']:
                        track = item['track']
                        # Use our date parser
                        added_date = self.parse_spotify_date(item['added_at'])
                        all_tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track['artists']],
                            'album': track['album']['name'],
                            'added_at': item['added_at'],
                            'added_date': added_date,  # Add parsed date for sorting
                            'duration_ms': track['duration_ms'],
                            'external_url': track['external_urls']['spotify']
                        })
                
                if results['next']:
                    results = self.sp.next(results)
                else:
                    break
            
            # Sort tracks by added_date (newest first)
            all_tracks.sort(key=lambda x: x['added_date'], reverse=True)
            
            print(f"📊 Found {len(all_tracks)} tracks in playlist")
            
            # Show the 3 most recently added tracks for debugging
            print("🆕 Most recent tracks:")
            for i, track in enumerate(all_tracks[:3]):
                artists = ", ".join(track['artists'])
                added_date = track['added_date'].strftime('%Y-%m-%d %H:%M')
                print(f"   {i+1}. {track['name']} - {artists} (added: {added_date})")
                    
            return all_tracks
            
        except Exception as e:
            print(f"❌ Error fetching tracks: {e}")
            return []
    
    def save_current_state(self):
        """Save current track count to file"""
        try:
            with open(self.state_file, 'w') as f:
                import json
                json.dump({'track_count': len(self.previous_tracks)}, f)
        except Exception as e:
            print(f"❌ Error saving state: {e}")
    
    def format_duration(self, duration_ms):
        """Convert milliseconds to minutes:seconds format"""
        minutes = duration_ms // 60000
        seconds = (duration_ms % 60000) // 1000
        return f"{minutes}:{seconds:02d}"
    
    
    def send_telegram_message(self, message):
        """Send message to Telegram - SIMPLE REQUESTS VERSION"""
        try:
            import requests
            
            # Send via Telegram Bot API directly
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print("✅ Notification sent to Telegram")
            else:
                print(f"❌ Telegram API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")

    async def _async_send_message(self, message):
        """Async helper to send Telegram message"""
        await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')  


    def check_for_new_tracks(self): 
        """Check for new tracks by comparing track IDs, not just counts"""
        print(f"🕒 Checking for new tracks at {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            current_tracks = self.get_current_tracks()
            current_track_ids = {track['id'] for track in current_tracks}
            previous_track_ids = {track['id'] for track in self.previous_tracks}
            
            # Find new tracks (in current but not in previous)
            new_track_ids = current_track_ids - previous_track_ids
            
            if new_track_ids:
                # Get the actual track objects for the new IDs
                new_tracks = [track for track in current_tracks if track['id'] in new_track_ids]
                
                print(f"🎉 Found {len(new_tracks)} new track(s)!")
                
                # Send notification for each new track
                for track in new_tracks:
                    message = self.create_track_message(track)
                    self.send_telegram_message(message)
                    print(f"📨 Sent notification for: {track['name']}")
                    time.sleep(1)
                
                # Update previous state
                self.previous_tracks = current_tracks
                self.previous_count = len(current_tracks)
                self.save_current_state()
                
            else:
                # Check if tracks were removed
                removed_track_ids = previous_track_ids - current_track_ids
                if removed_track_ids:
                    print(f"🗑️  {len(removed_track_ids)} track(s) were removed from playlist")
                    self.previous_tracks = current_tracks
                    self.previous_count = len(current_tracks)
                    self.save_current_state()
                else:
                    print("✅ No changes detected")
                
        except Exception as e:
            print(f"❌ Error in check_for_new_tracks: {e}")
    
    def create_track_message(self, track):
        """Create formatted message for a new track"""
        artists = ", ".join(track['artists'])
        duration = self.format_duration(track['duration_ms'])
        added_date = self.parse_spotify_date(track['added_at'])
        added_time = added_date.strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""
🎵 <b>New Song Added to Playlist!</b> 🎵

<b>Track:</b> {track['name']}
<b>Artist(s):</b> {artists}
<b>Album:</b> {track['album']}
<b>Duration:</b> {duration}
<b>Added:</b> {added_time}

🔗 <a href="{track['external_url']}">Listen on Spotify</a>
        """.strip()
        
        return message
    
    def start_monitoring(self, interval_minutes=5):
        """Start monitoring the playlist"""
        print(f"🚀 Starting playlist monitoring. Checking every {interval_minutes} minutes...")
        
        # Send startup message
        try:
            self.send_telegram_message(
                f"🎵 <b>Spotify Playlist Monitor Started!</b>\n\nI'll notify you when new songs are added to your playlist.\nChecking every {interval_minutes} minutes..."
            )
        except Exception as e:
            print(f"❌ Could not send startup message: {e}")
        
        # Initial check
        self.check_for_new_tracks()
        
        # Schedule periodic checks
        schedule.every(interval_minutes).minutes.do(self.check_for_new_tracks)
        
        print("✅ Monitor is running! Press Ctrl+C to stop.")
        print("📱 Add a song to your playlist to test notifications...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                try:
                    asyncio.run(self._async_send_message("🛑 Spotify Playlist Monitor stopped."))
                except:
                    pass
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)

    def stop_monitoring(self):
        """Stop monitoring and send shutdown message"""
        try:
            asyncio.run(self._async_send_message("🛑 Spotify Playlist Monitor stopped."))
        except:
            pass

def main():
    try:
        monitor = SpotifyPlaylistMonitor()
        # Start monitoring (check every 6 seconds for testing)
        monitor.start_monitoring(interval_minutes=0.1)  # 6 seconds
    except Exception as e:
        print(f"❌ Failed to start monitor: {e}")

if __name__ == "__main__":
    main()