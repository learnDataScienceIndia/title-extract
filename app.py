import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import os
import io
import zipfile
from io import StringIO

# --- App Configuration ---
st.set_page_config(
    page_title="HTML Title Tag Updater",
    page_icon="👑",
    layout="wide"
)

# --- Main Application UI ---
st.title("👑 Bulk HTML Title Tag Updater")
st.markdown("""
This tool allows you to update the `<title>` tags of multiple HTML files based on a URL mapping.
**Follow the steps below to get started.**
""")

# --- Step 1: Provide URL-to-Title Mapping ---
st.header("Step 1: Provide Your URL-to-Title Mapping")
st.markdown("Choose one of the two methods below to provide your data.")

# --- Use tabs for different input methods ---
tab1, tab2 = st.tabs(["📋 Paste Data Directly", "📄 Upload CSV File"])

# Initialize a placeholder for the DataFrame
df = None

with tab1:
    st.subheader("Paste URL and New Title Data")
    st.markdown("""
    Paste your data into the text area below. Each line should contain the canonical URL, followed by a separator, and then the new title.
    - **Default Separator:** Comma (`,`)
    - **Format:** `URL,New Title`
    """)
    
    separator = st.text_input("Separator Character", value=",", max_chars=1, help="The character that separates the URL from the new title on each line.")

    placeholder_text = (
        "https://sarahospitalityusa.com/blog/post-one,My First Awesome New Title\n"
        "https://sarahospitalityusa.com/blog/post-two,The Second Incredible Title\n"
        "https://sarahospitalityusa.com/blog/custom-hotel-reception-desks,Custom Hotel Reception Desks | Stylish Designs"
    )
    pasted_data = st.text_area("Paste your data here (one entry per line):", height=200, placeholder=placeholder_text)
    
    if pasted_data:
        try:
            # Use StringIO to treat the string as a file
            string_io = StringIO(pasted_data)
            # Read the data, assuming no header row
            df = pd.read_csv(string_io, sep=separator, header=None, names=['url', 'new_title'])
            # Clean up potential whitespace issues
            df['url'] = df['url'].str.strip()
            df['new_title'] = df['new_title'].str.strip()
            st.success(f"Successfully parsed {len(df)} rows. Here's a preview:")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"Could not parse the pasted data. Please check the format and separator. Error: {e}")
            df = None


with tab2:
    st.subheader("Upload a CSV File")
    st.markdown("""
    Upload a CSV file with two columns: `url` and `new_title`. The `url` column should contain the canonical URL of the page, and the `new_title` column should contain the desired new title.
    """)
    
    uploaded_csv = st.file_uploader("Upload your URL-to-Title CSV file", type="csv")
    
    if uploaded_csv:
        df = pd.read_csv(uploaded_csv)

    # Display a sample and provide a download template
    sample_data = {
        'url': [
            'https://sarahospitalityusa.com/blog/custom-hospitality-casegoods-tailored-solutions-for-unique-hotel-interiors',
            'https://sarahospitalityusa.com/blog/custom-hotel-reception-desks-designed-for-hospitality-excellence'
        ],
        'new_title': [
            'Custom Hospitality Casegoods for Unique Hotel Interiors',
            'Custom Hotel Reception Desks | Stylish & Functional Designs'
        ]
    }
    sample_df = pd.DataFrame(sample_data)
    st.markdown("**CSV Template Example:**")
    st.dataframe(sample_df)
    csv_template = sample_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV Template",
        data=csv_template,
        file_name='title_template.csv',
        mime='text/csv',
    )


# --- Step 2: Upload HTML Files ---
st.header("Step 2: Upload Your HTML Files")
uploaded_html_files = st.file_uploader(
    "Upload one or more HTML files",
    type=["html", "htm"],
    accept_multiple_files=True
)

# --- Step 3: Process and Download ---
st.header("Step 3: Process and Download Results")

# The process button is only active if we have a valid DataFrame AND uploaded HTML files
if st.button("🚀 Process Files", disabled=(df is None or not uploaded_html_files)):
    
    if 'url' not in df.columns or 'new_title' not in df.columns:
        st.error("Data must be resolved into 'url' and 'new_title' columns. Please check your input.")
    else:
        # Create a dictionary for fast lookups
        title_map = pd.Series(df.new_title.values, index=df.url).to_dict()
        
        processed_files = []
        log_messages = []
        
        st.info(f"Processing {len(uploaded_html_files)} HTML files...")
        progress_bar = st.progress(0)

        for i, file in enumerate(uploaded_html_files):
            filename = file.name
            try:
                content = file.getvalue().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')

                # Find the canonical URL in the HTML file
                canonical_link = soup.find('link', {'rel': 'canonical'})
                
                if canonical_link and canonical_link.get('href'):
                    url = canonical_link.get('href').strip() # Strip whitespace from URL
                    
                    # Check if this URL is in our map
                    if url in title_map:
                        new_title_text = title_map[url]
                        title_tag = soup.find('title')
                        
                        if title_tag:
                            old_title = title_tag.string if title_tag.string else "[Empty Title]"
                            title_tag.string = new_title_text
                            processed_files.append({'name': filename, 'content': str(soup)})
                            log_messages.append(f"✅ **{filename}**: Updated title from *'{old_title}'* to **'{new_title_text}'**.")
                        else:
                            log_messages.append(f"⚠️ **{filename}**: Found URL '{url}' but the file has no `<title>` tag to update.")
                    else:
                        log_messages.append(f"❌ **{filename}**: Canonical URL '{url}' not found in your mapping data. File skipped.")
                else:
                    log_messages.append(f"❌ **{filename}**: Could not find a `<link rel='canonical'>` tag. File skipped.")
            
            except Exception as e:
                log_messages.append(f"🔥 **{filename}**: An unexpected error occurred while processing this file. Error: {e}")


            progress_bar.progress((i + 1) / len(uploaded_html_files))

        # Display processing log
        with st.expander("📄 View Processing Log", expanded=True):
            for msg in log_messages:
                st.markdown(msg, unsafe_allow_html=True)
        
        # Create a zip file for download if any files were processed
        if processed_files:
            st.success(f"Successfully processed and modified {len(processed_files)} out of {len(uploaded_html_files)} files.")
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for p_file in processed_files:
                    zf.writestr(p_file['name'], p_file['content'].encode('utf-8'))
            
            zip_buffer.seek(0)
            st.download_button(
                label=f"📥 Download All {len(processed_files)} Modified HTML Files (.zip)",
                data=zip_buffer,
                file_name="modified_html_files.zip",
                mime="application/zip"
            )
        else:
            st.warning("No files were modified. Please check the logs above for details.")

st.markdown("---")
st.markdown("Developed with ❤️ by an AI Assistant")
