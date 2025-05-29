# EtymoBot - Pure Generative AI Etymology Twitter Bot

🤖 **A Twitter bot that generates fascinating etymological connections using pure AI + web search verification**

EtymoBot discovers surprising etymological connections between English words using OpenAI's GPT-4 and verifies them through web search. No corpus required - pure AI creativity with factual verification.

## 🎯 What It Does

- **AI Generation**: Uses GPT-4 to generate surprising word pairs that share etymological roots
- **Web Verification**: Searches the web to verify etymological claims before posting
- **Literary Tweets**: Crafts poetic tweets in the style of Lydia Davis, Tolkien, and Nabokov
- **Quality Control**: Rejects false, obvious, or uninteresting etymologies

## 📱 Example Tweets

> "muscle and mussel both spring from *musculus* (little mouse). One flexes beneath skin, the other clings to rocks—both shaped like tiny rodents in hiding."

> "salary meets salad through *sal* (salt). Roman soldiers earned their salt; we season our greens with it—currency and cuisine, both preserved by ancient crystals."

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/thomivy/etymological.git
   cd etymological
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export OPENAI_API_KEY="your_openai_api_key"
   export TWITTER_CONSUMER_KEY="your_key"
   export TWITTER_CONSUMER_SECRET="your_secret"
   export TWITTER_ACCESS_TOKEN="your_token"
   export TWITTER_ACCESS_TOKEN_SECRET="your_token_secret"
   ```

4. **Run the bot**
   ```bash
   # Dry run (generate tweet but don't post)
   python scripts/post.py --dry-run --verbose
   
   # Live posting
   python scripts/post.py --verbose
   ```

## 🛠️ How It Works

### 1. AI Generation
- GPT-4 generates surprising but genuine word pairs that share etymological roots
- Focuses on semantic drift and non-obvious connections
- Uses creative prompting to ensure interesting discoveries

### 2. Web Verification
- Searches DuckDuckGo for etymological evidence about both words
- AI analyzes the search results to determine confidence
- Only posts etymologies with high confidence (≥0.8)

### 3. Tweet Crafting
- Uses a specialized "EtymoWriter" prompt for literary style
- Creates compressed, poetic tweets showing semantic evolution
- Includes safeguards against false or boring etymologies

## ⚙️ Configuration

The bot is configured via environment variables:

### Required
- `OPENAI_API_KEY`: OpenAI API key for GPT-4 access
- `TWITTER_*`: Twitter API credentials for posting

### Optional
- `--dry-run`: Generate tweets without posting
- `--verbose`: Enable detailed logging

## 🤖 Automation

The bot runs automatically via GitHub Actions:
- **Schedule**: 3 times daily at optimal engagement hours
- **Manual**: Can be triggered manually with optional dry-run mode
- **Pure AI**: No corpus management or data preparation required

## 🎨 Features

- **Zero Setup**: No corpus to download or manage
- **Real-time**: Generates fresh etymologies on demand
- **Quality Control**: Multi-layer verification prevents false etymologies
- **Literary Style**: Poetic, compressed tweet format
- **Web-verified**: Uses real web search for fact-checking

## 📊 Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   GPT-4     │───▶│ Web Search   │───▶│   Tweet     │
│ Generation  │    │ Verification │    │  Posting    │
└─────────────┘    └──────────────┘    └─────────────┘
      ▲                     ▲                  ▲
      │                     │                  │
   AI Prompts         DuckDuckGo API     Twitter API
```

## 🔧 Development

The bot consists of:
- `scripts/post.py`: Main posting script with pure generative approach
- `.github/workflows/post-tweets.yml`: GitHub Actions automation
- Clean, focused codebase with no legacy RAG components

## 📈 Why Pure Generative?

- **Unlimited Content**: AI can generate infinite unique etymologies
- **No Maintenance**: No corpus to update or manage
- **Better Quality**: AI reasoning + web verification catches more errors
- **Real-time Facts**: Always uses current web information
- **Surprise Factor**: AI discovers connections humans might miss

## 🌟 Contributing

This is a pure generative AI project focused on etymology discovery. Contributions welcome for:
- Improved prompting strategies
- Better web search integration
- Enhanced fact-checking methods
- Tweet style refinements

## 📄 License

MIT License - See LICENSE file for details.

---

🐦 **Follow [@KnowEtymology](https://twitter.com/KnowEtymology)** for daily etymological discoveries!
