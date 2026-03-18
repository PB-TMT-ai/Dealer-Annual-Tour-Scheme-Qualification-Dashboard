# API Integration Skill

## Error Handling
```python
import httpx

async def fetch_data(endpoint: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}: {endpoint}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request failed: {e}")
        raise
```

## Retry with Backoff
```python
import asyncio

async def fetch_with_retry(fn, retries: int = 3):
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait_time = 2 ** attempt
            logger.warn(f"Retry {attempt + 1}/{retries} in {wait_time}s")
            await asyncio.sleep(wait_time)
```

## Rate Limiting
- Track requests per minute
- Add delays for batch operations
- Respect Retry-After headers

## Don'ts
- NEVER hardcode API keys
- NEVER log sensitive data
- NEVER ignore rate limits
