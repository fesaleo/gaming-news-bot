#!/usr/bin/env python3
"""
Gaming News Checker for GitHub Actions
Posts gaming news to Discord via webhooks
"""

import feedparser
import requests
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import time
import re
from html import unescape

# Game configurations
GAME_CONFIGS = {
    'cod': {
        'name': 'Call of Duty',
        'feeds': [
            'https://charlieintel.com/feed/',
            'https://www.reddit.com/r/ModernWarfareIII/.rss',
            'https://www.ign.com/games/call-of-duty/rss',
            'https://www.gamesradar.com/tag/call-of-duty/feed/'
        ],
        'keywords': ['call of duty', 'cod', 'warzone', 'modern warfare', 'black ops'],
        'color': 16744192,  # Orange
        'icon': '🎮',
        'max_posts_per_run': 2
    },
    'gta6': {
        'name': 'GTA 6',
        'feeds': [
            'https://www.reddit.com/r/GTA6/.rss',
            'https://www.reddit.com/r/GrandTheftAutoVI/.rss',
            'https://www.rockstargames.com/newswire.xml',
            'https://rockstarintel.com/feed',
            'https://www.ign.com/games/grand-theft-auto-vi/rss',
            'https://www.gamesradar.com/tag/gta-6/feed/',
            'https://kotaku.com/tag/grand-theft-auto/rss'
        ],
        'keywords': ['gta 6', 'gta vi', 'grand theft auto 6', 'grand theft auto vi', 'gta6', 'gtavi'],
        'color': 866614,  # Dark Green
        'icon': '🚗',
        'max_posts_per_run': 2
    },
    'bf6': {
        'name': 'Battlefield 6',
        'feeds': [
            'https://www.reddit.com/r/Battlefield/.rss',
            'https://insider-gaming.com/tag/battlefield/feed/',
            'https://gameranx.com/tag/battlefield/feed/',
            'https://comicbook.com/tag/battlefield/feed/'
        ],
        'keywords': ['battlefield 6', 'battlefield', 'bf6', 'dice'],
        'color': 16744192,  # Orange
        'icon': '🪖',
        'max_posts_per_run': 2
    },
    'arc_raiders': {
        'name': 'Arc Raiders',
        'feeds': [
            'https://www.reddit.com/r/ARCRaiders/.rss',
            'https://store.steampowered.com/news/app/1808500',
            'https://gamingintel.com/feed/',
            'https://gamepur.com/feed/'
        ],
        'keywords': ['arc raiders', 'embark studios', 'arcraiders'],
        'color': 10126617,  # Purple
        'icon': '🎮',
        'max_posts_per_run': 1
    }
}

