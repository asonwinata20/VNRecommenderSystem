import streamlit as st
import asyncio
import json
from datetime import datetime
from vndb_fetcher import VNDBFetcher
import pandas as pd

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="VNDB SFW Fetcher",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state IMMEDIATELY after page config
def init_session_state():
    """Initialize all session state variables"""
    if 'fetcher' not in st.session_state:
        st.session_state.fetcher = VNDBFetcher()
    if 'fetched_vns' not in st.session_state:
        st.session_state.fetched_vns = []
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

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
    .safe-indicator {
        background-color: #27AE60;
        color: white;
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

def display_vn_card(vn_data):
    """Display a VN in a card format"""
    with st.container():
        st.markdown(f'<div class="vn-card">', unsafe_allow_html=True)
        
        # Title and safe indicator
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f'<div class="vn-title">🎮 {vn_data["title"]}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="safe-indicator">✅ SFW</div>', unsafe_allow_html=True)
        
        # Main content
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Rating and info
            st.markdown(f'<div class="vn-rating">⭐ Rating: {vn_data["rating"]:.1f}/10</div>', unsafe_allow_html=True)
            st.write(f"🗳️ **Votes:** {vn_data['votes']:,}")
            st.write(f"🆔 **ID:** {vn_data['id']}")
            st.write(f"📅 **Released:** {vn_data['released']}")
            st.write(f"🌐 **Languages:** {', '.join(vn_data['languages'])}")
            
            # Description
            st.write("📖 **Description:**")
            description = vn_data['description']
            if len(description) > 400:
                with st.expander("Click to read full description"):
                    st.write(description)
                st.write(description[:400] + "...")
            else:
                st.write(description)
            
            # Tags
            if vn_data['tags']:
                st.write("🏷️ **Tags:**")
                tags_html = ""
                for tag in vn_data['tags'][:10]:  # Show first 10 tags
                    tags_html += f'<span class="tag">{tag}</span>'
                st.markdown(f'<div class="vn-tags">{tags_html}</div>', unsafe_allow_html=True)
                
                if len(vn_data['tags']) > 10:
                    with st.expander(f"Show all {len(vn_data['tags'])} tags"):
                        remaining_tags = ""
                        for tag in vn_data['tags'][10:]:
                            remaining_tags += f'<span class="tag">{tag}</span>'
                        st.markdown(f'<div class="vn-tags">{remaining_tags}</div>', unsafe_allow_html=True)
        
        with col2:
            # Image
            if vn_data['image_url']:
                st.image(vn_data['image_url'], caption=vn_data['title'], use_column_width=True)
            else:
                st.info("🖼️ No image available")
        
        st.markdown('</div>', unsafe_allow_html=True)

async def fetch_vn_async(max_attempts, strict_filtering, min_rating, max_id, min_votes):
    """Async wrapper for fetching VN"""
    return await st.session_state.fetcher.fetch_random_vn(
        max_attempts=max_attempts,
        strict_filtering=strict_filtering,
        min_rating=min_rating,
        max_id=max_id,
        min_votes=min_votes
    )

async def fetch_multiple_vns_async(count, **kwargs):
    """Async wrapper for fetching multiple VNs"""
    return await st.session_state.fetcher.fetch_multiple_vns(count=count, **kwargs)

async def search_vns_async(title, max_results, min_votes):
    """Async wrapper for searching VNs"""
    return await st.session_state.fetcher.search_vns_by_title(
        title=title,
        max_results=max_results,
        min_votes=min_votes
    )

