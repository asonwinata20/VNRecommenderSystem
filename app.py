import streamlit as st
import asyncio
import json
from datetime import datetime
import pandas as pd

# Import your VNDBFetcher - make sure this file exists and is properly implemented
try:
    from vndb_fetcher import VNDBFetcher
except ImportError as e:
    st.error(f"Error importing VNDBFetcher: {e}")
    st.error("Make sure vndb_fetcher.py exists and is properly implemented")
    st.stop()

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Visual Novel Recommender System",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize all session state variables"""
    try:
        if 'fetcher' not in st.session_state:
            st.session_state.fetcher = VNDBFetcher()
        if 'fetched_vns' not in st.session_state:
            st.session_state.fetched_vns = []
        if 'selected_required_tags' not in st.session_state:
            st.session_state.selected_required_tags = []
        if 'selected_excluded_tags' not in st.session_state:
            st.session_state.selected_excluded_tags = []
    except Exception as e:
        st.error(f"Error initializing session state: {e}")
        st.stop()

# Call initialization function
init_session_state()

# Custom CSS
st.markdown("""
<style>
    .vn-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
    .vn-title {
        font-size: 24px;
        font-weight: bold;
        color: #2E86C1;
        margin-bottom: 10px;
    }
    .vn-rating {
        font-size: 18px;
        color: #F39C12;
        margin-bottom: 5px;
    }
    .vn-tags {
        margin: 10px 0;
    }
    .tag {
        background-color: #3498DB;
        color: white;
        padding: 3px 8px;
        border-radius: 15px;
        font-size: 12px;
        margin: 2px;
        display: inline-block;
    }
    .required-tag {
        background-color: #27AE60;
        color: white;
        padding: 3px 8px;
        border-radius: 15px;
        font-size: 12px;
        margin: 2px;
        display: inline-block;
    }
    .excluded-tag {
        background-color: #E74C3C;
        color: white;
        padding: 3px 8px;
        border-radius: 15px;
        font-size: 12px;
        margin: 2px;
        display: inline-block;
    }
    .safe-indicator {
        background-color: #27AE60;
        color: white;
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .tag-category {
        background-color: #8E44AD;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        margin: 5px 0;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

def display_vn_card(vn_data):
    """Display a VN in a card format"""
    try:
        with st.container():
            st.markdown(f'<div class="vn-card">', unsafe_allow_html=True)
            
            # Title and safe indicator
            col1, col2 = st.columns([3, 1])
            with col1:
                title = vn_data.get("title", "Unknown Title")
                st.markdown(f'<div class="vn-title">🎮 {title}</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="safe-indicator">✅ SFW</div>', unsafe_allow_html=True)
            
            # Main content
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Rating and info
                rating = vn_data.get("rating", 0)
                votes = vn_data.get("votes", 0)
                vn_id = vn_data.get("id", "Unknown")
                released = vn_data.get("released", "Unknown")
                languages = vn_data.get("languages", [])
                
                st.markdown(f'<div class="vn-rating">⭐ Rating: {rating:.1f}/10</div>', unsafe_allow_html=True)
                st.write(f"🗳️ **Votes:** {votes:,}")
                st.write(f"🆔 **ID:** {vn_id}")
                st.write(f"📅 **Released:** {released}")
                st.write(f"🌐 **Languages:** {', '.join(languages) if languages else 'Unknown'}")
                
                # Description
                description = vn_data.get('description', 'No description available')
                st.write("📖 **Description:**")
                if len(description) > 400:
                    with st.expander("Click to read full description"):
                        st.write(description)
                    st.write(description[:400] + "...")
                else:
                    st.write(description)
                
                # Tags
                tags = vn_data.get('tags', [])
                if tags:
                    st.write("🏷️ **Tags:**")
                    tags_html = ""
                    for tag in tags[:10]:  # Show first 10 tags
                        tags_html += f'<span class="tag">{tag}</span>'
                    st.markdown(f'<div class="vn-tags">{tags_html}</div>', unsafe_allow_html=True)
                    
                    if len(tags) > 10:
                        with st.expander(f"Show all {len(tags)} tags"):
                            remaining_tags = ""
                            for tag in tags[10:]:
                                remaining_tags += f'<span class="tag">{tag}</span>'
                            st.markdown(f'<div class="vn-tags">{remaining_tags}</div>', unsafe_allow_html=True)
            
            with col2:
                # Image
                image_url = vn_data.get('image_url')
                if image_url:
                    try:
                        st.image(image_url, caption=title, use_container_width=True)
                    except Exception as e:
                        st.info("🖼️ Image could not be loaded")
                else:
                    st.info("🖼️ No image available")
            
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying VN card: {e}")

def display_tag_selector():
    """Display tag selection interface"""
    try:
        st.subheader("🏷️ Tag Selection")
        
        # Get available tags
        available_tags = st.session_state.fetcher.get_available_tags()
        
        # Create two columns for required and excluded tags
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### ✅ Required Tags (must have)")
            st.write("Select tags that the VN must include:")
            
            # Display tags by category for required tags
            for category, tags in available_tags.items():
                st.markdown(f'<div class="tag-category">{category.title()}</div>', unsafe_allow_html=True)
                for tag in tags:
                    if st.checkbox(f"✅ {tag}", key=f"req_{tag}", value=tag in st.session_state.selected_required_tags):
                        if tag not in st.session_state.selected_required_tags:
                            st.session_state.selected_required_tags.append(tag)
                    else:
                        if tag in st.session_state.selected_required_tags:
                            st.session_state.selected_required_tags.remove(tag)
        
        with col2:
            st.write("### ❌ Excluded Tags (must not have)")
            st.write("Select tags that the VN must NOT include:")
            
            # Display tags by category for excluded tags
            for category, tags in available_tags.items():
                st.markdown(f'<div class="tag-category">{category.title()}</div>', unsafe_allow_html=True)
                for tag in tags:
                    if st.checkbox(f"❌ {tag}", key=f"exc_{tag}", value=tag in st.session_state.selected_excluded_tags):
                        if tag not in st.session_state.selected_excluded_tags:
                            st.session_state.selected_excluded_tags.append(tag)
                    else:
                        if tag in st.session_state.selected_excluded_tags:
                            st.session_state.selected_excluded_tags.remove(tag)
        
        # Display current selection
        if st.session_state.selected_required_tags or st.session_state.selected_excluded_tags:
            st.write("### 📋 Current Selection")
            
            if st.session_state.selected_required_tags:
                st.write("**Required Tags:**")
                required_tags_html = ""
                for tag in st.session_state.selected_required_tags:
                    required_tags_html += f'<span class="required-tag">✅ {tag}</span>'
                st.markdown(f'<div class="vn-tags">{required_tags_html}</div>', unsafe_allow_html=True)
            
            if st.session_state.selected_excluded_tags:
                st.write("**Excluded Tags:**")
                excluded_tags_html = ""
                for tag in st.session_state.selected_excluded_tags:
                    excluded_tags_html += f'<span class="excluded-tag">❌ {tag}</span>'
                st.markdown(f'<div class="vn-tags">{excluded_tags_html}</div>', unsafe_allow_html=True)
            
            # Clear selections button
            if st.button("🗑️ Clear All Tag Selections"):
                st.session_state.selected_required_tags = []
                st.session_state.selected_excluded_tags = []
                st.rerun()
    except Exception as e:
        st.error(f"Error in tag selector: {e}")

async def fetch_vns_by_tags_async(required_tags, excluded_tags, max_results, min_rating, min_votes, strict_filtering, sort_by):
    """Async wrapper for fetching VNs by tags"""
    return await st.session_state.fetcher.fetch_vns_by_tags(
        required_tags=required_tags,
        excluded_tags=excluded_tags,
        max_results=max_results,
        min_rating=min_rating,
        min_votes=min_votes,
        strict_filtering=strict_filtering,
        sort_by=sort_by
    )

async def fetch_random_vn_with_tags_async(required_tags, excluded_tags, max_attempts, strict_filtering, min_rating, min_votes):
    """Async wrapper for fetching random VN with tags"""
    return await st.session_state.fetcher.fetch_random_vn_with_tags(
        required_tags=required_tags,
        excluded_tags=excluded_tags,
        max_attempts=max_attempts,
        strict_filtering=strict_filtering,
        min_rating=min_rating,
        min_votes=min_votes
    )

async def fetch_vn_async(max_attempts, strict_filtering, min_rating, max_id, min_votes):
    """Async wrapper for fetching VN (legacy method)"""
    return await st.session_state.fetcher.fetch_random_vn(
        max_attempts=max_attempts,
        strict_filtering=strict_filtering,
        min_rating=min_rating,
        max_id=max_id,
        min_votes=min_votes
    )

def main():
    """Main application function"""
    try:
        # Ensure session state is initialized (defensive programming)
        init_session_state()
        
        # Header
        st.title("🎮 Visual Novel Recommendation System")
        st.markdown("Discover Visual Novel using tag-based fetching from the VNDB database!")
        
        # Sidebar for settings
        st.sidebar.header("⚙️ Settings")
        
        # Filtering options
        st.sidebar.subheader("🔍 Filtering Options")
        strict_filtering = st.sidebar.toggle("Strict SFW Filtering", value=True, help="More restrictive content filtering")
        min_rating = st.sidebar.slider("Minimum Rating", 0, 100, 60, 5, help="Minimum VNDB rating (0-100)")
        min_votes = st.sidebar.slider("Minimum Votes", 100, 1000, 50, 10, help="Minimum number of user votes")
        
        # Sort options for tag-based search
        st.sidebar.subheader("📊 Sort Options")
        sort_by = st.sidebar.selectbox("Sort by", ["rating", "votecount", "released"], help="How to sort the results")
        
        # Legacy options
        st.sidebar.subheader("🎲 Legacy Random Options")
        max_id = st.sidebar.slider("Search Range (Max ID)", 100, 5000, 1500, 100, help="Higher = more VNs but slower (for random mode)")
        max_attempts = st.sidebar.slider("Max Attempts", 10, 300, 50, 10, help="How hard to try finding a VN")
        
        # Main tabs
        tab1, tab4, tab5 = st.tabs(["🏷️ Tag-Based Search", "📊 Statistics", "ℹ️ Help"])
        
        with tab1:
            st.header("🏷️ Tag-Based VN Search")
            st.write("Select tags to find VNs that match your preferences!")
            
            # Tag selector
            display_tag_selector()
            
            # Search controls
            st.subheader("🔍 Search Controls")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                max_results = st.number_input("Max Results", 1, 20, 5, help="Maximum number of VNs to fetch")
            
            with col2:
                # Single random VN with tags
                if st.button("🎲 Get Random VN with Tags", type="primary"):
                    if not st.session_state.selected_required_tags and not st.session_state.selected_excluded_tags:
                        st.warning("⚠️ Please select at least one required or excluded tag first!")
                    else:
                        with st.spinner("🔍 Searching for VN with selected tags..."):
                            try:
                                vn = asyncio.run(fetch_random_vn_with_tags_async(
                                    st.session_state.selected_required_tags,
                                    st.session_state.selected_excluded_tags,
                                    max_attempts,
                                    strict_filtering,
                                    min_rating,
                                    min_votes
                                ))
                                if vn:
                                    st.session_state.fetched_vns.append(vn)
                                    st.success("✅ Found a matching VN!")
                                else:
                                    st.error("❌ No VN found with selected tags. Try different tag combinations.")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
            
            with col3:
                # Multiple VNs with tags
                if st.button("📚 Search Multiple VNs", type="secondary"):
                    if not st.session_state.selected_required_tags and not st.session_state.selected_excluded_tags:
                        st.warning("⚠️ Please select at least one required or excluded tag first!")
                    else:
                        with st.spinner(f"🔍 Searching for {max_results} VNs with selected tags..."):
                            try:
                                vns = asyncio.run(fetch_vns_by_tags_async(
                                    st.session_state.selected_required_tags,
                                    st.session_state.selected_excluded_tags,
                                    max_results,
                                    min_rating,
                                    min_votes,
                                    strict_filtering,
                                    sort_by
                                ))
                                if vns:
                                    st.session_state.fetched_vns.extend(vns)
                                    st.success(f"✅ Found {len(vns)} matching VNs!")
                                else:
                                    st.error("❌ No VNs found with selected tags. Try different tag combinations.")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        
        # with tab2:
        #     st.header("🎲 Get Random SFW VN")
        #     st.write("Click the button below to fetch a random safe-for-work visual novel (no tag filtering)!")
            
        #     col1, col2, col3 = st.columns([1, 1, 2])
        #     with col1:
        #         if st.button("🎲 Fetch Random VN", type="primary"):
        #             with st.spinner("🔍 Searching for SFW visual novel..."):
        #                 try:
        #                     vn = asyncio.run(fetch_vn_async(
        #                         max_attempts, strict_filtering, min_rating, max_id, min_votes
        #                     ))
        #                     if vn:
        #                         st.session_state.fetched_vns.append(vn)
        #                         st.success("✅ Found a great VN!")
        #                     else:
        #                         st.error("❌ No VN found with current criteria. Try adjusting the settings.")
        #                 except Exception as e:
        #                     st.error(f"❌ Error: {str(e)}")
            
        #     with col2:
        #         if st.button("🗑️ Clear Results"):
        #             st.session_state.fetched_vns = []
        #             st.success("Results cleared!")
        
        # with tab3:
        #     st.header("🔢 Fetch Multiple Random VNs")
        #     st.write("Get several random VNs at once (no tag filtering)!")
            
        #     col1, col2 = st.columns([1, 1])
        #     with col1:
        #         vn_count = st.number_input("Number of VNs to fetch", 1, 10, 3)
            
        #     with col2:
        #         if st.button("🔢 Fetch Multiple VNs", type="primary"):
        #             with st.spinner(f"🔍 Fetching {vn_count} VNs..."):
        #                 progress_bar = st.progress(0)
        #                 try:
        #                     for i in range(vn_count):
        #                         vn = asyncio.run(fetch_vn_async(
        #                             max_attempts, strict_filtering, min_rating, max_id, min_votes
        #                         ))
        #                         if vn:
        #                             st.session_state.fetched_vns.append(vn)
        #                         progress_bar.progress((i + 1) / vn_count)
                            
        #                     st.success(f"✅ Fetching complete!")
        #                 except Exception as e:
        #                     st.error(f"❌ Error: {str(e)}")
        
        with tab4:
            st.header("📊 Statistics & Data Export")
            
            if st.session_state.fetched_vns:
                total_vns = len(st.session_state.fetched_vns)
                avg_rating = sum(vn.get('rating', 0) for vn in st.session_state.fetched_vns) / total_vns
                avg_votes = sum(vn.get('votes', 0) for vn in st.session_state.fetched_vns) / total_vns
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total VNs Fetched", total_vns)
                with col2:
                    st.metric("Average Rating", f"{avg_rating:.1f}/10")
                with col3:
                    st.metric("Average Votes", f"{avg_votes:,.0f}")
                
                # Create DataFrame for export
                df_data = []
                for vn in st.session_state.fetched_vns:
                    df_data.append({
                        'Title': vn.get('title', 'Unknown'),
                        'ID': vn.get('id', 'Unknown'),
                        'Rating': vn.get('rating', 0),
                        'Votes': vn.get('votes', 0),
                        'Released': vn.get('released', 'Unknown'),
                        'Languages': ', '.join(vn.get('languages', [])),
                        'Tags': ', '.join(vn.get('tags', [])[:5]),
                        'Image URL': vn.get('image_url', '')
                    })
                
                df = pd.DataFrame(df_data)
                
                # Display table
                st.subheader("📋 VN Data Table")
                st.dataframe(df, use_container_width=True)
                
                # Export options
                st.subheader("💾 Export Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📄 Download as CSV",
                        csv,
                        f"vndb_sfw_vns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
                
                with col2:
                    json_data = json.dumps(st.session_state.fetched_vns, indent=2, ensure_ascii=False)
                    st.download_button(
                        "📄 Download as JSON",
                        json_data,
                        f"vndb_sfw_vns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        "application/json"
                    )
            else:
                st.info("📊 No data to display. Fetch some VNs first!")
        
        with tab5:
            st.header("ℹ️ How to Use")
            
            st.subheader("🏷️ Tag-Based Search")
            st.write("""
            1. **Select Required Tags**: Choose tags that the VN must have
            2. **Select Excluded Tags**: Choose tags that the VN must NOT have
            3. **Use Search Controls**: Get a single random VN or multiple VNs matching your criteria
            4. **Adjust Settings**: Use the sidebar to fine-tune filtering options
            """)
            
            st.subheader("📚 Tag Categories")
            try:
                available_tags = st.session_state.fetcher.get_available_tags()
                for category, tags in available_tags.items():
                    st.write(f"**{category.title()}:** {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
            except Exception as e:
                st.error(f"Error loading tags: {e}")
            
            st.subheader("⚙️ Settings Explained")
            st.write("""
            - **Strict SFW Filtering**: More aggressive content filtering
            - **Minimum Rating**: Only show VNs with rating above this threshold
            - **Minimum Votes**: Only show VNs with enough user votes for reliability
            - **Sort By**: How to order results (rating, vote count, or release date)
            """)
            
            st.subheader("💡 Tips")
            st.write("""
            - Start with broad tags (like "Romance" or "Mystery") and refine from there
            - Use excluded tags to filter out content you don't want
            - Lower the minimum votes if you want to discover lesser-known VNs
            - Try different sort options to find hidden gems
            """)
        
        # Display fetched VNs (common to all tabs)
        if st.session_state.fetched_vns:
            st.header(f"📚 Fetched VNs ({len(st.session_state.fetched_vns)})")
            for i, vn in enumerate(reversed(st.session_state.fetched_vns)):
                st.write(f"### VN #{len(st.session_state.fetched_vns) - i}")
                display_vn_card(vn)
        
        # Footer
        st.markdown("---")
        st.markdown("**🎮 VNDB SFW Tag Fetcher** | Data from [VNDB.org](https://vndb.org) | Safe content filtering applied")
    
    except Exception as e:
        st.error(f"Critical error in main function: {e}")
        st.error("Please check your vndb_fetcher.py file and ensure all dependencies are installed.")

# Run the app
if __name__ == "__main__":
    main()