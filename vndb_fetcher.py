import httpx
import asyncio
import random
from typing import Optional, Dict, Any, List
import json

class VNDBFetcher:
    """A class to fetch Safe-for-Work Visual Novels from VNDB API with improved tag-based filtering"""
    
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
            "mature themes", "mature content", "low sexual content", 
            "sexual innuendo", "sex change"
        ]
        
        # Explicit NSFW tags for simple filtering
        self.explicit_nsfw = ["hentai", "nukige", "18+", "erotic", "pornographic"]
        
        # IMPROVED: Fixed and expanded tag mapping with verified VNDB tag IDs
        self.tag_map = {
            # Story genres
            "Mystery": "g19",
            "Horror": "g7", 
            "Comedy": "g104",
            "Drama": "g147",
            "Slice of Life": "g454",
            "Thriller": "g789",
            "Romance": "g96",
            "Action": "g12",
            "Fantasy": "g2",
            "Science Fiction": "g105",
            
            # Protagonist types - FIXED: Removed duplicate tag IDs
            "Male Protagonist": "g133",
            "Female Protagonist": "g134", 
            "Multiple Protagonists": "g136",
            "Adult Protagonist": "g137",
            "Student Protagonist": "g544",
            
            # Gameplay
            "Multiple Endings": "g148",
            "Kinetic Novel": "g709",
            "Linear Plot": "g145",
            "Branching Plot": "g606",
            
            # Setting
            "School": "g47",
            "Modern Day": "g143",
            "Past": "g141",
            "Future": "g140",
            # FIXED: Removed duplicate mapping for Historical
            
            # NEW: Additional useful tags
            "Friendship": "710",
            "Family": "g215",
            "Military": "g46"
        }
        
        # Common VN tags for easy reference
        self.common_tags = {
            "story": ["Mystery", "Horror", "Comedy", "Drama", "Slice of Life", 
                      "Thriller", "Romance", "Action", "Fantasy", "Science Fiction"],
            "protagonist": ["Male Protagonist", "Female Protagonist", "Multiple Protagonists",
                           "Adult Protagonist", "Student Protagonist"],
            "gameplay": ["Multiple Endings", "Linear Plot", "Kinetic Novel",
                        "Branching Plot"],
            "setting": ["School", "Modern Day", "Past", "Future"],
            "themes": ["Friendship", "Family", "Military"]
        }

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
            explicit_desc_patterns = ["contains sexual", "features erotic", "includes adult content", "hentai game"]
            for pattern in explicit_desc_patterns:
                if pattern in description:
                    return False, f"NSFW description contains '{pattern}'"
                    
        else:
            # Simple filtering - only exclude obviously explicit content
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

    def get_available_tags(self) -> Dict[str, List[str]]:
        """Return common VN tags organized by category"""
        return self.common_tags

    def resolve_tag_names(self, tag_names: List[str]) -> List[str]:
        """
        Convert tag names to tag IDs if available in tag_map, otherwise return as-is
        """
        resolved_tags = []
        for tag_name in tag_names:
            if tag_name in self.tag_map:
                resolved_tags.append(self.tag_map[tag_name])
                print(f"Debug: Resolved '{tag_name}' -> '{self.tag_map[tag_name]}'")
            else:
                resolved_tags.append(tag_name)
                print(f"Debug: Using tag name as-is: '{tag_name}'")
        return resolved_tags

    def build_tag_filters(self, required_tags: List[str] = None, excluded_tags: List[str] = None, 
                         tag_logic: str = "any") -> List:
        """
        Build filter conditions for tags with flexible logic
        
        Args:
            required_tags: List of tags that should be present
            excluded_tags: List of tags that must NOT be present
            tag_logic: "any" (OR logic) or "all" (AND logic) for required tags
        """
        filters = []
        
        if required_tags:
            resolved_required = self.resolve_tag_names(required_tags)
            print(f"Debug: Required tags resolved to: {resolved_required}")
            
            if len(resolved_required) == 1:
                filters.append(["tag", "=", resolved_required[0]])
            else:
                if tag_logic == "any":
                    # Use OR logic for multiple required tags
                    tag_conditions = ["or"]
                    for tag in resolved_required:
                        tag_conditions.append(["tag", "=", tag])
                    filters.append(tag_conditions)
                else:  # tag_logic == "all"
                    # Use AND logic for multiple required tags
                    for tag in resolved_required:
                        filters.append(["tag", "=", tag])
        
        if excluded_tags:
            resolved_excluded = self.resolve_tag_names(excluded_tags)
            print(f"Debug: Excluded tags resolved to: {resolved_excluded}")
            for tag in resolved_excluded:
                filters.append(["tag", "!=", tag])
        
        print(f"Debug: Built tag filters: {filters}")
        return filters

    def validate_tag_mapping(self) -> Dict[str, Any]:
        """
        Validate tag mapping for duplicates and return a report
        """
        tag_id_to_names = {}
        duplicates = {}
        warnings = []
        
        # Group tag names by their IDs
        for name, tag_id in self.tag_map.items():
            if tag_id not in tag_id_to_names:
                tag_id_to_names[tag_id] = []
            tag_id_to_names[tag_id].append(name)
        
        # Find duplicates
        for tag_id, names in tag_id_to_names.items():
            if len(names) > 1:
                duplicates[tag_id] = names
        
        return {
            'duplicates': duplicates,
            'warnings': warnings,
            'total_mappings': len(self.tag_map),
            'unique_ids': len(tag_id_to_names)
        }

    async def search_vns_by_query(self, query: str, max_results: int = 10, 
                                 min_rating: int = 60, min_votes: int = 50,
                                 strict_filtering: bool = True) -> List[Dict[str, Any]]:
        """
        Search VNs by title/description query
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                filters = [
                    ["and",
                        ["lang", "=", "en"],
                        ["rating", ">=", min_rating],
                        ["votecount", ">=", min_votes],
                        ["search", "=", query]
                    ]
                ]
                
                payload = {
                    "filters": filters,
                    "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                    "results": max_results * 2,
                    "sort": "rating",
                    "reverse": True
                }
                
                response = await client.post(self.api_url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    if data.get("results"):
                        for vn in data["results"]:
                            if len(results) >= max_results:
                                break
                                
                            is_safe, _ = self.is_content_safe(vn, strict_filtering)
                            if is_safe:
                                results.append(self.format_vn_info(vn))
                    
                    return results
                
                else:
                    print(f"Search failed with status {response.status_code}: {response.text}")
                    return []
                    
            except Exception as e:
                print(f"Error searching VNs: {e}")
                return []

    async def fetch_vns_by_tags(self, required_tags: List[str] = None, excluded_tags: List[str] = None,
                               max_results: int = 10, min_rating: int = 60, min_votes: int = 50,
                               strict_filtering: bool = True, sort_by: str = "rating",
                               tag_logic: str = "any") -> List[Dict[str, Any]]:
        """
        Fetch VNs based on tag selection with improved filtering
        
        Args:
            required_tags: List of tags that should be present in the VN
            excluded_tags: List of tags that must NOT be present in the VN
            max_results: Maximum number of results to return
            min_rating: Minimum rating threshold (0-100)
            min_votes: Minimum number of user votes required
            strict_filtering: Whether to use strict NSFW filtering
            sort_by: Sort criteria ("rating", "votecount", "released")
            tag_logic: "any" (OR logic) or "all" (AND logic) for required tags
        """
        if not required_tags and not excluded_tags:
            raise ValueError("At least one of required_tags or excluded_tags must be provided")
        
        print(f"Debug: Searching for VNs with required_tags={required_tags}, excluded_tags={excluded_tags}, logic={tag_logic}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Build base filters
                base_filters = [
                    ["lang", "=", "en"],
                    ["rating", ">=", min_rating],
                    ["votecount", ">=", min_votes]
                ]
                
                # Add tag filters
                tag_filters = self.build_tag_filters(required_tags, excluded_tags, tag_logic)
                
                # Combine all filters with proper logic
                if tag_filters:
                    all_filters = ["and"] + base_filters + tag_filters
                else:
                    all_filters = ["and"] + base_filters
                
                payload = {
                    "filters": all_filters,
                    "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                    "results": max_results * 3,
                    "sort": sort_by,
                    "reverse": True
                }
                
                print(f"Debug: Final API payload filters: {all_filters}")
                
                response = await client.post(self.api_url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    print(f"Debug: API returned {len(data.get('results', []))} results")
                    
                    if data.get("results"):
                        for i, vn in enumerate(data["results"]):
                            if len(results) >= max_results:
                                break
                                
                            print(f"Debug: Processing VN {i+1}: {vn.get('title', 'Unknown')}")
                            
                            is_safe, reason = self.is_content_safe(vn, strict_filtering)
                            if is_safe:
                                formatted_vn = self.format_vn_info(vn)
                                results.append(formatted_vn)
                                print(f"Debug: Added '{formatted_vn['title']}' with tags: {formatted_vn['tags'][:5]}...")
                            else:
                                print(f"Debug: Filtered out {vn.get('title', 'Unknown')}: {reason}")
                    
                    print(f"Debug: Returning {len(results)} safe results")
                    return results
                
                elif response.status_code == 429:
                    print("Rate limited, waiting...")
                    await asyncio.sleep(2)
                    return []
                else:
                    print(f"API error {response.status_code}: {response.text}")
                    return []
                    
            except Exception as e:
                print(f"Error fetching VNs by tags: {e}")
                return []

    async def fetch_popular_vns(self, max_results: int = 10, min_rating: int = 70, 
                               min_votes: int = 100, strict_filtering: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch popular/highly-rated VNs without specific tag requirements
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                filters = ["and",
                    ["lang", "=", "en"],
                    ["rating", ">=", min_rating],
                    ["votecount", ">=", min_votes]
                ]
                
                payload = {
                    "filters": filters,
                    "fields": "id, title, rating, votecount, released, languages, image.url, description, tags.name",
                    "results": max_results * 3,
                    "sort": "rating",
                    "reverse": True
                }
                
                response = await client.post(self.api_url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    if data.get("results"):
                        for vn in data["results"]:
                            if len(results) >= max_results:
                                break
                                
                            is_safe, _ = self.is_content_safe(vn, strict_filtering)
                            if is_safe:
                                results.append(self.format_vn_info(vn))
                    
                    return results
                else:
                    return []
                    
            except Exception as e:
                print(f"Error fetching popular VNs: {e}")
                return []

    async def fetch_random_vn_with_tags(self, required_tags: List[str] = None, excluded_tags: List[str] = None,
                                       max_attempts: int = 3, strict_filtering: bool = True,
                                       min_rating: int = 60, min_votes: int = 50,
                                       tag_logic: str = "any") -> Optional[Dict[str, Any]]:
        """
        Fetch a single random VN that matches the tag criteria
        """
        # First try to get a pool of VNs matching the criteria
        results = await self.fetch_vns_by_tags(
            required_tags=required_tags,
            excluded_tags=excluded_tags,
            max_results=20,
            min_rating=min_rating,
            min_votes=min_votes,
            strict_filtering=strict_filtering,
            tag_logic=tag_logic
        )
        
        if results:
            return random.choice(results)
        
        # If no results with tags, fall back to popular VNs
        popular_results = await self.fetch_popular_vns(
            max_results=20,
            min_rating=min_rating,
            min_votes=min_votes,
            strict_filtering=strict_filtering
        )
        
        if popular_results:
            return random.choice(popular_results)
        
        return None

    async def fetch_random_vn(self, max_attempts: int = 200, strict_filtering: bool = True, 
                             min_rating: int = 60, max_id: int = 1000, min_votes: int = 100) -> Optional[Dict[str, Any]]:
        """
        Fetch a random SFW Visual Novel
        """
        # Use the more efficient approach
        popular_vns = await self.fetch_popular_vns(
            max_results=200,
            min_rating=min_rating,
            min_votes=min_votes,
            strict_filtering=strict_filtering
        )
        
        if popular_vns:
            return random.choice(popular_vns)
        
        return None