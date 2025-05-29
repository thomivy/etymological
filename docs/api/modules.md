# EtymoBot API Reference

## Module Overview

The EtymoBot package is organized into several focused modules:

### Core Modules

- **[`etymobot.bot`](bot.md)** - Main orchestrator class
- **[`etymobot.models`](models.md)** - Data models and structures
- **[`etymobot.config`](config.md)** - Configuration management

### Service Modules

- **[`etymobot.database`](database.md)** - Database operations
- **[`etymobot.etymology`](etymology.md)** - Etymology discovery
- **[`etymobot.services`](services.md)** - External API services

### Utilities

- **[`etymobot.cli`](cli.md)** - Command-line interface

## Quick Start

```python
from etymobot import EtymoBot

# Using environment variables
bot = EtymoBot()

# Using custom config
from etymobot.config import Config
config = Config.from_env()
config.db_path = "custom.sqlite"
bot = EtymoBot(config)

# Run single cycle
success = bot.run_single_cycle()

# Get statistics
stats = bot.get_stats()
print(f"Cache size: {stats['cache_size']}")
```

## Package Structure

```
src/etymobot/
├── __init__.py          # Package exports
├── bot.py              # Main EtymoBot class
├── models.py           # Data models (WordPair)
├── config.py           # Configuration management
├── database.py         # Database operations
├── etymology.py        # Etymology discovery
├── services.py         # External APIs (Twitter, OpenAI)
└── cli.py             # Command-line interface
```

## Type Hints

All modules include comprehensive type hints for better IDE support and code clarity:

```python
from typing import Optional, List
from etymobot.models import WordPair

def find_pairs(root: str) -> List[WordPair]:
    """Find word pairs for a given root."""
    ...
``` 