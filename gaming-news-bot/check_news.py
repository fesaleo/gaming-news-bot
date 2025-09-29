#!/usr/bin/env python3
"""
Enhanced Gaming News Bot for GitHub Actions
Posts gaming news to Discord with advanced filtering and persistence
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
from urllib.parse import urlparse
import difflib

# Game configurations
GAME_CONFIGS = {
    'cod': {
        'name': 'Call of Duty',
        'feeds': [
            'https://www.callofduty.com/blog.rss',
            'https://charlieintel.com/feed/',
            'https://www.dexerto.com/call-of-duty/feed',
            'https://mp1st.com/feed'
        ],
        'keywords': ['call of duty', 'cod', 'warzone', 'modern warfare', 'black ops', 'vanguard', 'treyarch', 'infinity ward'],
        'negative_keywords': ['mobile', 'candy crush', 'king'],  # Filter out mobile games
        'color': 16744192,
        'icon': '🎮',
        'max_posts_per_run': 2,
        'min_relevance_score': 1,  # Minimum keywords to match
        'thumbnail_enabled': True
    },
    'gta6': {
        'name': 'GTA 6',
        'feeds': [
            'https://www.rockstargames.com/newswire.xml',
            'https://rockstarintel.com/feed',
            'https://www.dexerto.com/gta/feed',
            'https://kotaku.com/tag/grand-theft-auto/rss'
        ],
        'keywords': ['gta 6', 'gta vi', 'grand theft auto 6', 'grand theft auto vi', 'gta6', 'gtavi', 'lucia', 'jason'],
        'negative_keywords': ['gta online', 'gta plus', 'gta+', 'shark card'],
        'color': 866614,
        'icon': '🚗',
        'max_posts_per_run': 2,
        'min_relevance_score': 1,
        'thumbnail_enabled': True
    },
    'bf6': {
        'name': 'Battlefield 6',
        'feeds': [
            'https://www.ea.com/games/battlefield/news.rss',
            'https://insider-gaming.com/tag/battlefield/feed/',
            'https://gameranx.com/tag/battlefield/feed/',
            'https://www.dexerto.com/battlefield/feed'
        ],
        'keywords': ['battlefield 6', 'battlefield', 'bf6', 'dice', 'battlefield 2042'],
        'negative_keywords': ['battlefield mobile', 'battlefield heroes'],
        'color': 16744192,
        'icon': '🪖',
        'max_posts_per_run': 2,
        'min_relevance_score': 1,
        'thumbnail_enabled': True
    },
    'arc_raiders': {
        'name': 'Arc Raiders',
        'feeds': [
            'https://www.embark-studios.com/feed',
            'https://store.steampowered.com/news/app/1808500',
            'https://www.pcgamer.com/rss/',
            'https://www.pcgamesn.com/feed'
        ],
        'keywords': ['arc raiders', 'embark studios', 'arcraiders'],
        'negative_keywords': [],
        'color': 10126617,
        'icon': '🎮',
        'max_posts_per_run': 1,
        'min_relevance_score': 1,
        'thumbnail_enabled': True
    }
}

class NewsChecker:
    def __init__(self, game_name):
        self.game_name = game_name
        self.game_config = GAME_CONFIGS[game_name]
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK')
        self.error_webhook = os.environ.get('ERROR_WEBHOOK', self.webhook_url)  # Fallback to main webhook
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        self.posted_file = self.data_dir / 'posted_articles.json'
        self.failed_file = self.data_dir / 'failed_posts.json'
        self.metrics_file = self.data_dir / 'bot_metrics.json'
        self.posted_articles = self.load_posted_articles()
        self.failed_posts = self.load_failed_posts()
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"{game_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.max_article_age_hours = 48  # Only post articles from last 48 hours
        
    def log(self, message, level='INFO'):
        """Enhanced logging with levels"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')
            
        # Send critical errors to Discord
        if level == 'ERROR' and self.error_webhook and self.error_webhook != "TEST_MODE":
            self.send_error_notification(message)
    
    def send_error_notification(self, error_message):
        """Send error notifications to Discord"""
        try:
            embed = {
                'title': '⚠️ Bot Error Alert',
                'description': f"Error in {self.game_config['name']} checker",
                'color': 15158332,  # Red
                'fields': [
                    {'name': 'Error', 'value': error_message[:1024], 'inline': False},
                    {'name': 'Game', 'value': self.game_name, 'inline': True},
                    {'name': 'Time', 'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'inline': True}
                ]
            }
            requests.post(self.error_webhook, json={'embeds': [embed]}, timeout=10)
        except:
            pass  # Don't fail the main process for error notifications
    
    def load_posted_articles(self):
        """Load previously posted article IDs with timestamp"""
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    data = json.load(f)
                # Convert old format to new format with timestamps
                game_data = data.get(self.game_name, {})
                if isinstance(game_data, list):
                    # Old format - convert to dict
                    return {article_id: None for article_id in game_data}
                return game_data
            except Exception as e:
                self.log(f"Error loading posted articles: {e}", 'ERROR')
                return {}
        return {}
    
    def load_failed_posts(self):
        """Load failed post attempts for retry"""
        if self.failed_file.exists():
            try:
                with open(self.failed_file, 'r') as f:
                    data = json.load(f)
                return data.get(self.game_name, [])
            except:
                return []
        return []
    
    def save_posted_articles(self):
        """Save posted article IDs with timestamps"""
        all_data = {}
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        # Keep only last 1000 articles with cleanup of old entries
        current_time = datetime.now()
        cleaned_articles = {}
        for article_id, timestamp in self.posted_articles.items():
            if timestamp:
                posted_time = datetime.fromisoformat(timestamp)
                if (current_time - posted_time).days < 30:  # Keep 30 days of history
                    cleaned_articles[article_id] = timestamp
            else:
                cleaned_articles[article_id] = current_time.isoformat()
        
        # Keep most recent 1000
        sorted_articles = sorted(cleaned_articles.items(), key=lambda x: x[1] or '', reverse=True)[:1000]
        all_data[self.game_name] = dict(sorted_articles)
        
        with open(self.posted_file, 'w') as f:
            json.dump(all_data, f, indent=2)
    
    def save_failed_posts(self):
        """Save failed posts for retry"""
        all_data = {}
        if self.failed_file.exists():
            try:
                with open(self.failed_file, 'r') as f:
                    all_data = json.load(f)
            except:
                pass
        
        all_data[self.game_name] = self.failed_posts[-50:]  # Keep last 50 failed posts
        
        with open(self.failed_file, 'w') as f:
            json.dump(all_data, f, indent=2)
    
    def update_metrics(self, posted_count, failed_count, total_found):
        """Track bot performance metrics"""
        metrics = {}
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    metrics = json.load(f)
            except:
                pass
        
        if self.game_name not in metrics:
            metrics[self.game_name] = {
                'total_posted': 0,
                'total_failed': 0,
                'total_found': 0,
                'last_run': None,
                'runs': 0
            }
        
        metrics[self.game_name]['total_posted'] += posted_count
        metrics[self.game_name]['total_failed'] += failed_count
        metrics[self.game_name]['total_found'] += total_found
        metrics[self.game_name]['last_run'] = datetime.now().isoformat()
        metrics[self.game_name]['runs'] += 1
        
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def clean_text(self, text):
        """Enhanced text cleaning"""
        if not text:
            return ""
        
        text = unescape(text)
        text = re.sub('<.*?>', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        if len(text) > 300:
            text = text[:297] + "..."
        
        return text
    
    def calculate_relevance_score(self, title, description):
        """Calculate relevance score based on keyword matches"""
        text = f"{title} {description}".lower()
        
        # Check negative keywords first
        for negative in self.game_config.get('negative_keywords', []):
            if negative.lower() in text:
                return -1  # Negative score means exclude
        
        # Count keyword matches
        score = 0
        matched_keywords = []
        for keyword in self.game_config['keywords']:
            if keyword.lower() in text:
                score += 1
                matched_keywords.append(keyword)
        
        return score
    
    def is_recent_article(self, published_str):
        """Check if article is recent enough to post"""
        if not published_str:
            return True  # If no date, assume it's recent
        
        try:
            # Parse various date formats
            from email.utils import parsedate_to_datetime
            published_date = parsedate_to_datetime(published_str)
            
            age = datetime.now(published_date.tzinfo) - published_date
            return age.total_seconds() < (self.max_article_age_hours * 3600)
        except:
            return True  # On parse error, assume recent
    
    def is_duplicate_cross_game(self, title, url):
        """Check if article was already posted for another game"""
        all_posted = {}
        if self.posted_file.exists():
            try:
                with open(self.posted_file, 'r') as f:
                    all_posted = json.load(f)
            except:
                return False
        
        # Check all games for similar titles or same URL
        for game, articles in all_posted.items():
            if game == self.game_name:
                continue
            
            if isinstance(articles, dict):
                for article_id in articles.keys():
                    if url and url in article_id:
                        return True
            
        return False
    
    def extract_image_from_content(self, entry):
        """Try to extract image URL from feed entry"""
        # Check common image fields
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if 'image' in media.get('type', ''):
                    return media.get('url')
        
        if hasattr(entry, 'media_thumbnail'):
            return entry.media_thumbnail[0]['url']
        
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if 'image' in enclosure.get('type', ''):
                    return enclosure.get('href')
        
        # Try to extract from content
        if hasattr(entry, 'content'):
            content = entry.content[0].value
            img_match = re.search(r'<img.*?src="(.*?)"', content)
            if img_match:
                return img_match.group(1)
        
        return None
    
    def generate_article_id(self, title, url):
        """Generate unique ID for article"""
        content = f"{title}_{url}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def fetch_feed(self, feed_url):
        """Enhanced feed fetching with better error handling"""
        try:
            self.log(f"Fetching feed: {feed_url}")
            
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                self.log(f"Feed parse warning: {feed.bozo_exception}", 'WARNING')
                # Continue anyway, might still have valid entries
            
            articles = []
            for entry in feed.entries[:15]:  # Check more entries
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                description = self.clean_text(entry.get('description', ''))
                published = entry.get('published', entry.get('updated', ''))
                
                # Skip old articles
                if not self.is_recent_article(published):
                    continue
                
                # Check relevance
                relevance_score = self.calculate_relevance_score(title, description)
                if relevance_score < self.game_config.get('min_relevance_score', 1):
                    continue
                
                # Generate unique ID
                article_id = self.generate_article_id(title, link)
                
                # Skip if already posted
                if article_id in self.posted_articles:
                    continue
                
                # Skip if cross-posted
                if self.is_duplicate_cross_game(title, link):
                    continue
                
                # Extract image if available
                image_url = self.extract_image_from_content(entry) if self.game_config.get('thumbnail_enabled') else None
                
                articles.append({
                    'id': article_id,
                    'title': title[:256],
                    'url': link,
                    'description': description,
                    'published': published,
                    'source': feed.feed.get('title', 'Unknown Source'),
                    'image': image_url,
                    'relevance_score': relevance_score
                })
            
            self.log(f"Found {len(articles)} new relevant articles from {feed_url.split('/')[2]}")
            return articles
            
        except Exception as e:
            self.log(f"Error fetching feed {feed_url}: {e}", 'ERROR')
            return []
    
    def post_to_discord(self, article, retry_count=0):
        """Enhanced Discord posting with retries and better embeds"""
        if not self.webhook_url:
            self.log("No Discord webhook URL set!", 'ERROR')
            return False
        
        if self.webhook_url == "TEST_MODE":
            self.log(f"TEST MODE - Would post: {article['title']}")
            return True
        
        try:
            # Build embed
            embed = {
                'title': f"{self.game_config['icon']} {article['title']}",
                'url': article['url'],
                'description': article['description'],
                'color': self.game_config['color'],
                'fields': [
                    {
                        'name': '📰 Source',
                        'value': article['source'][:100],
                        'inline': True
                    }
                ],
                'footer': {
                    'text': f"Gaming News Bot | Relevance: {'⭐' * article['relevance_score']}"
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add image if available
            if article.get('image'):
                embed['thumbnail'] = {'url': article['image']}
            
            # Add published date if available
            if article.get('published'):
                embed['fields'].append({
                    'name': '📅 Published',
                    'value': article['published'][:100],
                    'inline': True
                })
            
            # Send to Discord with timeout
            response = requests.post(
                self.webhook_url, 
                json={'embeds': [embed]},
                timeout=10
            )
            
            if response.status_code == 204:
                self.log(f"Successfully posted: {article['title'][:50]}...")
                self.posted_articles[article['id']] = datetime.now().isoformat()
                
                # Remove from failed posts if it was there
                if article in self.failed_posts:
                    self.failed_posts.remove(article)
                
                return True
            else:
                raise Exception(f"Discord API returned {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            self.log(f"Timeout posting to Discord (attempt {retry_count + 1})", 'WARNING')
        except Exception as e:
            self.log(f"Error posting to Discord: {e}", 'ERROR')
        
        # Retry logic
        if retry_count < 2:  # Max 3 attempts
            time.sleep(2 ** retry_count)  # Exponential backoff
            return self.post_to_discord(article, retry_count + 1)
        
        # Save as failed post for later retry
        if article not in self.failed_posts:
            self.failed_posts.append(article)
        
        return False
    
    def check_similar_titles(self, articles):
        """Remove articles with very similar titles"""
        unique = []
        seen_titles = []
        
        for article in articles:
            is_duplicate = False
            
            for seen in seen_titles:
                similarity = difflib.SequenceMatcher(None, 
                    article['title'].lower(), 
                    seen.lower()
                ).ratio()
                
                if similarity > 0.85:  # 85% similar
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(article)
                seen_titles.append(article['title'])
        
        return unique
    
    def retry_failed_posts(self):
        """Retry previously failed posts"""
        if not self.failed_posts:
            return 0
        
        self.log(f"Retrying {len(self.failed_posts)} failed posts")
        retry_count = 0
        
        for article in self.failed_posts[:3]:  # Retry up to 3 failed posts
            if self.post_to_discord(article):
                retry_count += 1
                time.sleep(2)
        
        self.save_failed_posts()
        return retry_count
    
    def check_news(self):
        """Main function to check news and post"""
        self.log(f"Starting news check for {self.game_config['name']}")
        
        if not self.webhook_url:
            self.log("No Discord webhook URL set!", 'ERROR')
            return
        
        # Retry failed posts first
        retried = self.retry_failed_posts()
        
        all_articles = []
        
        # Fetch from all feeds
        for feed_url in self.game_config['feeds']:
            articles = self.fetch_feed(feed_url)
            all_articles.extend(articles)
            time.sleep(1)  # Rate limiting
        
        # Remove similar titles
        unique_articles = self.check_similar_titles(all_articles)
        
        # Sort by relevance and date
        unique_articles.sort(
            key=lambda x: (x['relevance_score'], x.get('published', '')), 
            reverse=True
        )
        
        self.log(f"Found {len(unique_articles)} unique new articles")
        
        # Post articles
        posted_count = 0
        failed_count = 0
        max_posts = self.game_config.get('max_posts_per_run', 2)
        
        for article in unique_articles[:max_posts]:
            if self.post_to_discord(article):
                posted_count += 1
            else:
                failed_count += 1
            time.sleep(2)  # Rate limiting
        
        # Save state
        self.save_posted_articles()
        self.save_failed_posts()
        self.update_metrics(posted_count + retried, failed_count, len(all_articles))
        
        # Summary
        self.log(f"Posted {posted_count} new articles, {retried} retried, {failed_count} failed")
        self.log(f"Total posted articles tracked: {len(self.posted_articles)}")

def main():
    parser = argparse.ArgumentParser(description='Enhanced Gaming News Bot')
    parser.add_argument('--game', required=True, choices=GAME_CONFIGS.keys(),
                      help='Game to check news for')
    parser.add_argument('--test', action='store_true',
                      help='Test mode - don\'t post to Discord')
    
    args = parser.parse_args()
    
    if args.test:
        os.environ['DISCORD_WEBHOOK'] = 'TEST_MODE'
        print(f"TEST MODE - Checking {args.game}")
    
    checker = NewsChecker(args.game)
    checker.check_news()

if __name__ == '__main__':
    main()
