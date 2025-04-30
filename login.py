# sign_in.py
import boto3
import streamlit as st
import cognito
from jose import jwt
import utils
import pandas as pd
import base64
from io import BytesIO
import gzip
from time import sleep


AWS_ACCESS_KEY_ID = st.secrets["cognitoClient"]["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["cognitoClient"]["AWS_SECRET_ACCESS_KEY"]

# Create Cognito client
cognito_idp_client = boto3.client('cognito-idp',
                                  region_name='us-east-1',
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

user_pool_id = st.secrets["cognitoClient"]["user_pool_id"]
client_id = st.secrets["cognitoClient"]["client_id"]

cogauth = cognito.CognitoIdentityProviderWrapper(cognito_idp_client, user_pool_id, client_id)

def login():
    # Allow access to success page without authentication
    query_params = st.query_params
    page = query_params.get('page', [''])[0]

    if page == 'success':
        return False 

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "need_new_password" not in st.session_state:
        st.session_state.need_new_password = False
    if "login_failed" not in st.session_state:
        st.session_state.login_failed = False


    if not st.session_state.authenticated and not st.session_state.need_new_password:
        st.title("Please Log In")
        with st.form("login_form", clear_on_submit=True):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Log In")

            if submit_button:

                try:
                    response = cogauth.sign_in_user(email, password)
                    if response["status"] == "AUTHENTICATED":
                        # ✅ Successful normal login
                        st.session_state['coi_email'] = email
                        st.session_state.access_token = response["access_token"]
                        st.session_state.authenticated = True
                        decoded_access_token = jwt.get_unverified_claims(st.session_state["access_token"])
                        coi_uid = decoded_access_token["username"]
                        st.session_state["coi_uid"] = coi_uid
                        st.session_state.login_failed = False 
                        get_coi_data()
                        st.rerun()
                    elif response["status"] == "NEW_PASSWORD_REQUIRED":
                        # ⚠️ Need to set new password
                        st.session_state.need_new_password = True
                        st.session_state.cognito_session = response["session"]
                        st.session_state.cognito_email = email
                        st.session_state['coi_email'] = email
                        st.warning("You must set a new password before continuing.")

                except Exception as e:
                    st.error("Login failed")
                    st.session_state.login_failed = True
                    



    # If user needs to set a new password
    if st.session_state.need_new_password:
        st.title("Set New Password")
        with st.form("new_password_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_new_password = st.text_input("Confirm New Password", type="password")
            submit_new_password = st.form_submit_button("Submit New Password")

            if submit_new_password:
                if new_password != confirm_new_password:
                    st.error("Passwords do not match!")
                else:
                    try:
                        # Call a new function to complete the NEW_PASSWORD_REQUIRED challenge
                        response = cogauth.respond_to_new_password_challenge(
                            st.session_state.cognito_email,
                            new_password,
                            st.session_state.cognito_session
                        )
                        st.session_state.jwt = response["AuthenticationResult"]["AccessToken"]
                        st.success("Password reset successful! You can now log in with your new password.")
                        sleep(3)
                        st.session_state.authenticated = False
                        st.session_state.need_new_password = False
                        st.rerun()

                    except Exception as e:
                        st.error(f"Failed to set new password: {str(e)}")
                        logout()
                        
    #================================================== Handle Forgot Password =======================================
    # Show "Forgot Password?" only if login failed
    if st.session_state.login_failed:
        if st.button("Forgot Password?"):
            st.session_state.show_forgot_password = True


    if st.session_state.get("show_forgot_password"):
        st.title("Reset Your Password")
        with st.form("forgot_form"):
            forgot_email = st.text_input("Enter your email")
            submit_forgot = st.form_submit_button("Send Reset Code")

            if submit_forgot:
                url = "https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/forgot-password"
                payload = {"email": forgot_email}
                try:
                    response = utils.safe_api_post(url, payload)
                    if response.status_code == 200:
                        st.success("A verification code was sent to your email.")
                        st.session_state.reset_email = forgot_email
                        st.session_state.code_sent = True
                    else:
                        st.error(response.json().get("message", "Failed to send reset code."))
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Reset Password Form
    if st.session_state.get("code_sent"):
        st.title("Enter Verification Code and New Password")
        with st.form("reset_password_form"):
            reset_code = st.text_input("Verification Code")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_reset = st.form_submit_button("Reset Password")

            if submit_reset:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    url = "https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/reset-password"
                    payload = {
                        "email": st.session_state.reset_email,
                        "code": reset_code,
                        "new_password": new_password
                    }
                    try:
                        response = utils.safe_api_post(url, payload)
                        if response.status_code == 200:
                            st.success("Password reset successful. You can now log in.")
                            st.session_state.show_forgot_password = False
                            st.session_state.code_sent = False
                            sleep(3)
                            st.rerun()
                        else:
                            st.error(response.json().get("message", "Password reset failed."))
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        logout()


    return st.session_state.authenticated

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


    st.rerun()

st.cache_data()
def get_coi_data(counter=None):
    url = 'https://kbeopzaocc.execute-api.us-east-1.amazonaws.com/prod/get-user-data'
    response = utils.safe_api_post(url, {})
    # st.write(response)
    if response.status_code == 200:
        data = response.json()
        # st.write(data)
        access_on = data['access_on']['BOOL']
        # st.write(f"Access on: {access_on}")
        if not access_on:
            st.error("Your access is blocked. Please contact support.")
            st.stop()
        else:

            access_on = data['access_on']
            st.session_state['access_on'] = access_on
            if st.session_state['access_on']:
            
                price_qty_data_df = pd.DataFrame(eval(data['price_qty_data']['S']))
                
                current_token_balance = data['current_token_balance']['N']

                encoded_client_df = data['client_df']

                coi_email_hash = data['coi_email_hash']

                encoded_default_banks_df = data['default_banks_df']

            else:
                st.warning("Please contact Eureka Partners Support at contact@eurekapartners.com")
                sleep(5)
                st.stop()


            # Step 1: Base64 decode
            if encoded_client_df:
                compressed_bytes = base64.b64decode(encoded_client_df)

                # Step 2: Gzip decompress
                with gzip.GzipFile(fileobj=BytesIO(compressed_bytes), mode='rb') as gz:
                    parquet_bytes = gz.read()
                buffer = BytesIO(parquet_bytes)
                client_df = pd.read_parquet(buffer)
            else:
                client_df = pd.DataFrame()

            if encoded_default_banks_df:
                parquet_bytes = base64.b64decode(encoded_default_banks_df)
                buffer = BytesIO(parquet_bytes)
                default_banks_df = pd.read_parquet(buffer)
            else:
                default_banks_df = pd.DataFrame()

            st.session_state["current_token_balance"] = current_token_balance
            st.session_state["price_qty_data_df"] = price_qty_data_df
            st.session_state["client_df"] = client_df
            st.session_state["coi_email_hash"] = coi_email_hash
            st.session_state["default_banks_df"] = default_banks_df



        return current_token_balance, price_qty_data_df, client_df, coi_email_hash, default_banks_df
    else:
        st.warning("Please contact Eureka Partnersa Support at contact@eurekapartners.com")
        logout()
        return None, None, None, None
    
        
            