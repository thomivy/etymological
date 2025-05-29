# EtymoBot 🔤

An automated etymology discovery and Twitter posting bot that finds semantically divergent word pairs sharing ancient roots, then crafts engaging tweets about their etymological connections.

## 🌟 **Key Features**

- **🔍 Intelligent Etymology Discovery**: Automatically finds semantically divergent word pairs sharing ancient roots
- **🎭 Stylistic Variation**: Rotates among 5 different tweet templates to avoid mechanical repetition:
  - **Statement + Twist**: Declarative opening with surprising reflection
  - **Question Hook**: Engaging question that draws readers in  
  - **Mini Anecdote**: Historical context with poetic contrast
  - **Fragment & Aside**: Modern style with parallel metaphors
  - **One-Liner Aphorism**: Punchy, quotable distillations
- **🧠 AI-Powered Content**: Uses GPT-4 for engaging, educational tweet generation
- **📊 Semantic Analysis**: Employs sentence transformers to find truly divergent word meanings
- **⏰ Smart Scheduling**: Posts only during peak engagement hours (9 AM, 1 PM, 3 PM EST)
- **🗄️ State Management**: Tracks posted pairs and problematic words to avoid repetition
- **🚀 Multiple Deployment Options**: GitHub Actions, Docker, or local execution
- **📈 Self-Improving**: Learns from failures and skips problematic words

## Features

- **Root-first Discovery**: Scrapes etymologies to build a cache of root-word mappings
- **Semantic Divergence Scoring**: Uses sentence transformers to find the most contrasting word pairs
- **Optimal Scheduling**: Posts 3 times daily during peak engagement hours (9 AM, 1 PM, 3 PM EST)
- **Robust Error Handling**: Gracefully skips problematic words and recovers from API failures
- **Modern APIs**: Uses Twitter API v2 and OpenAI's latest client
- **Persistent State**: SQLite database tracks posted pairs and failed attempts
- **Deployment Flexible**: Works with GitHub Actions, cron, Docker, or manual runs

## Example Tweets

**Statement + Twist** 
> Gregarious born of Latin greg ("herd"). Social butterflies and outcasts both carry the memory of the flock. Some seek it; others flee it.

**Question Hook**
> Ever wondered why sporadic and diaspora both echo Greek speirein? One scatters seeds randomly, the other scatters people by force. Both leave trails in foreign soil.

**Mini Anecdote**  
> In ancient times, *vir* meant "man"—the seed of virtue and virtual. One grew into moral strength, the other into mere appearance. Reality split from its shadow.

**Fragment & Aside**
> Malicious & malaise—rooted in Latin *mal* ("bad"). One strikes with intent, the other settles like fog (that heavy, creeping kind). Which wounds deeper?

**One-Liner Aphorism**
> Adamant/adapt: *adamas* ("unconquerable"). The diamond that won't bend birthed the skill that bends everything else.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file or set these environment variables:

```bash
# OpenAI API
OPENAI_API_KEY="your-openai-api-key"

# Twitter API v2 credentials
TWITTER_BEARER_TOKEN="your-bearer-token"
TWITTER_CONSUMER_KEY="your-consumer-key"
TWITTER_CONSUMER_SECRET="your-consumer-secret"
TWITTER_ACCESS_TOKEN="your-access-token"
TWITTER_ACCESS_TOKEN_SECRET="your-access-token-secret"
```

### 3. Initial Cache Build

```bash
python etymobot.py --build-cache
```

This will populate the etymology cache with ~1000 word-root mappings. The process takes 10-15 minutes due to rate limiting.

## Usage

### Single Tweet

```bash
python etymobot.py --mode single
```

### Scheduled Mode (Optimal Timing)

```bash
python etymobot.py --mode scheduled
```

Checks if current time is optimal (9 AM, 1 PM, or 3 PM EST) and posts if so.

### Custom Database Location

```bash
python etymobot.py --db /path/to/custom.sqlite
```

## Deployment

### GitHub Actions

Create `.github/workflows/etymobot.yml`:

```yaml
name: EtymoBot Posting

on:
  schedule:
    # Run every hour to check for optimal posting times
    - cron: '0 * * * *'
  workflow_dispatch: # Manual trigger

jobs:
  post-tweet:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Needed to commit database changes
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run EtymoBot
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
        TWITTER_CONSUMER_KEY: ${{ secrets.TWITTER_CONSUMER_KEY }}
        TWITTER_CONSUMER_SECRET: ${{ secrets.TWITTER_CONSUMER_SECRET }}
        TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
        TWITTER_ACCESS_TOKEN_SECRET: ${{ secrets.TWITTER_ACCESS_TOKEN_SECRET }}
      run: python etymobot.py --mode scheduled
    
    - name: Commit database changes
      uses: EndBug/add-and-commit@v9
      with:
        author_name: 'github-actions[bot]'
        author_email: '41998282+github-actions[bot]@users.noreply.github.com'
        message: 'Update EtymoBot state'
        add: 'etymobot.sqlite'
        default_author: github_actions
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY etymobot.py .
COPY etymobot.sqlite .

CMD ["python", "etymobot.py", "--mode", "scheduled"]
```

### Cron Job

