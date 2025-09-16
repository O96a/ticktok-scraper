#!/usr/bin/env python3
"""
Enhanced TikTok Live Stream Scraper
Robust, standalone scraper without API/Docker dependencies
Monitors multiple TikTok streamers and captures live comments with advanced features
"""

import asyncio
import logging
import os
import hashlib
import time
import json
import random
import signal
import sys
import unicodedata
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
import traceback

# TikTokLive imports
try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent, LikeEvent, ShareEvent, FollowEvent
    TIKTOK_LIVE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: TikTokLive not available: {e}")
    TIKTOK_LIVE_AVAILABLE = False

@dataclass
class ScrapingStats:
    """Statistics tracking for the scraper"""
    total_streamers: int = 0
    active_connections: int = 0
    comments_captured: int = 0
    likes_captured: int = 0
    shares_captured: int = 0
    follows_captured: int = 0
    duplicates_filtered: int = 0
    rate_limit_hits: int = 0
    connection_attempts: int = 0
    failed_connections: int = 0
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.last_update:
            result['last_update'] = self.last_update.isoformat()
        return result

@dataclass 
class RateLimitConfig:
    """Enhanced rate limiting configuration"""
    base_delay: int = 15
    max_delay: int = 1800
    rate_limit_cooldown: int = 3600
    global_rate_limit_duration: int = 1800
    per_streamer_rate_limit: int = 3600
    max_concurrent_connections: int = 2
    min_connection_interval: int = 5
    pre_connection_delay: tuple = (2, 5)
    connection_timeout: int = 45
    retry_attempts: int = 3
    backoff_multiplier: float = 2.0
    jitter_range: tuple = (0.8, 1.2)