class NewsChecker:
    def __init__(self, game_name):
        self.game_name = game_name
        self.game_config = GAME_CONFIGS[game_name]
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK')
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        self.posted_file = self.data_dir / 'posted_articles.json'
        self.posted_articles = self.load_posted_articles()
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"{game_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def log(self, message):
        """Log message to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')
    
    def load_posted_articles(self):
        """Load previously posted article IDs"""
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    data = json.load(f)
                return set(data.get(self.game_name, []))
            except:
                return set()
        return set()
    
    def save_posted_articles(self):
        """Save posted article IDs"""
        # Load all games' data
        all_data = {}
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        # Convert set to list for JSON serialization
        all_data[self.game_name] = list(self.posted_articles)[-1000:]  # Keep last 1000
        
        # Save back
        with open(self.posted_file, 'w') as f:
            json.dump(all_data, f, indent=2)
    
    def clean_text(self, text):
        """Clean HTML and format text"""
        if not text:
            return ""
        
        # Unescape HTML entities
        text = unescape(text)
        
        # Remove HTML tags
        text = re.sub('<.*?>', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Truncate if needed
        if len(text) > 200:
            text = text[:197] + "..."
        
        return text
    
    def is_relevant(self, title, description):
        """Check if article is relevant based on keywords"""
        text = f"{title} {description}".lower()
        
        # Special handling for Arc Raiders - needs exact match
        if self.game_name == 'arc_raiders':
            return any(keyword in text for keyword in self.game_config['keywords'])
        
        # For other games, check keywords
        return any(keyword in text for keyword in self.game_config['keywords'])
    
    def generate_article_id(self, title, url):
        """Generate unique ID for article"""
        content = f"{title}_{url}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def fetch_feed(self, feed_url):
        """Fetch and parse RSS feed"""
        try:
            self.log(f"Fetching feed: {feed_url}")
            
            # Parse feed without timeout parameter
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                self.log(f"Feed error: {feed.bozo_exception}")
                return []
            
            articles = []
            for entry in feed.entries[:10]:  # Check latest 10
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                description = self.clean_text(entry.get('description', ''))
                published = entry.get('published', '')
                
                # Generate unique ID
                article_id = self.generate_article_id(title, link)
                
                # Skip if already posted
                if article_id in self.posted_articles:
                    continue
                
                articles.append({
                    'id': article_id,
                    'title': title[:256],  # Discord limit
                    'url': link,
                    'description': description,
                    'published': published,
                    'source': feed.feed.get('title', 'Unknown Source')
                })
            
            self.log(f"Found {len(articles)} new relevant articles")
            return articles
            
        except Exception as e:
            self.log(f"Error fetching feed: {e}")
            return []
    
    def post_to_discord(self, article):
        """Post article to Discord webhook"""
        if not self.webhook_url:
            self.log("ERROR: No Discord webhook URL set!")
            self.log("Please set DISCORD_WEBHOOK environment variable")
            return False
        
        if self.webhook_url == "TEST_MODE":
            self.log(f"TEST MODE - Would post: {article['title']}")
            return True
        
        try:
            # Create embed
            embed = {
                'title': f"{self.game_config['icon']} {article['title']}",
                'url': article['url'],
                'description': article['description'],
                'color': self.game_config['color'],
                'fields': [
                    {
                        'name': 'Source',
                        'value': article['source'][:100],
                        'inline': True
                    }
                ],
                'footer': {
                    'text': f"Gaming News Bot"
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add published date if available
            if article['published']:
                embed['fields'].append({
                    'name': 'Published',
                    'value': article['published'][:100],
                    'inline': True
                })
            
            # Send to Discord
            response = requests.post(self.webhook_url, json={'embeds': [embed]})
            
            if response.status_code == 204:
                self.log(f"Posted: {article['title'][:50]}...")
                self.posted_articles.add(article['id'])
                return True
            else:
                self.log(f"Discord error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"Error posting to Discord: {e}")
            return False
    
    def check_news(self):
        """Main function to check news and post"""
        self.log(f"Starting news check for {self.game_config['name']}")
        
        if not self.webhook_url:
            self.log("ERROR: No Discord webhook URL set!")
            self.log("Please set DISCORD_WEBHOOK environment variable")
            return
        
        all_articles = []
        
        # Fetch from all feeds
        for feed_url in self.game_config['feeds']:
            articles = self.fetch_feed(feed_url)
            all_articles.extend(articles)
            time.sleep(0.5)  # Small delay between feeds
        
        # Remove duplicates based on title similarity
        unique_articles = []
        seen_titles = []
        
        for article in all_articles:
            # Check relevance first
            if not self.is_relevant(article['title'], article['description']):
                continue
                
            # Simple duplicate check
            title_words = set(article['title'].lower().split())
            is_duplicate = False
            
            for seen in seen_titles:
                if len(title_words.intersection(seen)) > len(title_words) * 0.7:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.append(title_words)
        
        # Sort by published date if available
        unique_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
        
        self.log(f"Found {len(unique_articles)} unique new articles")
        
        # Post articles (limited per run)
        posted_count = 0
        max_posts = self.game_config.get('max_posts_per_run', 2)
        
        for article in unique_articles[:max_posts]:
            if self.post_to_discord(article):
                posted_count += 1
                time.sleep(2)  # Delay between posts to avoid rate limiting
        
        self.log(f"Posted {posted_count} articles")
        
        # Save posted articles
        self.save_posted_articles()
        self.log(f"Saved {len(self.posted_articles)} posted articles")

def main():
    parser = argparse.ArgumentParser(description='Check gaming news and post to Discord')
    parser.add_argument('--game', required=True, choices=GAME_CONFIGS.keys(),
                      help='Game to check news for')
    parser.add_argument('--test', action='store_true',
                      help='Test mode - don\'t post to Discord')
    
    args = parser.parse_args()
    
    # Test mode
    if args.test:
        os.environ['DISCORD_WEBHOOK'] = 'TEST_MODE'
        print(f"TEST MODE - Checking {args.game}")
    
    checker = NewsChecker(args.game)
    checker.check_news()

if __name__ == '__main__':
    main()
