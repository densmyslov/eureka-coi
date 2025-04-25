import os
import streamlit as st
import stripe


STRIPE_SECRET_KEY=st.secrets['STRIPE']['STRIPE_SECRET_KEY']
stripe.api_key = STRIPE_SECRET_KEY

SUCCESS_URL = st.secrets['STRIPE']['SUCCESS_URL']
CANCEL_URL = st.secrets['STRIPE']['CANCEL_URL']



def pay_with_stripe():
    product_currency = "USD"
    product_name = "Eureka Tokens"
    product_price_cents = st.session_state['amount_to_pay'] * 100  # Convert to cents
    
    try:
        # 1) Create a Stripe Checkout Session
        #    Amount is inserted here automatically
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': product_currency,
                        'product_data': {
                            'name': product_name,
                            # Add more product details if needed: description, images
                        },
                        'unit_amount': product_price_cents, # Amount in cents
                    },
                    'quantity': 1,
                },
            ],
            mode='payment', # Use 'subscription' for recurring payments
            success_url=SUCCESS_URL + '?session_id={CHECKOUT_SESSION_ID}', # Include session ID for potential verification on success page
            cancel_url=CANCEL_URL,
            automatic_tax={'enabled': False},

            metadata={'order_id': '12345',
                      'coi_id': st.session_state['coi_uid'],
                      'coi_email': st.session_state['coi_email'],
                      'email_hash': st.session_state['coi_email_hash'],
                      'num_tokens': st.session_state['tokens_to_buy'],
                      'amount_total' : st.session_state['amount_to_pay'],
                      'transaction_type': 'Token purchase'
                      }
        )

        # 4) Redirect user to Stripe Checkout URL
        #    We use markdown to create a clickable link/button.
        #    Alternatively, for automatic redirect (might need careful handling in Streamlit):
        #    import streamlit.components.v1 as components
        #    components.html(f'<script>window.location.href = "{checkout_session.url}";</script>', height=0)

        checkout_url = checkout_session.url
        st.success("Click the link below to buy Eureka Tokens.")
        # Use Markdown for a styled link/button
        st.markdown(f"""
            <a href="{checkout_url}" target="_blank">
                <button style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Proceed to Payment
                </button>
            </a>
            """, unsafe_allow_html=True)
        # st.markdown(f"Or go to: {checkout_url}") # Provide the URL directly too

        # 5 & 6 happen on the Stripe page

    except stripe.error.StripeError as e:
        st.error(f"Error creating Stripe session: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
