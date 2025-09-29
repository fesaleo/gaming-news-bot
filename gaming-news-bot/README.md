# 🎮 Gaming News Bot - GitHub Actions Edition

A free, serverless Discord news bot that runs on GitHub Actions. Posts gaming news for Call of Duty, GTA 6, Battlefield 6, and Arc Raiders.

## ✨ Features

- **100% Free** - Runs on GitHub Actions (no hosting costs)
- **Automatic** - Checks every 15 minutes
- **Smart** - Avoids duplicate posts
- **Reliable** - GitHub's infrastructure (99.9% uptime)
- **No Maintenance** - Set and forget

## 🚀 Setup Instructions (10 minutes)

### Step 1: Create Discord Webhooks

1. Open Discord and go to your server
2. For each news channel:
   - Click the gear icon next to the channel name
   - Go to **Integrations** → **Webhooks**
   - Click **Create Webhook**
   - Give it a name (e.g., "COD News Bot")
   - Copy the webhook URL
   - Save it for Step 3

You need 4 webhook URLs total (one per game channel).

### Step 2: Fork/Create GitHub Repository

#### Option A: Fork (Easiest)
1. Go to GitHub and sign in
2. Fork this repository
3. You now have your own copy

#### Option B: Create New
1. Go to [github.com/new](https://github.com/new)
2. Name it `gaming-news-bot`
3. Make it **Public** (for unlimited Actions runtime)
4. Create repository

### Step 3: Add Discord Webhooks as Secrets

1. In your repository, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these 4 secrets:

   | Name | Value |
   |------|-------|
   | `DISCORD_WEBHOOK_COD` | Your COD channel webhook URL |
   | `DISCORD_WEBHOOK_GTA6` | Your GTA 6 channel webhook URL |
   | `DISCORD_WEBHOOK_BF6` | Your Battlefield 6 channel webhook URL |
   | `DISCORD_WEBHOOK_ARC` | Your Arc Raiders channel webhook URL |

### Step 4: Upload Bot Files

1. In your repository, click **Add file** → **Create new file**
2. Create these files:

#### File 1: `.github/workflows/news-checker.yml`
- Name the file exactly as shown (with the folders)
- Copy and paste the workflow content
- Commit

#### File 2: `check_news.py`
- Copy and paste the Python script
- Commit

#### File 3: `requirements.txt`
- Copy and paste the requirements
- Commit

#### File 4: `data/posted_articles.json`
- Create an empty JSON file with just `{}`
- This stores which articles have been posted
- Commit

### Step 5: Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. Click **I understand my workflows, go ahead and enable them**
3. Click on **Gaming News Checker** workflow
4. Click **Enable workflow**

### Step 6: Test It!

1. Go to **Actions** tab
2. Click **Gaming News Checker**
3. Click **Run workflow** → **Run workflow**
4. Watch it run! (Takes about 30 seconds)
5. Check your Discord channels for news posts

## 📅 Posting Schedule

The bot checks for news every 15 minutes and posts:
- **COD**: Maximum 2 articles per check
- **GTA 6**: Maximum 2 articles per check  
- **Battlefield 6**: Maximum 2 articles per check
- **Arc Raiders**: Maximum 1 article per check

This prevents spam while ensuring you don't miss important news.

## 🔧 Customization

### Change RSS Feeds
Edit `check_news.py` and modify the `feeds` list for each game:
```python
'feeds': [
    'https://your-rss-feed-here.com/rss',
    # Add more feeds
]
```

### Change Posting Frequency
Edit `.github/workflows/news-checker.yml`:
```yaml
- cron: '*/30 * * * *'  # Every 30 minutes instead of 15
```

### Change Max Posts Per Run
Edit `check_news.py`:
```python
'max_posts_per_run': 3  # Post up to 3 articles per check
```

### Add More Games
1. Add a new webhook secret in GitHub
2. Add game config in `check_news.py`
3. Add a new step in the workflow

## 📊 Monitoring

### View Logs
1. Go to **Actions** tab
2. Click on any workflow run
3. Click on a job to see detailed logs

### Check Posted Articles
The `data/posted_articles.json` file tracks all posted articles to prevent duplicates.

## 🆘 Troubleshooting

### Bot Not Running?
- Check **Actions** tab for errors
- Verify webhook URLs are correct in Secrets
- Make sure repository is public (or you have Actions minutes)

### Not Finding News?
- Check if RSS feeds are still active
- Adjust keywords in `check_news.py`
- Some feeds might be region-blocked

### Duplicate Posts?
- The bot tracks posted articles in `posted_articles.json`
- If you delete this file, it might repost old articles

### Rate Limited by Discord?
- Reduce `max_posts_per_run` in config
- Increase delay between posts in code

## 💡 Pro Tips

1. **Star Your Repository** - Makes it easier to find
2. **Watch Repository** - Get notifications of issues
3. **Check Actions Usage** - Monitor your free minutes (unlimited for public repos)
4. **Backup Webhooks** - Save webhook URLs somewhere safe
5. **Test Changes** - Use manual workflow run to test

## 📈 GitHub Actions Limits

- **Public Repository**: Unlimited Actions minutes! 
- **Private Repository**: 2,000 minutes/month free
- **Storage**: 500MB free (more than enough)
- **Concurrent Jobs**: 20 for free accounts
- **Workflow Run Time**: Maximum 6 hours (you'll use ~10 seconds)

## 🔒 Security Notes

- Webhook URLs are stored as encrypted secrets
- Nobody can see your webhook URLs in the code
- GitHub Actions is secure and trusted
- The bot only posts to Discord, doesn't read messages

## 🎉 You're Done!

Your bot will now:
- Run every 15 minutes automatically
- Check all RSS feeds for gaming news
- Post to Discord with nice embeds
- Never post duplicates
- Cost you $0 forever

No maintenance needed - it just works!

## 📝 License

MIT - Use however you want!

---

**Need help?** Open an issue in the repository or check the Actions logs for errors.