# 🤖 GitHub Actions Setup Guide

> 🔒 **Security Note**: Before setting up secrets, review our [Security Best Practices Guide](SECURITY.md) for comprehensive credential management recommendations.

## Overview

EtymoBot is now configured with two GitHub Actions workflows:

1. **`etymobot.yml`** - Automated posting workflow (runs hourly)
2. **`test.yml`** - Code quality and testing workflow (runs on push/PR)

## 🔐 Required Secrets

You need to add these secrets to your GitHub repository for the bot to work:

### OpenAI API
- **`OPENAI_API_KEY`** - Your OpenAI API key for GPT-4 tweet generation

### Twitter API v2 Credentials
- **`TWITTER_BEARER_TOKEN`** - Twitter API Bearer Token
- **`TWITTER_CONSUMER_KEY`** - Twitter API Consumer Key  
- **`TWITTER_CONSUMER_SECRET`** - Twitter API Consumer Secret
- **`TWITTER_ACCESS_TOKEN`** - Twitter API Access Token
- **`TWITTER_ACCESS_TOKEN_SECRET`** - Twitter API Access Token Secret

## 🛠️ Setting Up Secrets

### 1. Navigate to Repository Settings
1. Go to your repository on GitHub
2. Click **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**

### 2. Add Each Secret
For each secret above:
1. Click **New repository secret**
2. Enter the **Name** (exactly as shown above)
3. Enter the **Value** (your actual API key/token)
4. Click **Add secret**

### 3. Verify Setup
After adding all secrets, you should see:
```
OPENAI_API_KEY                 ••••••••••••••••••••
TWITTER_BEARER_TOKEN           ••••••••••••••••••••
TWITTER_CONSUMER_KEY           ••••••••••••••••••••
TWITTER_CONSUMER_SECRET        ••••••••••••••••••••
TWITTER_ACCESS_TOKEN           ••••••••••••••••••••
TWITTER_ACCESS_TOKEN_SECRET    ••••••••••••••••••••
```

## 🚀 Deployment Workflow

### Automatic Scheduling
- **Runs every hour** via cron: `0 * * * *`
- **Checks optimal posting times** (9 AM, 1 PM, 3 PM EST)
- **Posts only during peak hours** to maximize engagement
- **Automatically builds cache** if database is empty/small

### Manual Triggers
You can manually trigger the workflow:
1. Go to **Actions** tab in your repository
2. Click **EtymoBot Posting** workflow
3. Click **Run workflow** button
4. Select branch and click **Run workflow**

## 📊 Monitoring

### Workflow Status
- **Actions tab** shows all workflow runs and their status
- **Green checkmark** = successful run
- **Red X** = failed run (check logs for details)

### Database Updates
- Each successful post commits `etymobot.sqlite` to the repository
- This preserves the etymology cache and posted pairs history
- Commit message: "Update EtymoBot state [skip ci]"

## 🔧 Advanced Configuration

### Posting Schedule
To modify posting times, edit `src/etymobot/config.py`:
```python
optimal_posting_hours_est: List[int] = field(default_factory=lambda: [9, 13, 15])
```

### Cache Size
To adjust etymology cache size, edit `.github/workflows/etymobot.yml`:
```yaml
python -m etymobot.cli --build-cache --sample-size 300  # Increase number
```

### Workflow Frequency
To change how often it checks for posting opportunities:
```yaml
schedule:
  - cron: '0 */2 * * *'  # Every 2 hours instead of every hour
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Workflow Fails with "Missing Secrets"
**Solution**: Verify all 6 secrets are added with exact names shown above

#### 2. "Invalid API Key" Errors
**Solution**: Check that API keys are valid and have proper permissions

#### 3. Database Permission Errors
**Solution**: Ensure repository has Actions permission to write to `main` branch

#### 4. Cache Build Timeouts
**Solution**: Reduce `--sample-size` in the workflow (e.g., from 300 to 100)

### Debugging Steps

1. **Check workflow logs**:
   - Go to Actions tab → Click failed workflow → View error logs

2. **Test locally**:
   ```bash
   # Test with same environment variables
   export OPENAI_API_KEY="your-key"
   export TWITTER_BEARER_TOKEN="your-token"
   # ... other variables
   
   python -m etymobot.cli --mode scheduled
   ```

3. **Validate secrets**:
   ```bash
   python -m etymobot.cli --validate
   ```

## 📈 Expected Behavior

### First Run
1. **Builds etymology cache** (~5-10 minutes)
2. **Creates database file** (`etymobot.sqlite`)
3. **Checks posting time** - may skip if not optimal hour
4. **Commits database** to repository

### Subsequent Runs
1. **Checks cache size** - rebuilds if too small
2. **Evaluates posting time** - posts only during peak hours
3. **Finds best word pair** from etymology cache
4. **Generates engaging tweet** using AI
5. **Posts to Twitter** and records in database
6. **Commits updated database**

### Posting Pattern
- **3 posts per day maximum** (9 AM, 1 PM, 3 PM EST)
- **Never duplicates** previously posted word pairs
- **Avoids problematic words** that failed etymology lookup
- **Maintains posting quality** through semantic analysis

## 🎯 Success Metrics

A healthy deployment should show:
- ✅ **Green workflow runs** every hour
- ✅ **Regular database commits** after successful posts
- ✅ **Growing etymology cache** over time
- ✅ **Engaging tweets** posted during peak hours
- ✅ **No repeated word pairs**

## 📞 Support

If you encounter issues:
1. Check the [troubleshooting section](#troubleshooting) above
2. Review workflow logs in the Actions tab
3. Test locally with the same environment variables
4. Open an issue with error logs and configuration details 