# EtymoBot Quick Start - Pure Generative AI

🚀 **Get your etymological Twitter bot running in 5 minutes using pure AI generation!**

## Prerequisites

- GitHub account with Actions enabled
- Twitter Developer account
- OpenAI API key
- Basic command line knowledge

## 1. Setup Repository

### Fork the Repository
```bash
git clone https://github.com/thomivy/etymological.git
cd etymological
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Get API Keys

### Twitter API Keys
1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a new app
3. Generate API keys and tokens
4. Note down:
   - Consumer Key
   - Consumer Secret  
   - Access Token
   - Access Token Secret

### OpenAI API Key
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create API key
3. Ensure you have GPT-4 access

## 3. Configure Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add these repository secrets:

```
OPENAI_API_KEY=your_openai_api_key_here
TWITTER_CONSUMER_KEY=your_twitter_consumer_key
TWITTER_CONSUMER_SECRET=your_twitter_consumer_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
```

## 4. Test Locally (Optional)

### Set Environment Variables
```bash
export OPENAI_API_KEY="your_openai_api_key"
export TWITTER_CONSUMER_KEY="your_key"
export TWITTER_CONSUMER_SECRET="your_secret"
export TWITTER_ACCESS_TOKEN="your_token"
export TWITTER_ACCESS_TOKEN_SECRET="your_token_secret"
```

### Run Dry Test
```bash
# Generate a tweet without posting
python scripts/post.py --dry-run --verbose
```

### Run Live Test  
```bash
# Generate and post a real tweet
python scripts/post.py --verbose
```

## 5. Enable Automation

### GitHub Actions
The bot automatically runs **3 times daily** at optimal engagement hours:
- 13:00 UTC (9:00 AM EST)
- 17:00 UTC (1:00 PM EST)  
- 19:00 UTC (3:00 PM EST)

### Manual Trigger
You can also trigger manually:
1. Go to **Actions** tab in your repository
2. Select "Daily Tweet Posting - Pure Generative AI"
3. Click "Run workflow"
4. Optionally enable "dry run" mode

## 6. How It Works

### Pure Generative Process
1. **AI Generation**: GPT-4 creates surprising word pairs with shared roots
2. **Web Verification**: Searches web for etymological evidence
3. **Quality Check**: AI analyzes evidence for accuracy and interest
4. **Tweet Crafting**: Creates poetic, literary-style tweets
5. **Publishing**: Posts to Twitter if all checks pass

### No Corpus Required
- **Zero setup**: No data files to download or process
- **Real-time**: Fresh etymologies generated on demand  
- **Self-contained**: Everything handled by AI + web search

## Example Output

```
🤖 Using PURE GENERATIVE approach - AI + Web Search verification
✅ OpenAI API key found (length: 164 characters)
🤖 Pure generative approach - using OpenAI API with key ending in: ...abc
🤖 Generating verified etymology using AI + web search...
Attempt 1: Testing muscle + mussel -> *musculus*
✅ VERIFIED: muscle + mussel (confidence: 0.92)
✅ Generated: muscle + mussel -> *musculus*
📊 Confidence: 0.92
📄 Evidence: Search '"muscle" etymology origin': Both from Latin musculus meaning little mouse...
📱 Generated tweet: muscle and mussel both spring from *musculus* (little mouse). One flexes beneath skin, the other clings to rocks—both shaped like tiny rodents in hiding.
✅ Tweet posting completed successfully!
```

## Troubleshooting

### Common Issues

**"OpenAI API key not found"**
- Check your environment variables or GitHub secrets
- Ensure the key starts with `sk-`

**"Twitter credentials missing"**  
- Verify all 4 Twitter secrets are set correctly
- Check your Twitter app has write permissions

**"Failed to generate verified etymology"**
- This is normal - the bot is being selective
- It will try up to 10 times to find a high-quality etymology
- If repeated failures, check OpenAI API quota/billing

**"Etymology was rejected as uninteresting"**
- The AI detected the etymology wasn't surprising enough
- This is the quality control working correctly

### Debug Mode
```bash
python scripts/post.py --dry-run --verbose
```

This shows the full generation process without posting.

## Customization

### Posting Schedule
Edit `.github/workflows/post-tweets.yml` to change the cron schedule:
```yaml
schedule:
  - cron: '0 13,17,19 * * *'  # Current: 3x daily
```

### Confidence Threshold
In `scripts/post.py`, modify the confidence requirement:
```python
if verification and verification.confidence >= 0.8:  # Lower = more posts
```

### Tweet Style
The bot uses a specialized "EtymoWriter" prompt. You can modify this in the `generate_tweet` method to adjust the literary style.

## Next Steps

Once running successfully:
- Monitor your bot's Twitter account
- Check GitHub Actions logs for any issues
- The bot will automatically post interesting etymologies 3x daily
- No maintenance required - everything is generated fresh each time!

---

🎉 **Congratulations!** Your pure generative AI etymology bot is now live and discovering fascinating word connections!

