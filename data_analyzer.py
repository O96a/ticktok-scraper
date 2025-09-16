#!/usr/bin/env python3
"""
TikTok Scraper Data Analyzer
Analyzes and reports on scraped TikTok data
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any
import re

class TikTokDataAnalyzer:
    """Analyze scraped TikTok data and generate reports"""
    
    def __init__(self, data_dir: str = "output"):
        self.data_dir = Path(data_dir)
        self.data = []
        self.stats = defaultdict(int)
        self.streamer_stats = defaultdict(lambda: defaultdict(int))
        
    def load_data(self, days_back: int = 7):
        """Load data from the last N days"""
        print(f"📂 Loading data from {self.data_dir} (last {days_back} days)")
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        files_loaded = 0
        
        # Look for both old format and new format files
        patterns = ["tiktok-rawdata-*.txt", "tiktok-comments-*.txt"]
        
        for pattern in patterns:
            for file_path in self.data_dir.glob(pattern):
                try:
                    # Check file modification time
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        continue
                        
                    print(f"  📄 Loading {file_path.name}")
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                                
                            try:
                                # Try to parse as JSON first (new format)
                                if line.startswith('{'):
                                    data = json.loads(line)
                                    self.data.append(data)
                                    
                                    # Track basic stats
                                    self.stats['total_events'] += 1
                                    event_type = data.get('event_type', 'unknown')
                                    self.stats[f'{event_type}_events'] += 1
                                    
                                    # Track per-streamer stats
                                    streamer = data.get('streamer', 'unknown')
                                    self.streamer_stats[streamer]['total_events'] += 1
                                    self.streamer_stats[streamer][f'{event_type}_events'] += 1
                                    
                                else:
                                    # Parse as text format - try both new and old formats
                                    parts = line.split('|')
                                    
                                    if len(parts) == 2:
                                        # New format: user|content (no timestamp)
                                        user, content = parts
                                        
                                        # Extract streamer name from filename
                                        filename = file_path.name
                                        if 'tiktok-rawdata-' in filename:
                                            streamer = filename.replace('tiktok-rawdata-', '').split('-')[0]
                                        elif 'tiktok-comments-' in filename:
                                            streamer = filename.replace('tiktok-comments-', '').split('-')[0]
                                        else:
                                            streamer = 'unknown'
                                        
                                        # Use file time as timestamp for new format
                                        timestamp_str = file_time.isoformat()
                                        
                                    elif len(parts) == 3:
                                        # Old format: timestamp|user|content
                                        timestamp_str, user, content = parts
                                        
                                        # Extract streamer name from filename
                                        filename = file_path.name
                                        if 'tiktok-rawdata-' in filename:
                                            streamer = filename.replace('tiktok-rawdata-', '').split('-')[0]
                                        elif 'tiktok-comments-' in filename:
                                            streamer = filename.replace('tiktok-comments-', '').split('-')[0]
                                        else:
                                            streamer = 'unknown'
                                            
                                    else:
                                        # Skip malformed lines
                                        continue
                                    
                                    # Determine event type based on content
                                    event_type = 'comment'
                                    if user == 'SYSTEM':
                                        event_type = 'system'
                                    elif content.startswith('❤️'):
                                        event_type = 'like'
                                    elif content.startswith('🔄'):
                                        event_type = 'share'
                                    elif content.startswith('➕'):
                                        event_type = 'follow'
                                    
                                    # Create standardized data structure
                                    data = {
                                        'timestamp': timestamp_str,
                                        'event_type': event_type,
                                        'streamer': streamer,
                                        'user': user,
                                        'content': content
                                    }
                                    
                                    self.data.append(data)
                                    
                                    # Track basic stats
                                    self.stats['total_events'] += 1
                                    self.stats[f'{event_type}_events'] += 1
                                    
                                    # Track per-streamer stats
                                    self.streamer_stats[streamer]['total_events'] += 1
                                    self.streamer_stats[streamer][f'{event_type}_events'] += 1
                                        
                            except (json.JSONDecodeError, ValueError) as e:
                                print(f"    ⚠️ Parse error in {file_path.name}:{line_num}: {e}")
                                
                    files_loaded += 1
                    
                except Exception as e:
                    print(f"    ❌ Error loading {file_path.name}: {e}")
                    
        print(f"✅ Loaded {len(self.data)} events from {files_loaded} files")
        
    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        if not self.data:
            return "❌ No data loaded. Run load_data() first."
            
        report = []
        report.append("=" * 60)
        report.append("📊 TIKTOK SCRAPER DATA ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Overall statistics
        report.append("📈 OVERALL STATISTICS")
        report.append("-" * 30)
        for key, value in sorted(self.stats.items()):
            if key != 'total_events':
                report.append(f"  {key.replace('_', ' ').title()}: {value:,}")
        report.append("")
        
        # Time range analysis
        if self.data:
            timestamps = [datetime.fromisoformat(event.get('timestamp', '')) 
                         for event in self.data if event.get('timestamp')]
            if timestamps:
                start_time = min(timestamps)
                end_time = max(timestamps)
                duration = end_time - start_time
                
                report.append("⏰ TIME RANGE")
                report.append("-" * 30)
                report.append(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                report.append(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                report.append(f"  Duration: {duration}")
                
                # Events per hour
                if duration.total_seconds() > 0:
                    events_per_hour = len(self.data) / (duration.total_seconds() / 3600)
                    report.append(f"  Events per hour: {events_per_hour:.1f}")
                report.append("")
        
        # Streamer statistics
        report.append("👥 STREAMER STATISTICS")
        report.append("-" * 30)
        for streamer, stats in sorted(self.streamer_stats.items(), 
                                    key=lambda x: x[1]['total_events'], reverse=True):
            report.append(f"  📺 {streamer}:")
            for event_type, count in sorted(stats.items()):
                if event_type != 'total_events':
                    report.append(f"    {event_type.replace('_', ' ').title()}: {count:,}")
            report.append("")
            
        # Top commenters
        commenters = Counter()
        for event in self.data:
            if event.get('event_type') == 'comment':
                commenters[event.get('user', 'unknown')] += 1
                
        if commenters:
            report.append("💬 TOP COMMENTERS")
            report.append("-" * 30)
            for commenter, count in commenters.most_common(10):
                report.append(f"  {commenter}: {count:,} comments")
            report.append("")
            
        # Comment analysis
        comments = [event.get('content', '') for event in self.data 
                   if event.get('event_type') == 'comment']
        
        if comments:
            report.append("📝 COMMENT ANALYSIS")
            report.append("-" * 30)
            
            # Language detection (basic)
            arabic_comments = sum(1 for comment in comments if self._contains_arabic(comment))
            english_comments = sum(1 for comment in comments if self._contains_english(comment))
            
            report.append(f"  Total comments: {len(comments):,}")
            report.append(f"  Arabic comments: {arabic_comments:,} ({arabic_comments/len(comments)*100:.1f}%)")
            report.append(f"  English comments: {english_comments:,} ({english_comments/len(comments)*100:.1f}%)")
            
            # Average comment length
            avg_length = sum(len(comment) for comment in comments) / len(comments)
            report.append(f"  Average length: {avg_length:.1f} characters")
            
            # Most common words (basic analysis)
            all_words = []
            for comment in comments:
                # Simple word extraction
                words = re.findall(r'\b\w+\b', comment.lower())
                all_words.extend(words)
                
            if all_words:
                word_counter = Counter(all_words)
                # Filter out very short words and numbers
                filtered_words = {word: count for word, count in word_counter.items() 
                                if len(word) > 2 and not word.isdigit()}
                
                report.append("  Most common words:")
                for word, count in Counter(filtered_words).most_common(10):
                    report.append(f"    '{word}': {count:,}")
            report.append("")
            
        # Activity patterns
        if self.data:
            report.append("📅 ACTIVITY PATTERNS")
            report.append("-" * 30)
            
            # Activity by hour
            hourly_activity = defaultdict(int)
            daily_activity = defaultdict(int)
            
            for event in self.data:
                timestamp_str = event.get('timestamp')
                if timestamp_str:
                    try:
                        dt = datetime.fromisoformat(timestamp_str)
                        hourly_activity[dt.hour] += 1
                        daily_activity[dt.strftime('%Y-%m-%d')] += 1
                    except:
                        continue
                        
            if hourly_activity:
                report.append("  Activity by hour:")
                for hour in sorted(hourly_activity.keys()):
                    count = hourly_activity[hour]
                    bar = "█" * min(50, count // max(1, max(hourly_activity.values()) // 50))
                    report.append(f"    {hour:2d}:00 {count:4d} {bar}")
                report.append("")
                
            if daily_activity:
                report.append("  Activity by day:")
                for day in sorted(daily_activity.keys()):
                    count = daily_activity[day]
                    report.append(f"    {day}: {count:,} events")
                report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)
        
    def _contains_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
        return bool(arabic_pattern.search(text))
        
    def _contains_english(self, text: str) -> bool:
        """Check if text contains English characters"""
        english_pattern = re.compile(r'[a-zA-Z]')
        return bool(english_pattern.search(text))
        
    def export_summary(self, output_file: str):
        """Export summary to JSON file"""
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_events': len(self.data),
            'stats': dict(self.stats),
            'streamer_stats': {k: dict(v) for k, v in self.streamer_stats.items()}
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
            
        print(f"📊 Summary exported to {output_file}")
        
    def search_comments(self, query: str, case_sensitive: bool = False) -> List[Dict]:
        """Search for specific comments"""
        results = []
        query_lower = query.lower() if not case_sensitive else query
        
        for event in self.data:
            if event.get('event_type') == 'comment':
                content = event.get('content', '')
                search_content = content if case_sensitive else content.lower()
                
                if query_lower in search_content:
                    results.append(event)
                    
        return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="TikTok Scraper Data Analyzer")
    parser.add_argument("--data-dir", default="output", 
                        help="Directory containing scraped data")
    parser.add_argument("--days", type=int, default=7,
                        help="Number of days back to analyze")
    parser.add_argument("--export", help="Export summary to JSON file")
    parser.add_argument("--search", help="Search for specific comments")
    parser.add_argument("--case-sensitive", action="store_true",
                        help="Case-sensitive search")
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = TikTokDataAnalyzer(args.data_dir)
    
    # Load data
    analyzer.load_data(args.days)
    
    if args.search:
        # Search functionality
        results = analyzer.search_comments(args.search, args.case_sensitive)
        print(f"\n🔍 Search results for '{args.search}' ({len(results)} found):")
        print("-" * 50)
        
        for i, result in enumerate(results[:20], 1):  # Show first 20
            timestamp = result.get('timestamp', 'unknown')
            user = result.get('user', 'unknown')
            content = result.get('content', '')
            streamer = result.get('streamer', 'unknown')
            
            print(f"{i:2d}. [{timestamp}] @{streamer} - {user}: {content}")
            
        if len(results) > 20:
            print(f"... and {len(results) - 20} more results")
    else:
        # Generate and display report
        report = analyzer.generate_report()
        print(report)
        
    # Export if requested
    if args.export:
        analyzer.export_summary(args.export)

if __name__ == "__main__":
    main()
