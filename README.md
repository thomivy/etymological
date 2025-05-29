# EtymoBot 🔤

An automated etymology discovery and Twitter posting bot that finds semantically divergent word pairs sharing ancient roots, then crafts engaging tweets about their etymological connections.

## 🌟 **Key Features**

- **🌳 Root-based Discovery**: Processes Wiktionary dumps to extract authentic etymological roots and word relationships
- **📊 Linguistic Accuracy**: Uses real PIE (Proto-Indo-European) roots and scholarly etymology data
- **⏰ Smart Scheduling**: Posts 3 times daily during peak engagement hours (9 AM, 1 PM, 3 PM EST)
- **🗄️ Simple State Management**: Tracks posted pairs using flat CSV files (no database required)
- **🚀 GitHub-Native Pipeline**: Fully automated via GitHub Actions - no external infrastructure needed
- **📈 Self-Improving**: Learns from posting history and avoids repetition
- **🎭 Template Variety**: Multiple tweet formats for engaging, educational content
- **🔄 Zero Dependencies**: ML models enahnce output but are not required, and neither are external databases. 

## Requirements

- **GitHub repository** with Actions enabled
- **Twitter API v2 credentials** for posting
- **2.2GB disk space** for Wiktionary dump processing (handled automatically by GitHub Actions). This can be done locally and the post-processed file uploaded.

## Example Tweets

**Root Connection**
> gustable/gusty: "gustus" splits into gustable vs gusty.

**Divergent Meanings**  
> crimp/camp: "kampós" diverged into crimp vs camp.

**Ancient Origins**
> weary/worse: "wer" branches into weary vs worse.

**Semantic Evolution**
> carriage/cargo: "carrus" evolved into carriage vs cargo.

**Historical Splits**
> gear/yard: "gard" separated into gear vs yard.

## Setup

### 1. Fork Repository

Fork this repository to your GitHub account.

### 2. Configure Secrets

In your repository settings, add these secrets (Settings → Secrets and variables → Actions):

```bash
# Twitter API v2 credentials
TWITTER_CONSUMER_KEY="your-consumer-key"
TWITTER_CONSUMER_SECRET="your-consumer-secret"
TWITTER_ACCESS_TOKEN="your-access-token"
TWITTER_ACCESS_TOKEN_SECRET="your-access-token-secret"
```

### 3. Enable GitHub Actions

Go to the Actions tab and enable workflows.

### 4. First Run

Trigger the "Weekly Corpus Refresh" workflow manually to build initial data, then enable automatic posting.

## Usage

### Automated Operation

Once configured, the bot runs automatically:
- **Weekly**: Refreshes etymology corpus from latest Wiktionary dumps
- **3x Daily**: Posts tweets at optimal engagement times (13:00, 17:00, 19:00 UTC)

### Manual Testing

Test locally with the scripts:

```bash
# Install dependencies
pip install tweepy

# Download Wiktionary dump
curl -o data/wiktionary-data.jsonl.gz https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz

# Build etymology corpus
python scripts/build_roots.py

# Test tweet generation (dry run)
python scripts/post.py --dry-run
```

## Deployment

### GitHub Actions (Recommended)

The bot includes pre-configured workflows:

- **`roots-refresh.yml`**: Weekly corpus updates from Wiktionary dumps
- **`post-tweets.yml`**: 3x daily posting at optimal times
- **Built-in concurrency controls** and error handling
- **Automatic commit tracking** of posted pairs

### Manual Scheduling

For custom deployment, run the scripts directly:

```bash
# Weekly corpus refresh
python scripts/build_roots.py

# Daily posting  
python scripts/post.py
```

## Architecture

### Data Pipeline

1. **Corpus Building** (`scripts/build_roots.py`):
   - Downloads Wiktionary JSONL dumps (2.2GB)
   - Extracts PIE roots and word relationships
   - Outputs compressed `data/roots.json.gz`

2. **Tweet Generation** (`scripts/post.py`):
   - Loads etymology corpus and posting history
   - Selects unposted word pairs
   - Generates tweets using curated templates
   - Updates `data/posted.csv` history

### File Structure

```
etymological/
├── scripts/
│   ├── build_roots.py     # Corpus builder from Wiktionary dumps  
│   └── post.py           # Tweet generator and poster
├── data/
│   ├── roots.json.gz     # Etymology corpus (3K+ roots, 10K+ words)
│   └── posted.csv        # Posted pairs history
└── .github/workflows/
    ├── roots-refresh.yml # Weekly corpus refresh
    └── post-tweets.yml   # 3x daily posting
```

### Current Statistics

- **3,099 etymological roots** from comprehensive Wiktionary analysis
- **10,223 word relationships** across diverse vocabulary
- **Quality-focused extraction** using PIE root patterns and scholarly sources
- **Authentic connections** verified against etymological databases

## Configuration

### Posting Schedule

Default posting times (UTC):
- 13:00 UTC (9:00 AM EST)
- 17:00 UTC (1:00 PM EST)  
- 19:00 UTC (3:00 PM EST)

Modify the cron schedule in `.github/workflows/post-tweets.yml` to customize.

### Etymology Sources

The bot processes official Wiktionary dumps containing:
- Proto-Indo-European reconstructions
- Historical language etymologies  
- Scholarly root derivations
- Cross-referenced word families

### Template Variety

Multiple tweet formats ensure engaging content:
- Simple root connections
- Semantic divergence explanations
- Historical evolution narratives
- Direct root attributions

## License

TBD
