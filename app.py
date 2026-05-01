import streamlit as st
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import plotly.graph_objects as go
import stripe
from supabase import create_client, Client
from datetime import date

# ====================== CONFIG ======================
st.set_page_config(page_title="BlackScholes.ai", page_icon="📈", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

PRO_PRICE = 9.99

# ====================== BLACK-SCHOLES FUNCTIONS ======================
def black_scholes_price(S, K, T, r, sigma, option_type='call'):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0) if option_type == 'call' else max(K - S, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    price = black_scholes_price(S, K, T, r, sigma, option_type)
    if option_type == 'call':
        delta = norm.cdf(d1)
        theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1
        theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T)
    rho = K * T * np.exp(-r * T) * (norm.cdf(d2) if option_type == 'call' else norm.cdf(-d2))
    return {'Price': round(price, 4), 'Delta': round(delta, 4), 'Gamma': round(gamma, 4),
            'Theta (daily)': round(theta / 365, 4), 'Vega (per 1%)': round(vega / 100, 4),
            'Rho (per 1%)': round(rho / 100, 4)}

def implied_volatility(market_price, S, K, T, r, option_type='call'):
    def objective(sigma):
        return black_scholes_price(S, K, T, r, sigma, option_type) - market_price
    try:
        return brentq(objective, 1e-6, 5.0)
    except:
        return np.nan

# ====================== AUTH & USER FUNCTIONS ======================
def get_or_create_profile(user_id, email):
    # Get or create profile
    response = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if response.data:
        return response.data[0]
    # Create new profile
    profile = {"id": user_id, "email": email, "is_pro": False, "calculations_used": 0, "last_reset_date": str(date.today())}
    supabase.table("profiles").insert(profile).execute()
    return profile

def reset_daily_count_if_needed(profile):
    today = date.today()
    if profile["last_reset_date"] != str(today):
        profile["calculations_used"] = 0
        profile["last_reset_date"] = str(today)
        supabase.table("profiles").update({"calculations_used": 0, "last_reset_date": str(today)}).eq("id", profile["id"]).execute()
    return profile

# ====================== MAIN APP ======================
st.title("📊 BlackScholes.ai")
st.markdown("**The equation that built the multi-trillion dollar derivatives market — now in your browser.**")
st.latex(r"\frac{\partial V}{\partial t} + rS \frac{\partial V}{\partial S} + \frac{1}{2} \sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} - rV = 0")

# Session state
if "user" not in st.session_state:
    st.session_state.user = None
if "profile" not in st.session_state:
    st.session_state.profile = None

# Login / Signup
if not st.session_state.user:
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.profile = get_or_create_profile(res.user.id, res.user.email)
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account", use_container_width=True):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Please check your email to confirm (or use test mode).")
            except Exception as e:
                st.error(f"Signup failed: {e}")
else:
    # Logged in
    profile = st.session_state.profile
    profile = reset_daily_count_if_needed(profile)
    st.session_state.profile = profile

    with st.sidebar:
        st.header("👤 Account")
        st.write(f"**{profile['email']}**")
        if profile.get("is_pro"):
            st.success("✅ Pro Member — Unlimited calculations")
        else:
            st.info(f"Free Tier — {5 - profile['calculations_used']} calculations left today")
            if st.button("Upgrade to Pro — $9.99/mo", use_container_width=True):
                try:
                    checkout = stripe.checkout.Session.create(
                        payment_method_types=['card'],
                        line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'BlackScholes.ai Pro'}, 'unit_amount': int(PRO_PRICE * 100)}, 'quantity': 1}],
                        mode='payment',
                        success_url="https://black-scholes-mvp-rstarr37.streamlit.app/?success=true",
                        cancel_url="https://black-scholes-mvp-rstarr37.streamlit.app/",
                    )
                    st.link_button("Go to Stripe Checkout", checkout.url, use_container_width=True)
                except Exception as e:
                    st.error(f"Error: {e}")
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.profile = None
            st.rerun()

    # ==================== CALCULATOR ====================
    st.subheader("Options Calculator")
    col1, col2 = st.columns([1, 2])
    with col1:
        S = st.number_input("Current Stock Price (S) $", value=100.0, step=0.1)
        K = st.number_input("Strike Price (K) $", value=100.0, step=0.1)
        T = st.number_input("Time to Expiration (years)", value=1.0, step=0.01)
        r = st.number_input("Risk-Free Rate (%)", value=5.0, step=0.1) / 100
        sigma = st.number_input("Volatility (σ %)", value=20.0, step=0.1) / 100
        option_type = st.radio("Option Type", ["Call", "Put"])

    if st.button("🚀 Calculate", type="primary", use_container_width=True):
        if not profile.get("is_pro") and profile["calculations_used"] >= 5:
            st.error("You have reached your free daily limit. Upgrade to Pro for unlimited access!")
        else:
            greeks = black_scholes_greeks(S, K, T, r, sigma, option_type.lower())
            price = greeks['Price']
            
            st.success(f"**{option_type} Option Price: ${price:.2f}**")
            
            cols = st.columns(3)
            cols[0].metric("Delta", greeks['Delta'])
            cols[1].metric("Gamma", greeks['Gamma'])
            cols[2].metric("Theta (daily)", greeks['Theta (daily)'])
            cols = st.columns(3)
            cols[0].metric("Vega (per 1%)", greeks['Vega (per 1%)'])
            cols[1].metric("Rho (per 1%)", greeks['Rho (per 1%)'])
            cols[2].metric("Implied Volatility", f"{sigma*100:.1f}%")

            # Payoff chart
            st.subheader("Payoff at Expiration")
            prices = np.linspace(max(0, S-50), S+100, 200)
            payoff = np.maximum(prices - K, 0) if option_type == "Call" else np.maximum(K - prices, 0)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Payoff', line=dict(color='#00ff9d', width=3)))
            fig.update_layout(height=400, template="plotly_dark", xaxis_title="Stock Price at Expiration", yaxis_title="Profit/Loss")
            st.plotly_chart(fig, use_container_width=True)

            # Update usage count
            new_count = profile["calculations_used"] + 1
            supabase.table("profiles").update({"calculations_used": new_count}).eq("id", profile["id"]).execute()
            st.session_state.profile["calculations_used"] = new_count

    # Implied Volatility Solver
    st.divider()
    st.subheader("🔍 Implied Volatility Solver")
    market_price = st.number_input("Market Price of Option $", value=10.45, step=0.01)
    if st.button("Solve for Volatility", type="secondary"):
        iv = implied_volatility(market_price, S, K, T, r, option_type.lower())
        if not np.isnan(iv):
            st.success(f"**Implied Volatility: {iv*100:.2f}%**")
        else:
            st.error("Could not solve — try different inputs")

    st.caption("Professional version with login & usage tracking • Powered by Black-Scholes + Supabase")

# Success message from Stripe
if st.query_params.get("success"):
    st.success("✅ Payment successful! (Pro status will be activated automatically once we add webhooks — for now you can contact support or we can manually upgrade for testing)")
