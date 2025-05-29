# EtymoBot Quick Start Guide 🚀

Get your etymology bot running in minutes with our GitHub-native pipeline!

## 🔑 Prerequisites

1. **GitHub Account** - Free account with Actions enabled
2. **Twitter API Credentials** - Get from [Twitter Developer Portal](https://developer.twitter.com/en/portal)
   - Consumer Key/Secret  
   - Access Token/Secret

## ⚡ Quick Deploy (Recommended)

### 1. Fork this repository

Click "Fork" in the top-right corner to create your own copy.

### 2. Configure Repository Secrets

Go to your fork's Settings → Secrets and variables → Actions, and add:

```bash
TWITTER_CONSUMER_KEY=your-consumer-key
TWITTER_CONSUMER_SECRET=your-consumer-secret
TWITTER_ACCESS_TOKEN=your-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret
```

### 3. Enable GitHub Actions

1. Go to the "Actions" tab in your fork
2. Click "I understand my workflows, go ahead and enable them"

### 4. Initial Setup

1. Go to Actions → "Weekly Corpus Refresh" → "Run workflow" 
2. Wait 10-15 minutes for the etymology corpus to build
3. Your bot will automatically start posting 3x daily!

**That's it!** Your bot is now fully automated and will:
- 🔄 Refresh etymology data weekly
- 📱 Post tweets 3x daily at optimal times
- 📊 Track all posted pairs automatically

## 💻 Local Testing (Optional)

Want to test locally before deploying? Here's how:

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/etymological.git
cd etymological

# Install dependencies  
pip install tweepy

# Download Wiktionary dump (2.2GB)
curl -o data/wiktionary-data.jsonl.gz https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz
```

### Test Commands

```bash
# Build etymology corpus (takes 5-10 minutes)
python scripts/build_roots.py

# Test tweet generation (safe - no posting)
python scripts/post.py --dry-run

# Check corpus statistics
python scripts/build_roots.py --max-entries 1000  # Smaller test corpus
```

## 🛠️ Advanced Configuration

### Custom Posting Schedule

Edit `.github/workflows/post-tweets.yml` line 6:
```yaml
- cron: '0 13,17,19 * * *'  # 9AM, 1PM, 3PM EST
```

Change to your preferred times (in UTC).

### Monitoring Your Bot

- **Actions tab**: See workflow run history
- **Data folder**: Check `posted.csv` for tweet history  
- **Corpus stats**: View etymology data in `roots.json.gz`

### Troubleshooting

**No tweets posting?**
- Check if secrets are set correctly
- Verify workflows are enabled
- Ensure corpus build completed successfully

**Workflow failures?**
- Check Actions tab for error logs
- Verify Twitter API credentials
- Check if rate limits were hit

## 📋 What Happens Next

Once set up, your bot will:

- **📚 Build Corpus**: Extract 3,000+ etymological roots from Wiktionary
- **🎯 Smart Selection**: Choose unposted word pairs with authentic connections
- **📝 Generate Tweets**: Create engaging content using curated templates
- **⏰ Optimal Timing**: Post 3x daily during peak engagement hours
- **📊 Track History**: Avoid repeating pairs and maintain quality

## 📖 Example Bot Output

> gustable/gusty: "gustus" splits into gustable vs gusty.

> weary/worse: "wer" branches into weary vs worse.

> carriage/cargo: "carrus" evolved into carriage vs cargo.

## 🏗️ Project Structure

```
etymological/
├── scripts/
│   ├── build_roots.py      # Extract etymology corpus from Wiktionary
│   └── post.py            # Generate and post tweets
├── data/
│   ├── roots.json.gz      # Etymology corpus (auto-generated)
│   └── posted.csv         # Tweet history (auto-updated)
└── .github/workflows/
    ├── roots-refresh.yml  # Weekly corpus refresh
    └── post-tweets.yml    # 3x daily posting
```

## 🚀 Next Steps

- **Customize**: Edit templates in `scripts/post.py`
- **Monitor**: Watch your bot's performance in the Actions tab
- **Scale**: The system handles 10,000+ word relationships automatically
- **Improve**: Submit issues or PRs to enhance the bot

Your EtymoBot is now live and will continue running automatically! 🎉

