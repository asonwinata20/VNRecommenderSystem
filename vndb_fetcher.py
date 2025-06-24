import httpx
import asyncio
import random
from typing import Optional, Dict, Any, List
import json

class VNDBFetcher:
    """A class to fetch Safe-for-Work Visual Novels from VNDB API"""
    
    def __init__(self):
        self.api_url = "https://api.vndb.org/kana/vn"
        
        # NSFW keywords that indicate adult content
        self.nsfw_keywords = [
            "sex", "erotic", "hentai", "nukige", "18+", 
            "adult only", "explicit", "pornographic", "nudity"
        ]
        
        # Safe keywords that should NOT be flagged as NSFW
        self.safe_keywords = [
            "no sexual content", "adult protagonist", "adult heroine", 
            "mature protagonist", "mature heroine", "adult romance", 
            "mature themes", "mature content"
        ]
        
        # Explicit NSFW tags for simple filtering
        self.explicit_nsfw = ["hentai", "nukige", "18+", "erotic", "pornographic"]

    def is_content_safe(self, vn: Dict[str, Any], strict: bool = True) -> tuple[bool, str]:
        """
        Check if VN content is safe for work
        Returns: (is_safe, reason_if_not_safe)
        """
        tags = vn.get("tags", [])
        tag_names = [tag.get("name", "").lower() for tag in tags]
        description = vn.get("description", "").lower()
        
        if strict:
            # First check if tag is explicitly safe (like "no sexual content")
            for tag_name in tag_names:
                # Skip tags that are explicitly marking content as safe
                if any(safe_tag in tag_name for safe_tag in self.safe_keywords):
                    continue
                
                # Now check for NSFW keywords in remaining tags
                for nsfw_keyword in self.nsfw_keywords:
                    if nsfw_keyword in tag_name:
                        return False, f"NSFW tag: '{tag_name}' contains '{nsfw_keyword}'"
            
            # Check description - but be more careful about context
            # Only flag if it's clearly describing NSFW content, not the absence of it
            explicit_desc_patterns = ["contains sexual", "features erotic", "includes adult content", "hentai game"]
            for pattern in explicit_desc_patterns:
                if pattern in description:
                    return False, f"NSFW description contains '{pattern}'"
                    
        else:
            # Simple filtering - only exclude obviously explicit content
            # Ignore safe tags like "no sexual content"
            for tag_name in tag_names:
                # Skip safe tags
                if any(safe_tag in tag_name for safe_tag in self.safe_keywords):
                    continue
                    
                # Check for explicit content
                if any(explicit in tag_name for explicit in self.explicit_nsfw):
                    return False, "Contains explicit content tags"
        
        return True, ""

    def format_vn_info(self, vn: Dict[str, Any]) -> Dict[str, Any]:
        """Format VN information for display"""
        formatted = {
            'title': vn.get('title', 'Unknown'),
            'id': vn.get('id', 'Unknown'),
            'rating': vn.get('rating', 0) / 10,
            'votes': vn.get('votecount', 0),
            'released': vn.get('released', 'Unknown'),
            'languages': vn.get('languages', []),
            'description': vn.get('description', 'No description available'),
            'image_url': None,
            'tags': []
        }
        
        # Handle image
        image_info = vn.get("image")
        if image_info and isinstance(image_info, dict) and image_info.get("url"):
            formatted['image_url'] = image_info['url']
        
        # Handle tags
        tags = vn.get("tags", [])
        if tags:
            formatted['tags'] = [tag.get("name", "Unknown") for tag in tags[:15]]
        
        return formatted

    async def fetch_random_vn(self, max_attempts: int = 100, strict_filtering: bool = True, 
                             min_rating: int = 60, max_id: int = 1000, min_votes: int = 100) -> Optional[Dict[str, Any]]:
        """
        Fetch a random SFW Visual Novel
        
        Args:
            max_attempts: Maximum number of attempts to find a VN
            strict_filtering: Whether to use strict NSFW filtering
            min_rating: Minimum rating threshold (0-100)
            max_id: Maximum VN ID to search (affects range of VNs)
            min_votes: Minimum number of user votes required
        """
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_attempts):
                try:
                    vid = random.randint(1, max_id)
                    vn_id = f"v{vid}"

                    payload = {
                        "filters": ["and", 
                            ["id", "=", vn_id],
                            ["lang", "=", "en"],
                            ["rating", ">=", min_rating],
                            ["votecount", ">=", min_votes]
                        ],
                        "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                        "results": 1
                    }

                    response = await client.post(self.api_url, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("results"):
                            vn = data["results"][0]
                            
                            is_safe, reason = self.is_content_safe(vn, strict_filtering)
                            
                            if is_safe:
                                return self.format_vn_info(vn)
                    
                    elif response.status_code == 429:
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    await asyncio.sleep(0.1)

        return None

    async def fetch_multiple_vns(self, count: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Fetch multiple SFW Visual Novels"""
        results = []
        
        for i in range(count):
            vn = await self.fetch_random_vn(**kwargs)
            if vn:
                results.append(vn)
        
        return results

    async def search_vns_by_title(self, title: str, max_results: int = 10, min_votes: int = 50, debug: bool = False) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Search VNs by title with enhanced debugging
        Returns: (results_list, debug_info)
        """
        debug_info = {
            'query': title,
            'max_results': max_results,
            'min_votes': min_votes,
            'api_url': self.api_url,
            'status_code': None,
            'response_text': None,
            'error': None,
            'payload': None,
            'total_found': 0,
            'safe_found': 0,
            'filtered_out': 0
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Try multiple search strategies
                search_strategies = [
                    # Strategy 1: Exact title match with fuzzy search
                    {
                        "filters": ["and",
                            ["title", "~", title],
                            ["lang", "=", "en"],
                            ["votecount", ">=", min_votes]
                        ],
                        "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                        "results": max_results,
                        "sort": "rating",
                        "reverse": True
                    },
                    # Strategy 2: More lenient search if first fails
                    {
                        "filters": ["and",
                            ["title", "~", title],
                            ["lang", "=", "en"]
                        ],
                        "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                        "results": max_results,
                        "sort": "votecount",
                        "reverse": True
                    },
                    # Strategy 3: Even more lenient - remove language filter
                    {
                        "filters": ["title", "~", title],
                        "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                        "results": max_results,
                        "sort": "rating",
                        "reverse": True
                    }
                ]
                
                for i, payload in enumerate(search_strategies):
                    debug_info['payload'] = payload
                    debug_info['strategy'] = i + 1
                    
                    response = await client.post(self.api_url, json=payload)
                    debug_info['status_code'] = response.status_code
                    
                    if debug:
                        debug_info['response_text'] = response.text[:500]  # First 500 chars
                    
                    if response.status_code == 200:
                        data = response.json()
                        debug_info['raw_response'] = data if debug else None
                        
                        if data.get("results"):
                            debug_info['total_found'] = len(data["results"])
                            results = []
                            
                            for vn in data["results"]:
                                is_safe, reason = self.is_content_safe(vn, strict=False)
                                if is_safe:
                                    results.append(self.format_vn_info(vn))
                                    debug_info['safe_found'] += 1
                                else:
                                    debug_info['filtered_out'] += 1
                                    if debug:
                                        debug_info.setdefault('filtered_reasons', []).append(reason)
                            
                            if results:  # If we found results, return them
                                return results, debug_info
                        else:
                            debug_info['message'] = f"Strategy {i+1}: No results found"
                    
                    elif response.status_code == 429:
                        debug_info['error'] = "Rate limited"
                        await asyncio.sleep(1)
                    else:
                        debug_info['error'] = f"HTTP {response.status_code}: {response.text}"
                
                # If no strategy worked
                debug_info['final_message'] = "All search strategies failed"
                return [], debug_info
                        
            except Exception as e:
                debug_info['error'] = f"Exception: {str(e)}"
                return [], debug_info

    # Legacy method for backward compatibility (no debug info)
    async def search_vns_by_title_simple(self, title: str, max_results: int = 10, min_votes: int = 50) -> List[Dict[str, Any]]:
        """Simple search method for backward compatibility"""
        results, _ = await self.search_vns_by_title(title, max_results, min_votes, debug=False)
        return results