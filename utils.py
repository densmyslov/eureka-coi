
import requests
import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import auth

# ==============================
#  HELPER FUNCTIONS
# ==============================

import base64
from io import BytesIO
from PIL import Image
import streamlit as st
import utils  # assuming safe_api_post lives here

def display_images_in_tabs(image_dict):
    """
    Display images from a dictionary where keys are tab names and values are PIL images.
    """
    tab_labels = list(image_dict.keys())
    tabs = st.tabs(tab_labels)

    for tab, key in zip(tabs, tab_labels):
        with tab:
            st.image(image_dict[key], caption=key, width = 400)

st.cache_data()
def get_images_to_show(docs_df, email_hash, avail_doc_types, counter=None):
    images = {}

    if "doc_type" not in docs_df.columns or "key" not in docs_df.columns:
        return images  # nothing to show yet

    filtered_df = docs_df[docs_df["doc_type"].isin(avail_doc_types)]
    doc_key_dict = (
        filtered_df.drop_duplicates(subset=["doc_type"])[["doc_type", "key"]]
        .set_index("doc_type")
        .to_dict()
        .get("key", {})
    )

    for doc_type, key in doc_key_dict.items():
        payload = {"key": key}
        url = "https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/get-image"
        response = utils.safe_api_post(url, payload)

        if response.status_code == 200:
            data = response.json()
            base64_image = data.get("image")
            image_bytes = base64.b64decode(base64_image)
            images[doc_type] = Image.open(BytesIO(image_bytes))

    return images


def _load_docs():
    email_hash = st.session_state["selected_client"]
    url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/submit-docs'
    resp = safe_api_post(url, {
        "message": "return docs_df",
        "client_email_hash": email_hash,
        "coi_email_hash": st.session_state["coi_email_hash"]
    })
    data = resp.json()
    st.session_state["docs_df"] = (
        pd.DataFrame() if data.get("message") == "docs_df does not exist"
        else load_df_from_base64_parquet(data["docs_df_parquet_base64"])
    )

@st.fragment
def render_selector(df: pd.DataFrame):
    """
    Render an interactive data editor fragment that allows the user to select a single row.

    Displays a DataFrame with an added "Select" column of checkboxes. Enforces that only one
    checkbox can be selected at a time. When exactly one row is selected, returns
    (client_email_hash, first_name, last_name, email); otherwise returns (None, None, None, None).

    Parameters:
        df (pd.DataFrame): Input DataFrame containing client data, including 'client_email_hash'.

    Returns:
        Tuple[str, str, str, str] or (None, None, None, None):
            The selected row's (client_email_hash, first_name, last_name, email) or Nones.
    """
    # Initialize or reset selection state
    if (
        "single_selection" not in st.session_state
        or st.session_state.single_selection is None
        or len(st.session_state.single_selection) != len(df)
    ):
        st.session_state.single_selection = [False] * len(df)

    # Prepare DataFrame with selection column
    df_with_select = df.copy()
    df_with_select.insert(0, "Select", st.session_state.single_selection)

    # Render the editable DataFrame
    edited_df = st.data_editor(
        df_with_select,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=False)},
        disabled=df.columns.tolist(),
        use_container_width=True,
    )

    # Capture updated selection
    new_selection = edited_df["Select"].tolist()

    # Handle changes: enforce single selection and rerun
    if new_selection != st.session_state.single_selection:
        if sum(new_selection) > 1:
            # Keep only the most recently toggled checkbox
            for i, (prev, curr) in enumerate(zip(st.session_state.single_selection, new_selection)):
                if not prev and curr:
                    updated = [False] * len(new_selection)
                    updated[i] = True
                    st.session_state.single_selection = updated
                    # Abort current run and rerun fragment/app
                    st.rerun()
                    return None, None, None, None
        else:
            # Update for single or no selection and rerun
            st.session_state.single_selection = new_selection
            # Abort current run and rerun fragment/app
            st.rerun()
            return None, None, None, None

    # If exactly one row is selected, return its details
    if sum(st.session_state.single_selection) == 1:
        idx = st.session_state.single_selection.index(True)
        row = df.iloc[idx]
        client_email_hash = row["client_email_hash"]
        first_name = row.get("first_name", "")
        last_name = row.get("last_name", "")
        email = row.get("email", "")
        return client_email_hash, first_name, last_name, email

    return None, None, None, None


def safe_api_post(url, data):
    def send_request():
        cognito_jwt_token = st.session_state.get("access_token")
        headers = {
            "Authorization": f"Bearer {cognito_jwt_token}",
            "Content-Type": "application/json"
        }
        return requests.post(url, json=data, headers=headers)

    auth.refresh_tokens_if_needed()
    response = send_request()

    if response.status_code == 401:
        auth.refresh_tokens_if_needed()
        response = send_request()

    return response

def load_df_from_base64_parquet(base64_string: str) -> pd.DataFrame | None:
    """
    Decodes a Base64 encoded Parquet string and loads it into a Pandas DataFrame.

    Args:
        base64_string: The Base64 encoded string containing Parquet data.

    Returns:
        A Pandas DataFrame if successful, None otherwise.
    """
    try:
        # Decode the Base64 string to get the Parquet bytes
        parquet_bytes = base64.b64decode(base64_string)

        # Create an in-memory buffer from the bytes
        buffer = BytesIO(parquet_bytes)

        # Read the Parquet data from the buffer
        # Requires 'pyarrow' or 'fastparquet' to be installed (pip install pyarrow)
        df = pd.read_parquet(buffer)
        
        return df
    except base64.binascii.Error as e:
        st.error(f"Error decoding Base64 string: {e}")
        return None
    except ImportError:
         st.error("Error: `pyarrow` library not found. Please install it (`pip install pyarrow`).")
         return None
    except Exception as e:
        # Catch potential errors during Parquet reading (e.g., corrupted data)
        st.error(f"Error reading Parquet data: {e}")
        return None

@st.fragment
def upload_document_fragment():
    st.header("\U0001F4C2 Upload Required Documents")
    st.markdown(f"<span style='color:green;'>You will upload documents for: <span style='color:red;'>{first_name} {last_name}</span> ({email})</span>", unsafe_allow_html=True)

    doc_types = ["EIN Letter", "Articles of Incorporation", "ID - front", "ID - back", "Questionnaire"]
    doc_type = st.selectbox("Select Document Type", doc_types)
    file_obj = st.file_uploader(f"Upload {doc_type}", type=["pdf", "jpg", "png"], key="file_upload")

    if file_obj:
        st.session_state["last_uploaded_file"] = {
            "doc_type": doc_type,
            "file_name": file_obj.name,
            "file_data": base64.b64encode(file_obj.read()).decode("utf-8")
        }

    if st.button("Submit Document"):
        uploaded = st.session_state.get("last_uploaded_file")
        if uploaded is None:
            st.error("No document selected.")
            return

        payload = {
            "doc_type": uploaded["doc_type"],
            "file_name": uploaded["file_name"],
            "file_data": uploaded["file_data"],
            "client_email_hash": email_hash,
            "coi_email_hash": st.session_state["coi_email_hash"],
            "coi_uid": st.session_state["coi_uid"]
        }

        url = "https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/submit-docs"
        response = utils.safe_api_post(url, payload)
        if response and response.status_code == 200:
            docs_df_parquet_base64 = response.json().get("docs_df_parquet_base64")
            st.session_state["docs_df"] = utils.load_df_from_base64_parquet(docs_df_parquet_base64)
            st.success("Document submitted successfully!")
        else:
            st.error("Failed to submit document.")