class EnhancedTikTokScraper:
    """
    Enhanced TikTok scraper with robust error handling, advanced deduplication,
    and comprehensive monitoring without API/Docker dependencies
    """
    
    def __init__(self, 
                 streamers_file: str = "streamers.txt",
                 output_dir: str = "output",
                 config_file: str = "config.json"):
        
        # Setup paths
        self.script_dir = Path(__file__).parent
        self.streamers_file = self._resolve_path(streamers_file)
        self.output_dir = self._resolve_path(output_dir)
        self.config_file = self._resolve_path(config_file)
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize state
        self.stats = ScrapingStats()
        self.active_clients: Dict[str, TikTokLiveClient] = {}
        self.active_sessions: Set[str] = set()
        self.session_files: Dict[str, Path] = {}
        
        # Enhanced deduplication with persistent storage
        self.recent_comments: Dict[str, Dict[str, float]] = {}
        self.comment_history_file = self.output_dir / "comment_history.json"
        self._load_comment_history()
        
        # Rate limiting
        self.global_rate_limit_until = 0
        self.streamer_rate_limits: Dict[str, float] = {}
        self.connection_semaphore = asyncio.Semaphore(self.config.max_concurrent_connections)
        self.last_connection_time = 0
        
        # Graceful shutdown
        self.running = True
        self._setup_signal_handlers()
        
        self.logger.info("Enhanced TikTok Scraper initialized")
        
    def _resolve_path(self, path_str: str) -> Path:
        """Resolve path relative to script directory"""
        path = Path(path_str)
        if not path.is_absolute():
            path = self.script_dir / path
        return path
        
    def _load_config(self) -> RateLimitConfig:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                return RateLimitConfig(**config_data)
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
        
        # Create default config
        config = RateLimitConfig()
        self._save_config(config)
        return config
        
    def _save_config(self, config: RateLimitConfig):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def _setup_logging(self):
        """Setup comprehensive logging"""
        log_file = self.output_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Setup file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False
        
    def _is_emoji_only_message(self, text: str) -> bool:
        """Check if the message contains only emojis and whitespace"""
        if not text or not text.strip():
            return True
            
        # Remove all whitespace
        text_no_space = text.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
        
        # If empty after removing whitespace, it's not useful
        if not text_no_space:
            return True
            
        # Check if all characters are emojis/symbols
        emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F]|'  # emoticons
            r'[\U0001F300-\U0001F5FF]|'  # symbols & pictographs
            r'[\U0001F680-\U0001F6FF]|'  # transport & map symbols
            r'[\U0001F1E0-\U0001F1FF]|'  # flags (iOS)
            r'[\U00002702-\U000027B0]|'  # dingbats
            r'[\U000024C2-\U0001F251]|'  # enclosed characters
            r'[\U0001F900-\U0001F9FF]|'  # supplemental symbols
            r'[\U0001FA70-\U0001FAFF]'   # symbols and pictographs extended-a
        )
        
        # Remove all emojis from the text
        text_no_emoji = emoji_pattern.sub('', text_no_space)
        
        # If nothing remains after removing emojis, it's emoji-only
        return len(text_no_emoji.strip()) == 0
        
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def _load_comment_history(self):
        """Load comment history for persistent deduplication"""
        if self.comment_history_file.exists():
            try:
                with open(self.comment_history_file, 'r', encoding='utf-8') as f:
                    self.recent_comments = json.load(f)
                self.logger.info("Loaded comment history for deduplication")
            except Exception as e:
                self.logger.warning(f"Error loading comment history: {e}")
                self.recent_comments = {}
        else:
            self.recent_comments = {}
            
    def _save_comment_history(self):
        """Save comment history for persistent deduplication"""
        try:
            # Clean old entries before saving
            current_time = time.time()
            cutoff_time = current_time - (24 * 3600)  # Keep 24 hours
            
            cleaned_history = {}
            for username, comments in self.recent_comments.items():
                cleaned_comments = {
                    hash_val: timestamp for hash_val, timestamp in comments.items()
                    if timestamp > cutoff_time
                }
                if cleaned_comments:
                    cleaned_history[username] = cleaned_comments
                    
            with open(self.comment_history_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving comment history: {e}")
            
    def load_streamers(self) -> List[str]:
        """Load streamers from configuration file with validation"""
        if not self.streamers_file.exists():
            self.logger.warning(f"Streamers file {self.streamers_file} not found, creating template")
            self._create_streamers_template()
            return []
            
        streamers = []
        try:
            with open(self.streamers_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        username = line.replace('@', '').strip()
                        if self._validate_username(username):
                            streamers.append(username)
                        else:
                            self.logger.warning(f"Invalid username '{username}' on line {line_num}")
                            
            self.logger.info(f"Loaded {len(streamers)} valid streamers")
            return streamers
            
        except Exception as e:
            self.logger.error(f"Error loading streamers: {e}")
            return []
            
    def _validate_username(self, username: str) -> bool:
        """Validate TikTok username format"""
        if not username:
            return False
        # TikTok usernames: 1-24 chars, letters, numbers, underscores, periods
        import re
        pattern = r'^[a-zA-Z0-9_.]{1,24}$'
        return bool(re.match(pattern, username))
        
    def _create_streamers_template(self):
        """Create template streamers file"""
        template = """# TikTok Streamers Configuration
# Add one username per line (without @)
# Lines starting with # are comments

# Examples (replace with actual usernames):
# username1
# username2
# username3

# Current streamers:
"""
        try:
            with open(self.streamers_file, 'w', encoding='utf-8') as f:
                f.write(template)
            self.logger.info(f"Created template streamers file: {self.streamers_file}")
        except Exception as e:
            self.logger.error(f"Error creating streamers template: {e}")
            
    def get_output_filename(self, username: str) -> str:
        """Generate timestamped output filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"tiktok-rawdata-{username}-{timestamp}.txt"
        
    async def save_event(self, username: str, event_type: str, commenter: str, content: str, extra_data: Dict = None):
        """Save comment events in simple text format - only comment text, no usernames"""
        try:
            current_time = time.time()
            
            # Enhanced deduplication for comments
            if event_type == 'comment':
                if await self._is_duplicate_comment(username, commenter, content, current_time):
                    self.stats.duplicates_filtered += 1
                    return
                    
                # Filter out emoji-only messages
                if self._is_emoji_only_message(content):
                    self.stats.duplicates_filtered += 1  # Count as filtered
                    return
                    
            # Create session file if needed
            if username not in self.session_files:
                filename = self.get_output_filename(username)
                filepath = self.output_dir / filename
                self.session_files[username] = filepath
                
                # Write session header in text format
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"SYSTEM: Connected to @{username}'s live stream\n")
                    
            # Clean content for text format (remove pipes and newlines)
            clean_content = str(content).replace('\n', ' ').replace('\r', ' ').strip()
            
            # Only save comments and system messages - skip other event types
            if event_type == 'comment':
                # Save only the comment text (no username)
                filepath = self.session_files[username]
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(f"{clean_content}\n")
                    f.flush()
                
                # Update stats
                self.stats.comments_captured += 1
                self.stats.last_update = datetime.now()
                
                # Log with proper Unicode handling
                display_content = content[:100] + '...' if len(content) > 100 else content
                try:
                    self.logger.info(f"[{username}] COMMENT: {display_content}")
                except UnicodeEncodeError:
                    safe_content = content.encode('ascii', errors='replace').decode('ascii')
                    self.logger.info(f"[{username}] COMMENT: {safe_content}")
                    
            elif event_type == 'system':
                # Keep system messages with SYSTEM prefix for connection tracking
                filepath = self.session_files[username]
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(f"SYSTEM: {clean_content}\n")
                    f.flush()
                
        except Exception as e:
            self.logger.error(f"Error saving {event_type} for {username}: {e}")
            
    async def _is_duplicate_comment(self, username: str, commenter: str, comment: str, current_time: float) -> bool:
        """Enhanced duplicate detection with multiple strategies"""
        
        # Initialize tracking for this streamer
        if username not in self.recent_comments:
            self.recent_comments[username] = {}
            
        # Strategy 1: Exact match detection
        exact_key = f"{commenter}|{comment.strip()}"
        exact_hash = hashlib.md5(exact_key.encode('utf-8')).hexdigest()
        
        if exact_hash in self.recent_comments[username]:
            last_seen = self.recent_comments[username][exact_hash]
            if current_time - last_seen < 30:  # 30 second window
                return True
                
        # Strategy 2: Similar content detection (for spam/bots)
        normalized_comment = unicodedata.normalize('NFC', comment.lower().strip())
        similarity_key = f"{commenter}|{normalized_comment}"
        similarity_hash = hashlib.md5(similarity_key.encode('utf-8')).hexdigest()
        
        if similarity_hash in self.recent_comments[username]:
            last_seen = self.recent_comments[username][similarity_hash]
            if current_time - last_seen < 10:  # 10 second window for similar content
                return True
                
        # Strategy 3: Rapid-fire detection (same user posting too quickly)
        user_prefix = f"{commenter}|"
        recent_from_user = [
            timestamp for hash_val, timestamp in self.recent_comments[username].items()
            if hash_val.startswith(hashlib.md5(user_prefix.encode('utf-8')).hexdigest()[:8])
            and current_time - timestamp < 5  # 5 second window
        ]
        
        if len(recent_from_user) >= 3:  # More than 3 comments in 5 seconds
            return True
            
        # Store the hashes
        self.recent_comments[username][exact_hash] = current_time
        self.recent_comments[username][similarity_hash] = current_time
        
        # Cleanup old entries
        self._cleanup_old_comments(username, current_time)
        
        return False
        
    def _cleanup_old_comments(self, username: str, current_time: float):
        """Clean up old comment hashes to prevent memory bloat"""
        if username not in self.recent_comments:
            return
            
        # Remove entries older than 1 hour
        cutoff_time = current_time - 3600
        old_hashes = [
            comment_hash for comment_hash, timestamp 
            in self.recent_comments[username].items() 
            if timestamp < cutoff_time
        ]
        
        for comment_hash in old_hashes:
            del self.recent_comments[username][comment_hash]
            
        # Limit to 1000 most recent entries per streamer
        if len(self.recent_comments[username]) > 1000:
            sorted_comments = sorted(
                self.recent_comments[username].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            self.recent_comments[username] = dict(sorted_comments[:500])
            
    async def create_streamer_client(self, username: str) -> tuple[bool, bool]:
        """Create and connect TikTok client with enhanced error handling and retries"""
        
        if not TIKTOK_LIVE_AVAILABLE:
            self.logger.error("TikTokLive library not available")
            return False, False
            
        async with self.connection_semaphore:
            self.stats.connection_attempts += 1
            
            try:
                # Rate limiting checks
                current_time = time.time()
                
                # Global rate limit check
                if current_time < self.global_rate_limit_until:
                    remaining = self.global_rate_limit_until - current_time
                    self.logger.info(f"⏰ Global rate limit active, {remaining/60:.1f} minutes remaining")
                    return False, True
                    
                # Per-streamer rate limit check
                if username in self.streamer_rate_limits and current_time < self.streamer_rate_limits[username]:
                    remaining = self.streamer_rate_limits[username] - current_time
                    self.logger.debug(f"⏰ @{username} rate limited for {remaining/60:.1f} more minutes")
                    return False, True
                    
                # Connection interval enforcement
                time_since_last = current_time - self.last_connection_time
                if time_since_last < self.config.min_connection_interval:
                    wait_time = self.config.min_connection_interval - time_since_last
                    await asyncio.sleep(wait_time)
                    
                # Pre-connection stealth delay
                delay_min, delay_max = self.config.pre_connection_delay
                await asyncio.sleep(random.uniform(delay_min, delay_max))
                
                self.logger.info(f"🔌 Connecting to @{username}...")
                self.last_connection_time = time.time()
                
                # Create client
                client = TikTokLiveClient(unique_id=username)
                
                # Setup comprehensive event handlers
                self._setup_client_handlers(client, username)
                
                # Store client
                self.active_clients[username] = client
                
                # Start client with timeout
                await asyncio.wait_for(
                    client.start(), 
                    timeout=self.config.connection_timeout
                )
                
                return True, False
                
            except Exception as e:
                self.stats.failed_connections += 1
                error_msg = str(e)
                
                # Check for rate limiting indicators
                rate_limit_indicators = [
                    'rate_limit', 'rate limit', 'too many requests', '429',
                    'sign server', 'rate_limit_ip_day', 'euler', 'blocked'
                ]
                
                is_rate_limited = any(indicator in error_msg.lower() for indicator in rate_limit_indicators)
                
                if is_rate_limited:
                    self.stats.rate_limit_hits += 1
                    current_time = time.time()
                    
                    # Set rate limits
                    self.global_rate_limit_until = current_time + self.config.global_rate_limit_duration
                    self.streamer_rate_limits[username] = current_time + self.config.per_streamer_rate_limit
                    
                    self.logger.warning(f"🚫 Rate limit detected for @{username}: {error_msg}")
                    return False, True
                else:
                    self.logger.error(f"❌ Failed to connect to @{username}: {error_msg}")
                    return False, False
                    
    def _setup_client_handlers(self, client: TikTokLiveClient, username: str):
        """Setup comprehensive event handlers for the client"""
        
        @client.on(ConnectEvent)
        async def on_connect(event):
            try:
                self.logger.info(f"✅ Connected to @{username}'s live stream")
                self.active_sessions.add(username)
                self.stats.active_connections += 1
                await self.save_event(username, "system", "SCRAPER", f"Connected to live stream", {
                    "event": "connect",
                    "viewer_count": getattr(event, 'viewer_count', 0)
                })
            except Exception as e:
                self.logger.error(f"Error in connect handler for @{username}: {e}")
                
        @client.on(DisconnectEvent)
        async def on_disconnect(event):
            try:
                self.logger.info(f"❌ Disconnected from @{username}'s live stream")
                if username in self.active_sessions:
                    self.active_sessions.remove(username)
                    self.stats.active_connections = max(0, self.stats.active_connections - 1)
                await self.save_event(username, "system", "SCRAPER", f"Disconnected from live stream", {
                    "event": "disconnect"
                })
            except Exception as e:
                self.logger.error(f"Error in disconnect handler for @{username}: {e}")
                
        @client.on(CommentEvent)
        async def on_comment(event):
            try:
                # Extract comment data safely
                commenter = "unknown"
                comment = ""
                extra_data = {}
                
                if hasattr(event, 'user') and event.user:
                    commenter = getattr(event.user, 'username', getattr(event.user, 'display_name', 'unknown'))
                    extra_data['user_id'] = getattr(event.user, 'user_id', None)
                    
                if hasattr(event, 'comment'):
                    comment = str(event.comment)
                    
                # Normalize Unicode text
                commenter = unicodedata.normalize('NFC', str(commenter))
                comment = unicodedata.normalize('NFC', comment)
                
                await self.save_event(username, "comment", commenter, comment, extra_data)
                
            except Exception as e:
                self.logger.error(f"Error processing comment for @{username}: {e}")
                
        # Like, Share, and Follow events are disabled - only capturing comments
        # @client.on(LikeEvent)
        # @client.on(ShareEvent) 
        # @client.on(FollowEvent)
                
    async def monitor_streamer(self, username: str):
        """Monitor a single streamer with intelligent retry and backoff"""
        consecutive_failures = 0
        consecutive_rate_limits = 0
        last_success_time = time.time()
        
        self.logger.info(f"🎯 Starting monitoring for @{username}")
        
        while self.running:
            try:
                current_time = time.time()
                
                # Adaptive retry delay based on failure history
                if consecutive_failures > 0:
                    delay = min(
                        self.config.base_delay * (self.config.backoff_multiplier ** consecutive_failures),
                        self.config.max_delay
                    )
                    jitter = random.uniform(*self.config.jitter_range)
                    actual_delay = delay * jitter
                    
                    self.logger.info(f"⏳ @{username}: Waiting {actual_delay:.1f}s before retry (failures: {consecutive_failures})")
                    await asyncio.sleep(actual_delay)
                    
                # Rate limit cooldown check
                if consecutive_rate_limits >= 3:
                    cooldown_remaining = self.config.rate_limit_cooldown - (current_time - last_success_time)
                    if cooldown_remaining > 0:
                        self.logger.info(f"🕒 @{username}: Rate limit cooldown, {cooldown_remaining/60:.1f}m remaining")
                        await asyncio.sleep(min(cooldown_remaining, 300))
                        continue
                        
                # Attempt connection
                success, is_rate_limited = await self.create_streamer_client(username)
                
                if is_rate_limited:
                    consecutive_rate_limits += 1
                    consecutive_failures += 1
                    continue
                    
                if success:
                    self.logger.info(f"✅ Successfully monitoring @{username}")
                    consecutive_failures = 0
                    consecutive_rate_limits = 0
                    last_success_time = time.time()
                    
                    # Monitor while connected
                    while username in self.active_sessions and self.running:
                        await asyncio.sleep(10)
                        
                    self.logger.info(f"🔄 @{username} stream ended, will retry")
                else:
                    consecutive_failures += 1
                    self.logger.debug(f"❌ @{username} not live or connection failed")
                    
                # Cleanup client
                if username in self.active_clients:
                    try:
                        await self.active_clients[username].disconnect()
                    except:
                        pass
                    del self.active_clients[username]
                    
            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Error monitoring @{username}: {e}")
                await asyncio.sleep(60)
                
        self.logger.info(f"🛑 Stopped monitoring @{username}")
        
    async def status_reporter(self):
        """Periodic status reporting and maintenance"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                if not self.running:
                    break
                    
                # Calculate runtime
                runtime = datetime.now() - self.stats.start_time if self.stats.start_time else timedelta(0)
                
                # Rate limit status
                current_time = time.time()
                global_rl_remaining = max(0, self.global_rate_limit_until - current_time)
                active_rl_count = sum(1 for t in self.streamer_rate_limits.values() if current_time < t)
                
                # Status report - only showing comments since we're only capturing comments
                self.logger.info(
                    f"📊 Status: {self.stats.active_connections}/{self.stats.total_streamers} active | "
                    f"💬 {self.stats.comments_captured} comments | "
                    f"🚫 {self.stats.duplicates_filtered} duplicates filtered | "
                    f"⚠️ {self.stats.rate_limit_hits} rate limits | "
                    f"⏱️ Runtime: {str(runtime).split('.')[0]}"
                )
                
                if global_rl_remaining > 0:
                    self.logger.info(f"🚫 Global rate limit: {global_rl_remaining/60:.1f}m remaining")
                    
                if active_rl_count > 0:
                    self.logger.info(f"🚫 {active_rl_count} streamers rate limited")
                    
                # Save comment history periodically
                self._save_comment_history()
                
                # Save stats
                await self._save_stats()
                
            except Exception as e:
                self.logger.error(f"Error in status reporter: {e}")
                
    async def _save_stats(self):
        """Save statistics to file"""
        try:
            stats_file = self.output_dir / "scraper_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving stats: {e}")
            
    async def run(self):
        """Main execution method"""
        try:
            self.logger.info("🚀 Starting Enhanced TikTok Scraper...")
            self.stats.start_time = datetime.now()
            
            # Load streamers
            streamers = self.load_streamers()
            if not streamers:
                self.logger.error("❌ No streamers configured. Please add usernames to streamers.txt")
                return
                
            self.stats.total_streamers = len(streamers)
            self.logger.info(f"👥 Monitoring {len(streamers)} streamers: {', '.join(streamers)}")
            
            # Create monitoring tasks
            tasks = []
            
            # Add streamer monitoring tasks
            for username in streamers:
                task = asyncio.create_task(self.monitor_streamer(username))
                tasks.append(task)
                
            # Add status reporter task
            status_task = asyncio.create_task(self.status_reporter())
            tasks.append(status_task)
            
            # Run all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Received shutdown signal")
        except Exception as e:
            self.logger.error(f"💥 Fatal error: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            await self._cleanup()
            
    async def _cleanup(self):
        """Cleanup resources and save final state"""
        self.logger.info("🧹 Cleaning up...")
        self.running = False
        
        # Disconnect all clients
        for username, client in self.active_clients.items():
            try:
                self.logger.info(f"Disconnecting from @{username}")
                await client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting from @{username}: {e}")
                
        self.active_clients.clear()
        self.active_sessions.clear()
        
        # Save final state
        self._save_comment_history()
        await self._save_stats()
        
        # Final statistics - only showing comments since we're only capturing comments
        if self.stats.start_time:
            runtime = datetime.now() - self.stats.start_time
            self.logger.info(f"📈 Final Statistics (Runtime: {str(runtime).split('.')[0]}):")
            self.logger.info(f"   💬 Comments: {self.stats.comments_captured}")
            self.logger.info(f"   🚫 Duplicates filtered: {self.stats.duplicates_filtered}")
            self.logger.info(f"   ⚠️ Rate limit hits: {self.stats.rate_limit_hits}")
            self.logger.info(f"   🔌 Connection attempts: {self.stats.connection_attempts}")
            self.logger.info(f"   ❌ Failed connections: {self.stats.failed_connections}")
            
        self.logger.info("✅ Cleanup complete")

def main():
    """Main entry point"""
    if not TIKTOK_LIVE_AVAILABLE:
        print("❌ TikTokLive library is required. Install with: pip install TikTokLive")
        sys.exit(1)
        
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="Enhanced TikTok Live Stream Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enhanced_scraper.py                                    # Use default settings
  python enhanced_scraper.py --streamers custom_streamers.txt  # Custom streamers file
  python enhanced_scraper.py --output custom_output_dir        # Custom output directory
        """
    )
    
    parser.add_argument("--streamers", default="streamers.txt",
                        help="Path to streamers configuration file")
    parser.add_argument("--output", default="output",
                        help="Output directory for scraped data")
    parser.add_argument("--config", default="config.json",
                        help="Configuration file path")
    
    args = parser.parse_args()
    
    # Create and run scraper
    scraper = EnhancedTikTokScraper(
        streamers_file=args.streamers,
        output_dir=args.output,
        config_file=args.config
    )
    
    try:
        asyncio.run(scraper.run())
    except KeyboardInterrupt:
        print("\n🛑 Scraper stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
