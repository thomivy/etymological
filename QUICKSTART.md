# EtymoBot Quick Start Guide 🚀

Get your etymology bot running in minutes!

## 🔑 Prerequisites

1. **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/api-keys)
2. **Twitter API Credentials** - Get from [Twitter Developer Portal](https://developer.twitter.com/en/portal)
   - Bearer Token
   - Consumer Key/Secret  
   - Access Token/Secret

## ⚡ Quick Deploy (GitHub Actions)

1. **Fork this repository**

2. **Set repository secrets** (Settings → Secrets and variables → Actions):
   ```
   OPENAI_API_KEY=your-openai-key
   TWITTER_BEARER_TOKEN=your-bearer-token
   TWITTER_CONSUMER_KEY=your-consumer-key
   TWITTER_CONSUMER_SECRET=your-consumer-secret
   TWITTER_ACCESS_TOKEN=your-access-token
   TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret
   ```

3. **Enable GitHub Actions** (Actions tab → Enable workflows)

4. **Trigger first run** (Actions → EtymoBot Posting → Run workflow)

**Done!** Your bot will now post 3 times daily at optimal hours.

## 🐳 Docker Deploy

```bash
# Clone and setup
git clone your-fork-url
cd etymological
cp env.example .env
# Edit .env with your API keys

# Build initial cache
docker-compose --profile init up etymobot-cache-builder

# Start bot
docker-compose up etymobot
```

## 💻 Local Setup

### Option 1: Using the Package (Recommended)

```bash
# Install dependencies and package
pip install -r requirements.txt
pip install -e .

# Set environment variables
export OPENAI_API_KEY="your-key"
export TWITTER_BEARER_TOKEN="your-token"
# ... set all required vars

# Build cache (takes 10-15 minutes)
etymobot --build-cache

# Test single tweet
etymobot --mode single

# Start scheduled posting
etymobot --mode scheduled
```

### Option 2: Using the Main Script

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key"
export TWITTER_BEARER_TOKEN="your-token"
# ... set all required vars

# Build cache (takes 10-15 minutes)
python main.py --build-cache

# Test single tweet
python main.py --mode single

# Start scheduled posting
python main.py --mode scheduled
```

## 🛠️ Advanced Usage

### Statistics and Monitoring

```bash
# Show bot statistics
etymobot --stats

# Dry run (generate tweet without posting)
etymobot --dry-run

# Verbose logging
etymobot --verbose --mode single

# Custom database location
etymobot --db /path/to/custom.sqlite --stats
```

### Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black src/ tests/

# Type checking
mypy src/
```

## 📋 What Happens Next

- **Cache Building**: Bot discovers 1000+ word-root mappings
- **Smart Posting**: Posts only during peak hours (9 AM, 1 PM, 3 PM EST)
- **Content Quality**: AI generates engaging tweets about word pairs using 5 different stylistic templates
- **Stylistic Variation**: Randomly rotates between Statement+Twist, Question Hook, Mini Anecdote, Fragment+Aside, and One-Liner Aphorism formats
- **Self-Improvement**: Skips problematic words, tracks what's been posted

## 🔧 Troubleshooting

**Missing credentials**: Verify all API keys are set correctly
**No tweets**: Check if current time is optimal (9/13/15 EST)  
**Cache empty**: Run `--build-cache` first
**Rate limits**: Built-in handling, just wait
**Import errors**: Make sure to install with `pip install -e .`

## 📖 Example Tweet

> Sporadic and diaspora sprout from Greek speirein, to sow. One names lonely seeds scattered by wind, the other a people scattered by history. Every grain carries a map of home.

## 🏗️ Project Structure

```
etymological/
├── src/etymobot/           # Main package
│   ├── bot.py             # Core bot logic
│   ├── config.py          # Configuration
│   ├── database.py        # Database operations
│   ├── etymology.py       # Etymology discovery
│   ├── services.py        # External APIs
│   └── cli.py            # Command-line interface
├── tests/                  # Test suite
├── main.py                # Entry point script
├── pyproject.toml         # Package configuration
└── requirements.txt       # Dependencies
```

