# dashboard.py
import streamlit as st
import login
import pandas as pd
from PIL import Image
import base64
from io import BytesIO
import io
import requests
from jose import jwt
from time import sleep
import gzip
import json
from PyPDF2 import PdfMerger
import utils
import stripe_payment as stp

st.set_page_config(page_title="Eureka Partners Client Dashboard", layout="wide")

utils.show_title()

#====================================BUTTON COLOR======================
st.markdown("""
            <style>
            div.stButton > button:first-child {
                background-color: #4CAF50;  /* Green */
                color: white;
            }
            </style>
            """, unsafe_allow_html=True)

#====================================================================================================================
# STRIPE REDIRECT PAGE
#====================================================================================================================


query_params = st.query_params
page = query_params.get('page', [''])

if page == "success":
    utils.show_success_page()
    st.stop()

#====================================================================================================================
# INITIALIZE SESSION STATES
#====================================================================================================================
if 'access_on' not in st.session_state:
    st.session_state.access_on = 'False'

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "counter" not in st.session_state:
        st.session_state.counter = 0
#====================================================================================================================
#   AUTHENTICATION
#====================================================================================================================

    
authenticated = st.session_state.authenticated


# Run login check first
cols = st.columns((1,2,1))

if not st.session_state.authenticated:

    with cols[0]:
        authenticated = login.login()



#====================================================================================================================
#   LOGOUT
#====================================================================================================================


if authenticated and st.session_state.access_on:
    #-----------------------------Logout-----------------------------------
    # when btn Logout is clicked, all st.session keys are erased
    # since 'authorized' key is erased too, app returnes to unauthenticated state 
    if st.sidebar.button("Logout"):
        login.logout()

  
    st.sidebar.success(f"You are logged in as {st.session_state['coi_email']}.")


        
    # ✅ Only show dashboard if authenticated
    st.success("Welcome to the Dashboard!")

#=======================================================================================================================================
# REFRESH APP
# current_token_balance, price_qty_data_df, client_df, coi_email_hash
#=======================================================================================================================================


    def increment_counter():
        st.session_state.counter += 1

    if st.sidebar.button("Refresh"):
        increment_counter()
        # af.load_coi_table.clear()
        current_token_balance, price_qty_data_df, client_df, coi_email_hash, default_banks_df = login.get_coi_data(counter=st.session_state['counter'])
        st.session_state.current_token_balance = current_token_balance
        st.session_state.price_qty_data_df = price_qty_data_df
        st.session_state.client_df = client_df
        st.session_state.coi_email_hash = coi_email_hash
        st.session_state.default_banks_df = default_banks_df
        st.rerun()

    # docs_df is df showing client documents in client's subfolder (client_email_hash)
    if "docs_df" not in st.session_state or st.session_state.docs_df is None:
        st.session_state.docs_df = pd.DataFrame()

#========================================GET COI DATA===========================================       
    # these values are stored by login.get_coi_data() which is part of login.login()
    current_token_balance = int(st.session_state.get("current_token_balance"))
    price_qty_data_df = st.session_state.get("price_qty_data_df")
    client_df = st.session_state.get("client_df")
    coi_email_hash = st.session_state.get("coi_email_hash")







#=================================================================================
# CREATE NEW CLIENT
#=================================================================================
    auth_col, balance_col, price_col = st.columns(3)


    with auth_col:
        st.markdown("<h2 style='text-align: center'>Add New Client</h2>", unsafe_allow_html=True)
        if current_token_balance > 0:
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
                                    "coi_email": st.session_state['coi_email'],
                                    "docs_submitted": "False"
                                }
                                        
                        url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/create-new-client'
                        response = utils.safe_api_post(url, payload)
                        if response.status_code == 200:
                            st.success("Client added successfully!")
                            # update COI data
                            current_token_balance, price_qty_data_df, client_df, coi_email_hash = login.get_coi_data()
                            st.session_state["current_token_balance"] = current_token_balance
                            st.session_state["price_qty_data_df"] = price_qty_data_df
                            st.session_state["client_df"] = client_df
                            st.session_state["coi_email_hash"] = coi_email_hash
                            sleep(3)
                            st.rerun()
        else:
            st.warning("You need to buy tokens to add new clients")
            
