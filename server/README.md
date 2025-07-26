# Gandalf Server

High-performance Python MCP server implementation with advanced optimizations.

## Architecture

```
src/
├── main.py           # Server entry point with health monitoring
├── config/           # Configuration and validation with schema enforcement
├── core/             # Business logic with performance optimizations
│   ├── server.py             # Enhanced MCP server with connection pooling
│   ├── project_filtering.py  # Optimized pathlib-based file discovery
│   ├── conversation_analysis.py # Memory-aware conversation processing
│   └── ...
├── tool_calls/       # MCP tool implementations
└── utils/            # Advanced caching and performance utilities
    ├── database_pool.py      # SQLite connection pooling
    ├── memory_cache.py       # LRU cache with memory management
    ├── common.py             # Streamlined logging utilities
    └── README.md             # Comprehensive utils documentation
```

## Development

```bash
# Setup with optimizations
pip install -e .

# Comprehensive testing
pytest --cov=src --cov-report=html
./gandalf test
./gandalf lembas

# Performance profiling
python -m cProfile -o profile.stats src/main.py

# Code quality
ruff check src/ && ruff format src/
mypy src/
```

## Performance Monitoring

```bash
# Monitor memory usage
python -m memory_profiler src/main.py

# Database performance
sqlite3 ~/.gandalf/cache/analysis.db ".schema"

# Cache statistics
python -c "from src.utils.memory_cache import get_keyword_cache; print(get_keyword_cache().get_stats())"
```
