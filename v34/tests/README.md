# Test Files

**Note:** Some of these test files may not work with the current version of the codebase. They were created during earlier development iterations and may require updates to function properly.

## Test Files

- `test_chat_endpoint.py` - Tests for the chat endpoint
- `test_connection.py` - Connection testing utilities
- `test_connectivity.py` - Service connectivity checks
- `test_megaprompt.py` - Megaprompt strategy testing
- `test_request.py` - Request handling tests
- `test_tail_mode.py` - KV cache tail mode tests
- `test_tail_mode_delayed.py` - Delayed tail mode tests
- `test_vision_state.py` - Vision state management tests

## Demo/Utility Scripts

- `classifier.py` - Standalone GLiClass classifier demo script
- `kv_cache_test.py` - KV cache performance testing utility

## Running Tests

Before running tests, ensure:
1. Virtual environment is activated: `source ~/timmy-backend/.venv/bin/activate`
2. All services are running (Ollama, PostgreSQL, etc.)
3. Configuration in `config.py` is correct for your environment

Some tests may require updates to work with the current codebase version.