#=================================================================================
# SHOW TOKEN BALANCE
#=================================================================================
    with balance_col:
        st.markdown("<h2 style='text-align: center'>Token Balance</h2>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center'>{current_token_balance}</h3>", unsafe_allow_html=True)

#=================================================================================
# BUY TOKENS
#=================================================================================
    with price_col:
        st.markdown("<h2 style='text-align: left'>Buy Tokens</h2>", unsafe_allow_html=True)
        st.dataframe(price_qty_data_df)
        st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
        
        tokens_to_buy = st.radio(
            "Buy tokens", price_qty_data_df['Qty'],
            horizontal=True,
            label_visibility="visible"
        )
        
        if tokens_to_buy:
            st.session_state["tokens_to_buy"] = tokens_to_buy
            amount_to_pay = utils.calculate_amount_to_pay()
            st.metric(label="Amount to Pay", value=amount_to_pay)

            # stp.pay_with_stripe()
            checkout_url = stp.create_checkout_session()
            if checkout_url:
                # Display the payment button
                st.markdown("""
                    <div style='text-align: center; margin-top: 20px;'>
                        <a href="{0}" target="_blank">
                            <button style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                Proceed to Payment
                            </button>
                        </a>
                    </div>
                """.format(checkout_url), unsafe_allow_html=True)

#=====================================================================================================
                                        # SEE CLIENTS
#=====================================================================================================
    st.header("👥 Your Clients")

    with st.expander("Expand to see Your Clients"):
        if client_df.empty:
            st.warning("You did not create any clients yet.")
            email_hash = None
            first_name = ""
            last_name = ""
            email = ""
        else:
            # st.dataframe(client_df)
            email_hash, first_name, last_name, email = utils.render_selector(client_df)


#=====================================================================================================
                                        # DOCUMENTS
#=====================================================================================================


#----------------------------------------SUBMIT DOCUMENTS--------------------------------------------
    st.header("📝 Client Documents")

    with st.expander("Expand to Submit Client Documents"):

        st.info("Select a client in Your Clients section above. Upload each required document individually. Supported formats: PDF, JPG, PNG.")
        st.header("📂 Upload Required Documents")
        st.markdown(
            f"<span style='color:green;'>You will upload documents of "
            f"<span style='color:red;'>{first_name} {last_name}</span> "
            f"with email <span style='color:blue;'>{email}</span></span>",
            unsafe_allow_html=True
        )

        col_submit, _, col_questionnaire = st.columns(3)
        with col_submit:
            if email_hash:
                utils.fetch_docs_df(email_hash)



                doc_types = ["EIN Letter", "Articles of Incorporation", "ID - front", "ID - back", "Questionnaire"]
                doc_type = st.selectbox("Select Document Type", doc_types)

                file_obj = st.file_uploader(f"Upload {doc_type}", type=["pdf", "jpg", "png"], key="file_upload")

                if file_obj is not None:
                    st.session_state["last_uploaded_file"] = {
                        "doc_type": doc_type,
                        "file_name": file_obj.name,
                        "file_data": base64.b64encode(file_obj.read()).decode("utf-8")
                    }

                    if st.button("Submit Document"):
                        uploaded = st.session_state.get("last_uploaded_file")
                        if uploaded is None:
                            st.error("No document selected.")
                            st.stop()

                        payload = {
                            "doc_type": uploaded["doc_type"],
                            "file_name": uploaded["file_name"],
                            "file_data": uploaded["file_data"],
                            "client_email_hash": email_hash,
                            "coi_email_hash": st.session_state["coi_email_hash"],
                            "coi_uid": st.session_state["coi_uid"]
                        }
                        utils.submit_document(payload)

        with col_questionnaire:

            bank_name = st.selectbox("Select Bank", st.session_state.default_banks_df['name'])
            st.write(f"You will submit a questionnaire for {bank_name}")
            q_obj = st.file_uploader(f"Upload bank questionnaire for {bank_name}", type=["pdf"],key="questionnaire_upload")
            if q_obj is not None:
                st.session_state["last_uploaded_questionnaire"] = {
                    "file_name": f"{bank_name} Questionnaire.pdf",
                    "file_data": base64.b64encode(q_obj.read()).decode("utf-8"),
                    "doc_type":"Questionnaire",
                    "bank_name": bank_name
                }
                if st.button("Submit Document", key='submit_questionnaire'):
                    uploaded_q = st.session_state.get("last_uploaded_questionnaire")
                    if uploaded_q is None:
                        st.error("No questionnaire selected.")
                        st.stop()

                    payload = {
                        "doc_type": uploaded_q["doc_type"],
                        "file_name": uploaded_q["file_name"],
                        "file_data": uploaded_q["file_data"],
                        "bank_name": uploaded_q["bank_name"],
                        "client_email_hash": email_hash,
                        "coi_email_hash": st.session_state["coi_email_hash"],
                        "coi_uid": st.session_state["coi_uid"]
                    }

                    utils.submit_document(payload)


           
