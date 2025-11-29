"""
Streamlit Visa Exhibit Generator
Standalone application for generating numbered exhibit packages from PDFs, folders, and Google Drive
"""

import streamlit as st
import os
from pathlib import Path
import zipfile
import tempfile
from datetime import datetime

# Import our custom modules
from exhibit_processor import ExhibitProcessor
from pdf_handler import PDFHandler
from google_drive import GoogleDriveHandler
from archive_handler import ArchiveHandler

# Page config
st.set_page_config(
    page_title="Visa Exhibit Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'exhibits' not in st.session_state:
    st.session_state.exhibits = []
if 'processor' not in st.session_state:
    st.session_state.processor = ExhibitProcessor()

def main():
    # Header
    st.markdown('<div class="main-header">📄 Visa Exhibit Generator</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Archive.org option
        archive_urls = st.checkbox("Archive URLs to archive.org", value=True)

        # Exhibit numbering
        numbering_style = st.selectbox(
            "Exhibit Numbering Style",
            ["Letters (A, B, C...)", "Numbers (1, 2, 3...)", "Roman (I, II, III...)"]
        )

        # Include TOC
        include_toc = st.checkbox("Include Table of Contents", value=True)

        # Merge PDFs
        merge_all = st.checkbox("Merge all exhibits into single PDF", value=True)

        st.divider()

        # API Configuration
        with st.expander("🔑 API Configuration (Optional)"):
            api2pdf_key = st.text_input("API2PDF Key", type="password", help="For URL to PDF conversion")
            google_creds = st.file_uploader("Google Credentials JSON", type=['json'], help="For Google Drive access")

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Upload Files", "🔗 Add URLs", "☁️ Google Drive", "📊 Generate"])

    # Tab 1: Upload Files
    with tab1:
        st.header("Upload PDFs and Documents")

        col1, col2 = st.columns([2, 1])

        with col1:
            # File uploader
            uploaded_files = st.file_uploader(
                "Upload PDF files for exhibits",
                type=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                help="Upload individual files or multiple files at once"
            )

            # ZIP file uploader
            zip_file = st.file_uploader(
                "Or upload a ZIP file containing exhibits",
                type=['zip'],
                help="Upload a ZIP file with all your exhibits"
            )

        with col2:
            st.info("💡 **Tips:**\n- Upload PDFs directly\n- Use ZIP for folders\n- Drag & drop supported\n- No file size limit")

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded")

            # Preview uploaded files
            with st.expander("View uploaded files"):
                for idx, file in enumerate(uploaded_files):
                    st.write(f"{idx + 1}. {file.name} ({file.size / 1024:.1f} KB)")

            # Add to exhibits
            if st.button("Add Files to Exhibit List", type="primary"):
                with st.spinner("Processing files..."):
                    for file in uploaded_files:
                        # Save to temp and add to exhibits
                        temp_path = save_uploaded_file(file)
                        st.session_state.exhibits.append({
                            'source': 'upload',
                            'path': temp_path,
                            'name': file.name,
                            'type': 'file'
                        })
                st.success(f"Added {len(uploaded_files)} exhibits!")
                st.rerun()

        if zip_file:
            st.success(f"✅ ZIP file uploaded: {zip_file.name}")

            if st.button("Extract ZIP and Add Exhibits", type="primary"):
                with st.spinner("Extracting ZIP file..."):
                    extracted_files = extract_zip(zip_file)
                    for file_path, file_name in extracted_files:
                        st.session_state.exhibits.append({
                            'source': 'zip',
                            'path': file_path,
                            'name': file_name,
                            'type': 'file'
                        })
                st.success(f"Extracted and added {len(extracted_files)} exhibits!")
                st.rerun()

    # Tab 2: Add URLs
    with tab2:
        st.header("Add URLs for Exhibits")

        col1, col2 = st.columns([2, 1])

        with col1:
            url_input = st.text_area(
                "Enter URLs (one per line)",
                height=200,
                placeholder="https://example.com/article1\nhttps://example.com/article2"
            )

            if st.button("Add URLs to Exhibit List", type="primary"):
                urls = [url.strip() for url in url_input.split('\n') if url.strip()]
                if urls:
                    with st.spinner(f"Processing {len(urls)} URLs..."):
                        for url in urls:
                            st.session_state.exhibits.append({
                                'source': 'url',
                                'url': url,
                                'name': url.split('/')[-1] or 'webpage',
                                'type': 'url'
                            })
                    st.success(f"Added {len(urls)} URL exhibits!")
                    st.rerun()
                else:
                    st.warning("Please enter at least one URL")

        with col2:
            st.info("💡 **URL Tips:**\n- One URL per line\n- Will be archived\n- Converted to PDF\n- Headers added")

    # Tab 3: Google Drive
    with tab3:
        st.header("Import from Google Drive")

        if not google_creds:
            st.warning("⚠️ Please upload Google credentials in the sidebar to use this feature")
        else:
            st.success("✅ Google credentials loaded")

            # Initialize Drive handler
            drive_handler = GoogleDriveHandler(google_creds)

            folder_url = st.text_input(
                "Google Drive Folder URL",
                placeholder="https://drive.google.com/drive/folders/..."
            )

            if st.button("Import Folder", type="primary"):
                if folder_url:
                    with st.spinner("Importing from Google Drive..."):
                        files = drive_handler.list_folder_files(folder_url)
                        for file_info in files:
                            st.session_state.exhibits.append({
                                'source': 'google_drive',
                                'file_id': file_info['id'],
                                'name': file_info['name'],
                                'type': 'file'
                            })
                    st.success(f"Imported {len(files)} files from Google Drive!")
                    st.rerun()

    # Tab 4: Generate
    with tab4:
        st.header("Generate Exhibit Package")

        # Display current exhibits
        st.subheader(f"📋 Current Exhibits: {len(st.session_state.exhibits)}")

        if st.session_state.exhibits:
            # Exhibit list
            for idx, exhibit in enumerate(st.session_state.exhibits):
                col1, col2, col3 = st.columns([0.5, 3, 1])

                with col1:
                    st.write(f"**{get_exhibit_number(idx, numbering_style)}**")

                with col2:
                    st.write(exhibit['name'])

                with col3:
                    if st.button("🗑️", key=f"delete_{idx}"):
                        st.session_state.exhibits.pop(idx)
                        st.rerun()

            st.divider()

            # Generation settings
            col1, col2 = st.columns(2)

            with col1:
                case_name = st.text_input("Case Name/ID", value=f"Exhibit_Package_{datetime.now().strftime('%Y%m%d')}")

            with col2:
                beneficiary_name = st.text_input("Beneficiary Name (Optional)", placeholder="John Doe")

            # Generate button
            if st.button("🚀 Generate Exhibit Package", type="primary", use_container_width=True):
                generate_exhibits(
                    case_name,
                    beneficiary_name,
                    numbering_style,
                    include_toc,
                    merge_all,
                    archive_urls
                )
        else:
            st.info("👆 Add exhibits using the tabs above to get started")

        # Clear all button
        if st.session_state.exhibits:
            if st.button("🗑️ Clear All Exhibits", type="secondary"):
                st.session_state.exhibits = []
                st.rerun()


def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp directory"""
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, uploaded_file.name)

    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    return file_path


def extract_zip(zip_file):
    """Extract ZIP file and return list of file paths"""
    temp_dir = tempfile.mkdtemp()
    extracted_files = []

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

        # Walk through extracted files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(root, file)
                    extracted_files.append((file_path, file))

    return extracted_files


def get_exhibit_number(idx, style):
    """Generate exhibit number based on style"""
    if style == "Letters (A, B, C...)":
        return chr(65 + idx)  # A, B, C...
    elif style == "Numbers (1, 2, 3...)":
        return str(idx + 1)
    else:  # Roman numerals
        romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
        return romans[idx] if idx < len(romans) else str(idx + 1)


def generate_exhibits(case_name, beneficiary_name, numbering_style, include_toc, merge_all, archive_urls):
    """Generate the final exhibit package"""

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Process each exhibit
        status_text.text("Processing exhibits...")
        progress_bar.progress(10)

        processed_exhibits = []
        pdf_handler = PDFHandler()
        archive_handler = ArchiveHandler()

        for idx, exhibit in enumerate(st.session_state.exhibits):
            status_text.text(f"Processing exhibit {idx + 1}/{len(st.session_state.exhibits)}...")

            exhibit_num = get_exhibit_number(idx, numbering_style)

            # Handle different source types
            if exhibit['type'] == 'file':
                pdf_path = exhibit['path']
            elif exhibit['type'] == 'url':
                # Archive URL if enabled
                if archive_urls:
                    archived = archive_handler.archive_url(exhibit['url'])
                    exhibit['archive_url'] = archived.get('archive_url')

                # Convert URL to PDF (requires API2PDF or similar)
                pdf_path = pdf_handler.url_to_pdf(exhibit['url'])

            # Add exhibit number to PDF
            numbered_pdf = pdf_handler.add_exhibit_number(pdf_path, exhibit_num)

            processed_exhibits.append({
                'number': exhibit_num,
                'path': numbered_pdf,
                'name': exhibit['name'],
                'original_url': exhibit.get('url'),
                'archive_url': exhibit.get('archive_url')
            })

            progress_bar.progress(10 + (idx + 1) * 60 // len(st.session_state.exhibits))

        # Step 2: Generate Table of Contents
        if include_toc:
            status_text.text("Generating Table of Contents...")
            progress_bar.progress(75)

            toc_pdf = pdf_handler.generate_toc(
                processed_exhibits,
                case_name,
                beneficiary_name
            )

        # Step 3: Merge all PDFs
        if merge_all:
            status_text.text("Merging all exhibits...")
            progress_bar.progress(85)

            pdf_files = []
            if include_toc and toc_pdf:
                pdf_files.append(toc_pdf)
            pdf_files.extend([ex['path'] for ex in processed_exhibits])

            final_pdf = pdf_handler.merge_pdfs(pdf_files, case_name)

        # Step 4: Complete
        progress_bar.progress(100)
        status_text.text("✅ Generation complete!")

        # Display results
        st.success("🎉 Exhibit package generated successfully!")

        # Download buttons
        col1, col2 = st.columns(2)

        with col1:
            if merge_all and final_pdf:
                with open(final_pdf, 'rb') as f:
                    st.download_button(
                        label="📥 Download Complete Package",
                        data=f.read(),
                        file_name=f"{case_name}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )

        with col2:
            if include_toc and toc_pdf:
                with open(toc_pdf, 'rb') as f:
                    st.download_button(
                        label="📋 Download Table of Contents",
                        data=f.read(),
                        file_name=f"{case_name}_TOC.pdf",
                        mime="application/pdf"
                    )

        # Individual exhibits
        with st.expander("Download Individual Exhibits"):
            for exhibit in processed_exhibits:
                with open(exhibit['path'], 'rb') as f:
                    st.download_button(
                        label=f"Exhibit {exhibit['number']}: {exhibit['name']}",
                        data=f.read(),
                        file_name=f"Exhibit_{exhibit['number']}_{exhibit['name']}.pdf",
                        mime="application/pdf",
                        key=f"download_{exhibit['number']}"
                    )

    except Exception as e:
        st.error(f"❌ Error generating exhibits: {str(e)}")
        progress_bar.progress(0)


if __name__ == "__main__":
    main()