def main():
    # Ensure session state is initialized (defensive programming)
    init_session_state()
    
    # Header
    st.title("🎮 VNDB SFW Visual Novel Fetcher")
    st.markdown("Discover safe-for-work visual novels from the VNDB database!")
    
    # Sidebar for settings
    st.sidebar.header("⚙️ Settings")
    
    # Filtering options
    st.sidebar.subheader("🔍 Filtering Options")
    strict_filtering = st.sidebar.toggle("Strict SFW Filtering", value=True, help="More restrictive content filtering")
    min_rating = st.sidebar.slider("Minimum Rating", 0, 100, 60, 5, help="Minimum VNDB rating (0-100)")
    min_votes = st.sidebar.slider("Minimum Votes", 10, 5000, 100, 10, help="Minimum number of user votes")
    max_id = st.sidebar.slider("Search Range (Max ID)", 10, 10000, 1500, 100, help="Higher = more VNs but slower")
    max_attempts = st.sidebar.slider("Max Attempts", 10, 1000, 50, 10, help="How hard to try finding a VN")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎲 Random VN", "🔢 Multiple VNs", "🔍 Search", "📊 Statistics"])
    
    with tab1:
        st.header("🎲 Get Random SFW VN")
        st.write("Click the button below to fetch a random safe-for-work visual novel!")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🎲 Fetch Random VN", type="primary"):
                with st.spinner("🔍 Searching for SFW visual novel..."):
                    try:
                        vn = asyncio.run(fetch_vn_async(
                            max_attempts, strict_filtering, min_rating, max_id, min_votes
                        ))
                        if vn:
                            st.session_state.fetched_vns.append(vn)
                            st.success("✅ Found a great VN!")
                        else:
                            st.error("❌ No VN found with current criteria. Try adjusting the settings.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        with col2:
            if st.button("🗑️ Clear Results"):
                st.session_state.fetched_vns = []
                st.success("Results cleared!")
        
        # Display fetched VNs
        if st.session_state.fetched_vns:
            st.subheader(f"📚 Fetched VNs ({len(st.session_state.fetched_vns)})")
            for i, vn in enumerate(reversed(st.session_state.fetched_vns)):
                st.write(f"### VN #{len(st.session_state.fetched_vns) - i}")
                display_vn_card(vn)
    
    with tab2:
        st.header("🔢 Fetch Multiple VNs")
        st.write("Get several VNs at once!")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            vn_count = st.number_input("Number of VNs to fetch", 1, 10, 3)
        
        with col2:
            if st.button("🔢 Fetch Multiple VNs", type="primary"):
                with st.spinner(f"🔍 Fetching {vn_count} VNs..."):
                    progress_bar = st.progress(0)
                    try:
                        for i in range(vn_count):
                            vn = asyncio.run(fetch_vn_async(
                                max_attempts, strict_filtering, min_rating, max_id, min_votes
                            ))
                            if vn:
                                st.session_state.fetched_vns.append(vn)
                            progress_bar.progress((i + 1) / vn_count)
                        
                        st.success(f"✅ Fetching complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        # Display recent batch
        if st.session_state.fetched_vns:
            recent_vns = st.session_state.fetched_vns[-vn_count:] if len(st.session_state.fetched_vns) >= vn_count else st.session_state.fetched_vns
            st.subheader(f"📚 Recent Batch ({len(recent_vns)} VNs)")
            for i, vn in enumerate(recent_vns):
                display_vn_card(vn)
    
    with tab3:
        st.header("🔍 Search VNs by Title")
        st.write("Search for specific visual novels by title!")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_query = st.text_input("Enter VN title to search", placeholder="e.g., Steins Gate")
        
        with col2:
            max_results = st.number_input("Max Results", 1, 20, 10)
        
        if st.button("🔍 Search VNs", type="primary"):
            if search_query:
                with st.spinner(f"🔍 Searching for '{search_query}'..."):
                    try:
                        results = asyncio.run(search_vns_async(search_query, max_results, min_votes))
                        st.session_state.search_results = results
                        if results:
                            st.success(f"✅ Found {len(results)} VNs!")
                        else:
                            st.warning("⚠️ No VNs found matching your search.")
                    except Exception as e:
                        st.error(f"❌ Search error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a search term.")
        
        # Display search results
        if st.session_state.search_results:
            st.subheader(f"🔍 Search Results ({len(st.session_state.search_results)})")
            for i, vn in enumerate(st.session_state.search_results):
                st.write(f"### Result #{i + 1}")
                display_vn_card(vn)
    
    with tab4:
        st.header("📊 Statistics & Data Export")
        
        if st.session_state.fetched_vns:
            total_vns = len(st.session_state.fetched_vns)
            avg_rating = sum(vn['rating'] for vn in st.session_state.fetched_vns) / total_vns
            avg_votes = sum(vn['votes'] for vn in st.session_state.fetched_vns) / total_vns
            
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
                    'Title': vn['title'],
                    'ID': vn['id'],
                    'Rating': vn['rating'],
                    'Votes': vn['votes'],
                    'Released': vn['released'],
                    'Languages': ', '.join(vn['languages']),
                    'Tags': ', '.join(vn['tags'][:5]) if vn['tags'] else '',
                    'Image URL': vn['image_url'] or ''
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
    
    # Footer
    st.markdown("---")
    st.markdown("**🎮 VNDB SFW Fetcher** | Data from [VNDB.org](https://vndb.org) | Safe content filtering applied")

if __name__ == "__main__":
    main()