#----------------------------------------VIEW SUBMITTED DOCUMENTS--------------------------------------------
    with st.expander("Expand to View Submitted Documents"):
    
            if st.session_state.get("docs_df").empty:
                st.warning("You did not submit any documents yet.")
            else:


                if (
                        "docs_df" in st.session_state
                        and not st.session_state["docs_df"].empty
                        and {"doc_type", "key"}.issubset(st.session_state["docs_df"].columns)
                    ):
                    docs_df = st.session_state["docs_df"]

                    # Show the uploaded document status
                    doc_types_uploaded = docs_df["doc_type"].str.lower().dropna().unique()
                    doc_types_list = [doc_type.lower() in doc_types_uploaded for doc_type in doc_types]
                    docs_uploaded_df = pd.DataFrame({"doc_type": doc_types, "available": doc_types_list})


                    avail_doc_types = docs_uploaded_df.query("available == True")["doc_type"].tolist()

                    # Show images
                    images = utils.get_images_to_show(docs_df, email_hash, avail_doc_types)
                    utils.display_images_in_tabs(images)

            
                    

    # Final Package Download
    #----------------------------------------DOWNLOAD FINAL COMBINED PDF--------------------------------------------
    st.header("📥 Final Package")
    if st.button("Download Final Combined PDF"):
        original_docs = []
        original_files_dict = st.session_state['docs_df'].query("doc_class=='original'").set_index('doc_type')['key'].to_dict()
        api_url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/get-original-file'


        for doc_type, key in original_files_dict.items():
            payload = {"key": key}
            response = utils.safe_api_post(api_url, payload)
            print(response.status_code)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                file_bytes = io.BytesIO(response.content)

                # Convert images to PDF if needed
                if content_type.startswith('image/'):
                    img = Image.open(file_bytes).convert("RGB")
                    img_pdf = io.BytesIO()
                    img.save(img_pdf, format="PDF")
                    img_pdf.seek(0)
                    original_docs.append(img_pdf)
                elif content_type == 'application/pdf':
                    original_docs.append(file_bytes)
            else:
                st.warning(f"Failed to fetch {doc_type} from API.")


        # Merge all PDFs
        if original_docs:
            merger = PdfMerger()
            for pdf in original_docs:
                merger.append(pdf)

            final_pdf = io.BytesIO()
            merger.write(final_pdf)
            merger.close()
            final_pdf.seek(0)

            st.download_button(
                label="📄 Download Combined PDF",
                data=final_pdf,
                file_name="combined_documents.pdf",
                mime="application/pdf"
            )
        else:
            st.error("No documents available to combine.")





