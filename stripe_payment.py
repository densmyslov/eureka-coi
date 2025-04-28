# stp.py

import stripe
import streamlit as st

STRIPE_SECRET_KEY = st.secrets['STRIPE']['STRIPE_SECRET_KEY']
stripe.api_key = STRIPE_SECRET_KEY

SUCCESS_URL = st.secrets['STRIPE']['SUCCESS_URL']
CANCEL_URL = st.secrets['STRIPE']['CANCEL_URL']

def create_checkout_session():
    product_currency = "USD"
    product_name = "Eureka Tokens"
    product_price_cents = st.session_state['amount_to_pay'] * 100  # Convert to cents

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': product_currency,
                        'product_data': {
                            'name': product_name,
                        },
                        'unit_amount': product_price_cents,
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
            automatic_tax={'enabled': False},
            metadata={
                'order_id': '12345',
                'coi_id': st.session_state['coi_uid'],
                'coi_email': st.session_state['coi_email'],
                'email_hash': st.session_state['coi_email_hash'],
                'num_tokens': st.session_state['tokens_to_buy'],
                'amount_total': st.session_state['amount_to_pay'],
                'transaction_type': 'Token purchase'
            }
        )

        return checkout_session.url

    except stripe.error.StripeError as e:
        st.error(f"Error creating Stripe session: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
