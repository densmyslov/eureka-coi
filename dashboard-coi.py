# dashboard.py
import streamlit as st
import login
import pandas as pd
from PIL import Image
import base64
from io import BytesIO
import requests
from jose import jwt
import base64
from time import sleep
import gzip
import json
import utils

st.set_page_config(page_title="Eureka Partners Client Dashboard", layout="wide")
# Your dashboard code here
image = Image.open("assets/eureka_logo.jpeg")
buffered = BytesIO()
image.save(buffered, format="PNG")
img_b64 = base64.b64encode(buffered.getvalue()).decode()
st.markdown(f"""
    <div style="display: flex; align-items: center;">
        <img src="data:image/png;base64,{img_b64}" width="40" style="margin-right: 10px;">
        <h1 style="margin: 0;">Eureka Partners Client Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

#====================================BUTTON COLOR======================
st.markdown("""
            <style>
            div.stButton > button:first-child {
                background-color: #4CAF50;  /* Green */
                color: white;
            }
            </style>
            """, unsafe_allow_html=True)

#========================================AUTHENTICATION==========================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


    
authenticated = st.session_state.authenticated


# Run login check first
cols = st.columns((1,2,1))

if not st.session_state.authenticated:

    with cols[0]:
        authenticated = login.login()

if authenticated:
    #-----------------------------Logout-----------------------------------
    # when btn Logout is clicked, all st.session keys are erased
    # since 'authorized' key is erased too, app returnes to unauthenticated state 
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        

        st.rerun() # makes sure that app shows login form login.login()



        
    # ✅ Only show dashboard if authenticated
    st.success("Welcome to the Dashboard!")

    # docs_df is df showing client documents in client's subfolder (client_email_hash)
    if "docs_df" not in st.session_state or st.session_state.docs_df is None:
        st.session_state.docs_df = pd.DataFrame()

#========================================GET COI DATA===========================================       
    # these values are stored by login.get_coi_data() which is part of login.login()
    current_token_balance = st.session_state.get("current_token_balance")
    price_qty_data_df = st.session_state.get("price_qty_data_df")
    client_df = st.session_state.get("client_df")
    coi_email_hash = st.session_state.get("coi_email_hash")


    # Simulated values
    monthly_performance = [2, 5, 3, 7, 6, 9]



#==========================================CREATE NEW CLIENT=======================================
    auth_col, balance_col, price_col = st.columns(3)

    with auth_col:
        st.markdown("<h2 style='text-align: center'>Create Client</h2>", unsafe_allow_html=True)
        with st.expander("Fill out new client form"):
        
                with st.form("create_new_client_form", clear_on_submit=True):
                    first_name = st.text_input("First Name")
                    last_name = st.text_input("Last Name")
                    email = st.text_input("Email")
                    phone_number = st.text_input("Phone Number")
                    address = st.text_input("Address")
                    city = st.text_input("City")
                    state = st.text_input("State")
                    zip_code = st.text_input("Zip Code")
                    company_name = st.text_input("Company Name")

                    submitted = st.form_submit_button("Enter")
                    if submitted:
                        if any(value is None for value in [first_name, last_name, email]):
                            st.error("Email and First/Last Name cannot be empty.")
                            st.stop()
                        payload = {
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "phone_number": phone_number,
                                    "address": address,
                                    "city": city,
                                    "state": state,
                                    "zip_code": zip_code,
                                    "company_name": company_name,
                                    "coi_uid": st.session_state["coi_uid"],
                                    "coi_email_hash": st.session_state["coi_email_hash"],
                                    "docs_submitted": "False"
                                }
                                        
                        url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/create-new-client'
                        response = utils.safe_api_post(url, payload)
                        if response.status_code == 200:
                            st.success("Client created successfully!")
                            # update COI data
                            current_token_balance, price_qty_data_df, client_df, coi_email_hash = login.get_coi_data()
                            st.session_state["current_token_balance"] = current_token_balance
                            st.session_state["price_qty_data_df"] = price_qty_data_df
                            st.session_state["client_df"] = client_df
                            st.session_state["coi_email_hash"] = coi_email_hash
                            sleep(3)
                            st.rerun()
            

    with balance_col:
        st.markdown("<h2 style='text-align: center'>Token Balance</h2>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center'>{current_token_balance}</h3>", unsafe_allow_html=True)

    with price_col:
        st.markdown("<h2 style='text-align: left'>Token Pricing</h2>", unsafe_allow_html=True)
        st.dataframe(price_qty_data_df)
        st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
        token_to_buy = st.radio(
            "Buy tokens", price_qty_data_df['Qty'],
            horizontal=True,
            label_visibility="visible"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Center the button as well
        st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
        if st.button("Buy with Stripe"):
            st.info(f"Redirecting to Stripe for {token_to_buy} token(s)...")
        st.markdown("</div>", unsafe_allow_html=True)

    # Client df
    with st.expander("See Your Clients"):
        if client_df.empty:
            st.warning("You did not create any clients yet.")
        else:
            # st.dataframe(client_df)
            email_hash, first_name, last_name, email = utils.render_selector(client_df)


#=====================================================================================================
                                        # DOCUMENTS
#=====================================================================================================
    # Credit Submission
    st.header("📝 Client Documents")
    
#----------------------------------------SUBMIT DOCUMENTS--------------------------------------------
    with st.expander("Submit Client Documents"):
        st.markdown("Select client from the table below:")

        col_submit, col_view = st.columns(2)
        with col_submit:

            if email_hash :
                url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/submit-docs'
                payload = {
                    "message": "return docs_df",
                    "client_email_hash": email_hash,
                    "coi_email_hash": st.session_state["coi_email_hash"]
                }
                response = utils.safe_api_post(url, payload)
                if response.status_code == 200:

                    response_data = response.json()
                    if 'message' in response_data and response_data['message'] == 'docs_df does not exist':
                        
                    
                        docs_df = pd.DataFrame()
                        st.session_state["docs_df"] = docs_df
                    else:
                

                        # 2. Get the 'body' field, which contains a JSON *string*
                        body_string = response_data.get('body')
                        docs_df_parquet_base64 = response_data.get('docs_df_parquet_base64')
                        docs_df = utils.load_df_from_base64_parquet(docs_df_parquet_base64)
                        st.session_state["docs_df"] = docs_df



                st.header("📂 Upload Required Documents")
                st.markdown(
                                f"<span style='color:green;'>You will upload documents of <span style='color:red;'>{first_name}</span> <span style='color:red;'>{last_name}</span> with email <span style='color:blue;'>{email}</span></span>",
                                unsafe_allow_html=True
                            )
                
                
                # Let the user choose which document type to upload.
                doc_types = ["EIN Letter", 
                            "Articles of Incorporation", 
                            "ID - front",
                            "ID - back",
                            "Questionnaire"]
                
                doc_type = st.selectbox("Select Document Type", doc_types)
                # Provide a file uploader for the selected document type.
                file_obj = st.file_uploader(f"Upload {doc_type}", type=["pdf", "jpg", "png"])
                if file_obj is not None:
                    # Read and encode the file content to Base64.
                    encoded_file = base64.b64encode(file_obj.read()).decode("utf-8")
                    
                    # Prepare payload with document type and file details.
                    payload = {
                                "doc_type": doc_type,
                                "file_name": file_obj.name,
                                "file_data": encoded_file,
                                "client_email_hash": email_hash,
                                "coi_email_hash": st.session_state["coi_email_hash"],
                                "coi_uid": st.session_state["coi_uid"]
                            }
        
                    # Send the payload to the API.

                    if st.button("Submit Document"):
                        
                        url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/submit-docs'
                        response = utils.safe_api_post(url, payload)

                        if response is not None and response.status_code == 200:
                            st.success("Document submitted successfully!")
                            try:
                                # 1. Parse the main JSON response from API Gateway/Lambda A
                                response_data = response.json()

                                # 2. Get the 'body' field, which contains a JSON *string*
                                body_string = response_data.get('body')
                                docs_df_parquet_base64 = response_data.get('docs_df_parquet_base64')
                                st.session_state.docs_df = utils.load_df_from_base64_parquet(docs_df_parquet_base64)
                                

                                

                            except json.JSONDecodeError as e:
                                st.error(f"Failed to decode JSON response from API: {e}")
                                st.text(f"Raw response text: {response.text}")
                            except KeyError as e:
                                st.error(f"Missing expected key in API response: {e}")
                                st.json(response.json()) # Show the structure received
                            except Exception as e:
                                st.error(f"An error occurred processing the response: {e}")

                        elif response is not None:
                            st.error(f"API call failed with status code {response.status_code}")
                            try:
                                st.json(response.json()) # Show error details if available
                            except json.JSONDecodeError:
                                st.text(f"Raw error response: {response.text}")
                        else:
                            st.error("API call failed (no response received).")
                        
#----------------------------------------VIEW SUBMITTED DOCUMENTS--------------------------------------------
    with st.expander("View Submitted Documents"):
    
            if st.session_state.get("docs_df").empty:
                st.warning("You did not submit any documents yet.")
            else:
                st.cache_data()
                def get_images_to_show(docs_df, email_hash, avail_doc_types, counter=None):
                    images = {}
                    doc_key_dict = docs_df.query("doc_type==@avail_doc_types").drop_duplicates(subset=["doc_type"])[['doc_type', 'key']].set_index("doc_type").to_dict()['key']

                    for doc_type, key in doc_key_dict.items():

                        payload = {"key": key}
                        url = "https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/get-image"
                        response =  utils.safe_api_post(url, payload)

                        if response.status_code == 200:
                            data = response.json()
                            base64_image = data.get("image")
                            # decode and open as PIL
                            image_bytes = base64.b64decode(base64_image)
                            images[doc_type] =  Image.open(BytesIO(image_bytes))
                    return images
                


                            
                

                
                doc_types_uploaded = st.session_state["docs_df"].dropna(subset=["doc_type"])["doc_type"].unique()
                doc_types_list = [True if i in doc_types_uploaded else False for i in doc_types]
                docs_uploaded_df = pd.DataFrame({"doc_type": doc_types, "available": doc_types_list})
                st.dataframe(docs_uploaded_df)

                avail_doc_types = docs_uploaded_df.query("available==True").doc_type.tolist()
                images = get_images_to_show(docs_df, email_hash, avail_doc_types, counter=None)

        

                def display_images_in_tabs(image_dict):
                    """
                    Display images from a dictionary where keys are tab names and values are PIL images.
                    """
                    tab_labels = list(image_dict.keys())
                    tabs = st.tabs(tab_labels)

                    for tab, key in zip(tabs, tab_labels):
                        with tab:
                            st.image(image_dict[key], caption=key, width = 400)
                display_images_in_tabs(images)

            




            # # Create a DataFrame copy and insert the selection column with current state.
            # df_with_select = docs_uploaded_df.copy()
            # df_with_select.insert(0, "Select", docs_uploaded_df["available"])
            
            # # Display the data editor.
            # edited_df = st.data_editor(
            #     df_with_select,
            #     hide_index=True,
            #     column_config={"Select": st.column_config.CheckboxColumn(required=False)},
            #     disabled=docs_uploaded_df.columns.tolist(),
            #     use_container_width=True,
            # )

            
            # selected_doc_types = edited_df[edited_df["Select"] == True]["doc_type"].tolist()
            

            # if st.button(":blue[Show selected files]"):
            #     if len(selected_doc_types) == 0:
            #         st.error("You have not selected any files")
            #         st.stop()
                
            #     for doc_type in selected_doc_types:
            #         # try:
            #             images = []
            #             df_to_show = st.session_state["docs_df"].copy()
            #             df = df_to_show.query("doc_class=='images' & doc_type==@doc_type")
            #             st.dataframe(df)
            #             if not df.empty:
            #                 image = get_images_to_show(df, num_images = 1)
            #                 st.write(image)
            #                 if image:
            #                     images.append(image)
            #                 st.write(len(images))


            #                 # pil_images_to_show, byte_images_to_show = utils.get_images_to_show(gr)
                            

                    
            #         # except:
            #         #     st.warning("You did not submit any documents of this type yet.")
                
                    

    # Final Package Download
    st.header("📥 Final Package")
    if st.button("Download Final Combined PDF"):
        st.download_button("📄 Download PDF", b"Dummy PDF content", file_name="final_package.pdf")

    # Request Token Back
    st.header("⬅️ Token Return")
    denial_letter = st.file_uploader("Upload Denial Letter", type=["pdf"])
    if st.button("Request Token Back"):
        st.info("Token return requested!")

    # Progress Tracker
    st.header("📶 Client Progress")
    steps = ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
    progress = [0.2, 0.4, 0.6, 0.3, 0.8]
    for s, p in zip(steps, progress):
        st.write(s)
        st.progress(p)

    # Referral Tracker
    st.header("👥 Referral Tracker")
    st.metric("Clients Referred", 6)
    st.metric("Fees Earned", "$1,250")
    st.bar_chart(pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "Referrals": monthly_performance
    }).set_index("Month"))


