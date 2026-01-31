"""
Reddit integration for dynamic topic generation
Fetches trending posts from Reddit to create conversation starters
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

# Reddit API doesn't require authentication for public data when using a user agent
REDDIT_USER_AGENT = "LanguageLearningTutor/1.0 (Language learning chatbot)"
REDDIT_BASE_URL = "https://www.reddit.com"


async def fetch_reddit_top_posts(
    subreddit: str = "popular",
    limit: int = 20,
    time_filter: str = "day"
) -> List[Dict]:
    """
    Fetch top posts from a given subreddit
    
    Args:
        subreddit: Subreddit name (without r/) - default "popular"
        limit: Number of posts to fetch (max 100) - default 20
        time_filter: Time period for sorting: "hour", "day", "week", "month", "year", "all" - default "day"
    
    Returns:
        List of post dictionaries with keys:
        - title: Post title
        - subreddit: Subreddit name
        - score: Upvote score
        - url: Post URL
        - created_utc: Timestamp
        - num_comments: Number of comments
        - selftext: Post body text (if text post)
        - domain: Domain (if link post)
    
    Raises:
        Exception: If the Reddit API request fails
    """
    
    # Validate inputs
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1
    
    # Construct Reddit API URL
    # Reddit's JSON API endpoint: /r/{subreddit}/top.json
    url = f"{REDDIT_BASE_URL}/r/{subreddit}/top.json"
    
    params = {
        "limit": limit,
        "t": time_filter  # time filter parameter
    }
    
    headers = {
        "User-Agent": REDDIT_USER_AGENT
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise Exception(f"Reddit API returned status {response.status}")
                
                data = await response.json()
                
                # Extract posts from the response
                posts = []
                for item in data.get("data", {}).get("children", []):
                    post_data = item.get("data", {})
                    posts.append({
                        "title": post_data.get("title", ""),
                        "subreddit": post_data.get("subreddit", ""),
                        "score": post_data.get("score", 0),
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "created_utc": post_data.get("created_utc", 0),
                        "num_comments": post_data.get("num_comments", 0),
                        "selftext": post_data.get("selftext", "")[:500],  # Truncate to 500 chars
                        "domain": post_data.get("domain", ""),
                        "is_self": post_data.get("is_self", False),  # True if text post
                    })
                
                return posts
    
    except asyncio.TimeoutError:
        raise Exception("Reddit API request timed out")
    except aiohttp.ClientError as e:
        raise Exception(f"Failed to connect to Reddit: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching Reddit posts: {str(e)}")


async def fetch_multiple_subreddits(
    subreddits: List[str],
    limit_per_subreddit: int = 5,
    time_filter: str = "day"
) -> List[Dict]:
    """
    Fetch top posts from multiple subreddits concurrently
    
    Args:
        subreddits: List of subreddit names
        limit_per_subreddit: Number of posts per subreddit
        time_filter: Time period for sorting
    
    Returns:
        Combined list of posts from all subreddits
    """
    
    tasks = [
        fetch_reddit_top_posts(subreddit, limit_per_subreddit, time_filter)
        for subreddit in subreddits
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_posts = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Error fetching from subreddit: {result}")
            continue
        all_posts.extend(result)
    
    return all_posts


# Testing/Demo
if __name__ == "__main__":
    async def test():
        print("Fetching top 20 posts from r/popular...")
        posts = await fetch_reddit_top_posts("popular", limit=20, time_filter="day")
        
        print(f"\nFetched {len(posts)} posts:\n")
        for i, post in enumerate(posts, 1):
            print(f"{i}. {post['title']}")
            print(f"   Subreddit: r/{post['subreddit']} | Score: {post['score']} | Comments: {post['num_comments']}")
            print()
    
    asyncio.run(test())
