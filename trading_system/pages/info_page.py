"""
Info Page - Display news data information and preview.
"""
import streamlit as st
import subprocess
import sys
from pathlib import Path
from services.chatbot_service import get_chatbot_service


def scan_news_data() -> tuple[bool, str, str]:
    """
    Chạy trend_news/main.py để scan dữ liệu mới.
    
    Returns:
        tuple: (success: bool, message: str, output: str)
    """
    try:
        # Xác định đường dẫn đến trend_news/main.py
        # Từ trading_system/pages/info_page.py -> ../../trend_news/main.py
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        trend_news_main = project_root / "trend_news" / "main.py"
        trend_news_dir = project_root / "trend_news"
        
        # Kiểm tra file tồn tại
        if not trend_news_main.exists():
            return False, f"❌ Không tìm thấy file: {trend_news_main}", ""
        
        # Chạy subprocess trong thư mục trend_news để đảm bảo import paths đúng
        result = subprocess.run(
            [sys.executable, str(trend_news_main)],
            cwd=str(trend_news_dir),
            capture_output=True,
            text=True,
            timeout=600  # Timeout 10 phút
        )
        
        if result.returncode == 0:
            return True, "✅ Quét dữ liệu thành công!", result.stdout
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return False, f"❌ Lỗi khi quét dữ liệu (exit code: {result.returncode})", error_msg
            
    except subprocess.TimeoutExpired:
        return False, "❌ Quét dữ liệu timeout sau 10 phút", ""
    except FileNotFoundError as e:
        return False, f"❌ Không tìm thấy file hoặc thư mục: {e}", ""
    except Exception as e:
        return False, f"❌ Lỗi khi chạy scan: {str(e)}", ""


def render():
    """Render the info page."""
    # Get chatbot service
    try:
        chatbot = get_chatbot_service()
        available_dates = chatbot.get_available_dates()
    except ValueError as e:
        st.error(str(e))
        st.info("Please update OPENAI_API_KEY in trading_system/.env file")
        return
    
    if not available_dates:
        st.warning("No news data found.")
        st.info("Please run trend_news crawler first to generate news data.")
    
    # Scan button section
    st.subheader("🔄 Scan News Data")
    st.caption("Quét dữ liệu news mới từ các nguồn tin tức")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        scan_button = st.button("🔄 Scan", type="primary", key="scan_news_button", use_container_width=True)
    
    if scan_button:
        with st.spinner("Đang quét dữ liệu news... Vui lòng đợi (có thể mất vài phút)"):
            success, message, output = scan_news_data()
            
            if success:
                st.success(message)
                if output:
                    with st.expander("📋 Chi tiết output", expanded=False):
                        st.text(output)
                # Refresh để hiển thị data mới
                st.rerun()
            else:
                st.error(message)
                if output:
                    with st.expander("❌ Chi tiết lỗi", expanded=True):
                        st.text(output)
    
    if not available_dates:
        return
    
    st.divider()
    
    # Quick summary section
    st.subheader("🔍 Quick Search")
    st.caption("Search for specific keywords in the news data")
    
    # Get default selected date for search
    selected_date_for_search = available_dates[0] if available_dates else None
    
    search_term = st.text_input("Enter keyword to search", placeholder="e.g., AI, 茅台, Bitcoin...", key="info_search_term")
    
    if search_term and selected_date_for_search:
        preview_content = chatbot.get_document_preview(selected_date_for_search, max_lines=1000)
        
        # Simple search
        lines_with_keyword = [
            line.strip() for line in preview_content.split("\n") 
            if search_term.lower() in line.lower()
        ]
        
        if lines_with_keyword:
            st.success(f"Found {len(lines_with_keyword)} matches:")
            for i, line in enumerate(lines_with_keyword[:20], 1):
                st.markdown(f"{i}. {line}")
            if len(lines_with_keyword) > 20:
                st.info(f"... and {len(lines_with_keyword) - 20} more matches")
        else:
            st.warning(f"No matches found for '{search_term}'")
    
    st.divider()
    
    # Document preview
    st.subheader("📄 Document Preview")
    
    selected_date = st.selectbox(
        "Select date to preview",
        options=available_dates,
        index=0,
        key="info_date_select"
    )
    
    # Preview options
    col1, col2 = st.columns([3, 1])
    with col1:
        max_lines = st.slider("Max lines", min_value=50, max_value=500, value=100, step=50, key="info_max_lines")
    with col2:
        show_preview = st.button("👁️ Show Preview", type="primary", key="info_show_preview")
    
    if show_preview:
        preview_content = chatbot.get_document_preview(selected_date, max_lines=max_lines)
        
        # Show file info
        txt_files = chatbot.get_txt_files(selected_date)
        if txt_files:
            st.info(f"Showing: **{txt_files[-1].name}** ({max_lines} lines max)")
        
        # Display content in expandable container
        with st.expander("📝 Document Content", expanded=True):
            st.text(preview_content)

    st.divider()
    # Date selection
    st.subheader("📋 Available Dates")
    
    # Display dates as table
    date_data = []
    for date_str in available_dates:
        txt_files = chatbot.get_txt_files(date_str)
        date_data.append({
            "Date": date_str,
            "Files": len(txt_files),
            "Latest File": txt_files[-1].name if txt_files else "N/A"
        })
    
    st.dataframe(date_data, use_container_width=True, hide_index=True)
    
    st.divider()

    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📅 Available Dates", len(available_dates))
    with col2:
        st.metric("📁 Data Path", "trend_news/output")
    with col3:
        latest_date = available_dates[0] if available_dates else "N/A"
        st.metric("🆕 Latest Date", latest_date[:10] if len(latest_date) > 10 else latest_date)
    

if __name__ == "__main__":
    render()