```bash
# Run every hour to check for optimal posting times
0 * * * * cd /path/to/etymobot && python etymobot.py --mode scheduled
```

## Configuration

### Posting Schedule

The bot targets 3 daily posts during peak engagement:
- 9:00 AM EST (14:00 UTC)
- 1:00 PM EST (18:00 UTC) 
- 3:00 PM EST (20:00 UTC)

Modify `get_optimal_posting_times()` to customize.

### Word Sources

Default uses `wordfreq` top 10K English words. Override in `build_root_cache()` to use:
- Custom word lists
- Wordnik API
- COCA frequency data

### Root Extraction

Current regex pattern: `(?:from|root)\s+([A-Za-z\-]+)`

Captures roots mentioned as "from Latin root" or "root Sanskrit xyz". Customize in `EtymoBot.__init__()`.

## Database Schema

### `rootmap` - Etymology cache
- `root`: Extracted root (e.g., "greg", "sper")  
- `word`: English word containing this root
- `created_at`: Timestamp when discovered

### `posted` - Posted pairs tracking  
- `word1`, `word2`: Word pair that was tweeted
- `root`: Shared root
- `tweet_id`: Twitter post ID
- `posted_at`: Post timestamp

### `failed_words` - Error tracking
- `word`: Word that failed etymology lookup
- `failure_count`: Number of failures
- `last_failure`: Most recent failure timestamp

## Error Handling

- **Network failures**: Automatic retries with exponential backoff
- **Problematic words**: Tracked and skipped after 3 failures
- **API rate limits**: Built-in rate limiting and wait-on-limit
- **Malformed etymologies**: Gracefully skipped
- **Tweet length**: Automatic retry with shorter prompt

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 🚀 Development Roadmap

### ✅ Completed (Recent Improvements)
- **Comprehensive linting cleanup**: Reduced from 373 to 9 minor violations
- **Dependency updates**: Updated to latest stable versions
- **Enhanced configuration management**: Better validation and timezone handling
- **Robust error handling**: Improved retry logic and failure tracking
- **Professional code structure**: Modular design with comprehensive testing

### 📋 Medium-term Goals (Next 3-6 months)

#### **Integration Tests**
- End-to-end workflow testing with mock APIs
- Database integration testing across different scenarios
- Performance testing for cache building and pair selection
- Error scenario testing (API failures, network issues)

#### **Enhanced Monitoring & Analytics**
- Tweet performance tracking (likes, retweets, engagement)
- Cache effectiveness metrics and optimization
- Etymology source diversity analysis
- Posting time optimization based on engagement data

#### **Performance Optimization**
- Semantic model caching and lazy loading
- Database query optimization with advanced indexing
- Etymology cache compression and cleanup routines
- Memory usage optimization for long-running processes

#### **Advanced Etymology Features**
- Multiple etymology source integration (Wiktionary, OED API)
- Cross-language etymology tracking (Latin, Greek, Sanskrit, etc.)
- Etymology confidence scoring and validation
- Historical period tagging for roots

### 🎯 Long-term Vision (6+ months)

#### **CI/CD Pipeline**
- Automated testing and deployment workflows
- Code quality gates with coverage requirements
- Automated dependency security scanning
- Staging environment for testing new features

#### **Multi-language Support**
- Support for languages beyond English etymology
- Cross-linguistic root relationship discovery
- International posting schedule optimization
- Unicode and special character handling

#### **Advanced Analytics Dashboard**
- Web-based monitoring interface
- Real-time etymology discovery statistics
- Tweet performance analytics and insights
- Cache health and optimization recommendations

#### **Machine Learning Enhancements**
- Custom etymology extraction models
- Intelligent posting time optimization
- Semantic similarity model fine-tuning
- Automated tweet quality assessment

#### **API and Integration**
- RESTful API for etymology discovery
- Webhook support for external integrations
- Plugin architecture for custom etymology sources
- Integration with academic linguistic databases

#### **Community Features**
- User-submitted etymology corrections
- Collaborative etymology validation
- Etymology fact-checking and verification
- Educational content partnerships

### 🔧 Technical Debt & Maintenance

#### **Code Quality**
- Complete type hint coverage with mypy validation
- Comprehensive documentation with Sphinx
- Advanced logging and debugging capabilities
- Code complexity reduction and refactoring

#### **Security & Reliability**
- API key rotation and secure storage
- Rate limiting enhancements
- Backup and disaster recovery procedures
- Security audit and vulnerability scanning

#### **Scalability**
- Microservices architecture exploration
- Cloud deployment optimization
- Database scaling strategies
- Load balancing for high-traffic scenarios

## Getting Involved

We welcome contributions! Here are ways to get involved:

- **🐛 Bug Reports**: Submit issues with detailed reproduction steps
- **💡 Feature Requests**: Propose new functionality with use cases
- **📝 Documentation**: Improve setup guides and API documentation
- **🧪 Testing**: Add test cases and improve coverage
- **🎨 UI/UX**: Design better monitoring and analytics interfaces

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/username/etymobot.git
cd etymobot
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Type checking
python -m mypy src/ --ignore-missing-imports

# Code formatting
python -m black src/ tests/
python -m flake8 src/ --max-line-length=100
```

## License

MIT License - see LICENSE file for details.
