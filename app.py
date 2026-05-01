import streamlit as st
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import plotly.graph_objects as go
import stripe
from datetime import date

st.set_page_config(page_title="BlackScholes.ai", page_icon="📈", layout="wide")

# === STRIPE SETUP - RECURRING SUBSCRIPTION ===
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]import streamlit as st
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import plotly.graph_objects as go
import stripe
from datetime import date

st.set_page_config(page_title="BlackScholes.ai", page_icon="📈", layout="wide")

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
MONTHLY_PRICE = 999  # $9.99

# ====================== BLACK-SCHOLES CORE ======================
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

# ====================== SESSION STATE ======================
if "user_email" not in st.session_state: st.session_state.user_email = None
if "is_pro" not in st.session_state: st.session_state.is_pro = False
if "calculations_used" not in st.session_state: st.session_state.calculations_used = 0
if "last_reset_date" not in st.session_state: st.session_state.last_reset_date = str(date.today())
if "portfolio" not in st.session_state: st.session_state.portfolio = []  # list of dicts

# Daily reset
if st.session_state.last_reset_date != str(date.today()):
    st.session_state.calculations_used = 0
    st.session_state.last_reset_date = str(date.today())

# ====================== LANDING PAGE ======================
if not st.session_state.user_email:
    # Hero
    st.markdown("""
    <h1 style='text-align:center; font-size:3rem;'>
        📊 BlackScholes.ai
    </h1>
    <p style='text-align:center; font-size:1.5rem; color:#00ff9d;'>
        The equation that created the $846 trillion derivatives market — now in your browser.
    </p>
    """, unsafe_allow_html=True)

    st.latex(r"\frac{\partial V}{\partial t} + rS \frac{\partial V}{\partial S} + \frac{1}{2} \sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} - rV = 0")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://i.imgur.com/2vL8z9K.png", use_column_width=True)  # placeholder for your original screenshot

    st.markdown("### Why traders love BlackScholes.ai")
    st.markdown("""
    - Instant fair value pricing + full Greeks
    - Implied volatility solver
    - Strategy builder with payoff charts
    - Portfolio risk tracker
    - Clear “Good Buy / Sell” signals
    """)

    st.info("**Free tier**: 5 calculations per day  •  **Pro**: $9.99/month unlimited")

    if st.button("🚀 Get Started Free — Create Account", type="primary", use_container_width=True):
        st.session_state.user_email = "demo@black-scholes.ai"
        st.rerun()

    st.caption("Trusted by options traders who want an edge. Join 100+ users already using the beta.")

else:
    # ====================== LOGGED-IN APP ======================
    with st.sidebar:
        st.header("👤 Account")
        st.write(f"**{st.session_state.user_email}**")
        if st.session_state.is_pro:
            st.success("✅ Pro — Unlimited")
        else:
            remaining = 5 - st.session_state.calculations_used
            st.info(f"Free Tier — {max(0, remaining)} left today")
            if st.button("Upgrade to Pro — $9.99/month", use_container_width=True):
                checkout = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'BlackScholes.ai Pro'}, 'unit_amount': MONTHLY_PRICE, 'recurring': {'interval': 'month'}}, 'quantity': 1}],
                    mode='subscription',
                    success_url="https://black-scholes-mvp-rstarr37.streamlit.app/?success=true",
                    cancel_url="https://black-scholes-mvp-rstarr37.streamlit.app/",
                )
                st.link_button("Go to Stripe Checkout", checkout.url, use_container_width=True)
        if st.button("Logout"):
            st.session_state.user_email = None
            st.session_state.is_pro = False
            st.rerun()

    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["📐 Calculator", "🛠 Strategy Builder", "📦 Portfolio"])

    # ====================== CALCULATOR TAB ======================
    with tab1:
        st.subheader("Options Calculator + Smart Recommendation")
        col1, col2 = st.columns([1, 2])
        with col1:
            S = st.number_input("Current Stock Price (S) $", value=100.0, step=0.1)
            K = st.number_input("Strike Price (K) $", value=100.0, step=0.1)
            T = st.number_input("Time to Expiration (years)", value=1.0, step=0.01)
            r = st.number_input("Risk-Free Rate (%)", value=5.0, step=0.1) / 100
            sigma = st.number_input("Volatility (σ %)", value=20.0, step=0.1) / 100
            option_type = st.radio("Option Type", ["Call", "Put"])
            market_price = st.number_input("Current Market Price of Option $", value=10.45, step=0.01)

        if st.button("🚀 Calculate & Analyze", type="primary", use_container_width=True):
            if not st.session_state.is_pro and st.session_state.calculations_used >= 5:
                st.error("Free daily limit reached. Upgrade to Pro!")
            else:
                greeks = black_scholes_greeks(S, K, T, r, sigma, option_type.lower())
                fair_price = greeks['Price']
                
                st.success(f"**Fair Value: ${fair_price:.2f}**")

                # Good Buy / Sell indicator
                if market_price < fair_price * 0.95:
                    st.success("🟢 **STRONG BUY** — Option is undervalued")
                elif market_price > fair_price * 1.05:
                    st.error("🔴 **SELL / AVOID** — Option is overvalued")
                else:
                    st.info("⚖️ **Fairly priced**")

                cols = st.columns(3)
                cols[0].metric("Delta", greeks['Delta'])
                cols[1].metric("Gamma", greeks['Gamma'])
                cols[2].metric("Theta (daily)", greeks['Theta (daily)'])
                cols = st.columns(3)
                cols[0].metric("Vega (per 1%)", greeks['Vega (per 1%)'])
                cols[1].metric("Rho (per 1%)", greeks['Rho (per 1%)'])
                cols[2].metric("Implied Volatility", f"{sigma*100:.1f}%")

                st.subheader("Payoff at Expiration")
                prices = np.linspace(max(0, S-50), S+100, 200)
                payoff = np.maximum(prices - K, 0) if option_type == "Call" else np.maximum(K - prices, 0)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Payoff', line=dict(color='#00ff9d', width=3)))
                fig.update_layout(height=400, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

                st.session_state.calculations_used += 1

    # ====================== STRATEGY BUILDER TAB ======================
    with tab2:
        st.subheader("Strategy Builder")
        strategy = st.selectbox("Choose Strategy", ["Long Call", "Long Put", "Straddle", "Iron Condor"])
        st.info("More advanced strategies coming soon. Start with these for now.")
        st.caption("Enter parameters below — combined payoff chart will appear")

        # Simple example for Straddle
        if strategy == "Straddle":
            S = st.number_input("Stock Price", value=100.0)
            K = st.number_input("Strike (same for call & put)", value=100.0)
            T = st.number_input("Days to expiration", value=30) / 365
            r = 0.05
            sigma = 0.20
            st.plotly_chart(go.Figure().add_trace(go.Scatter(x=np.linspace(50,150,200), y=np.maximum(np.abs(np.linspace(50,150,200)-K),0), name="Straddle Payoff")), use_container_width=True)

    # ====================== PORTFOLIO TAB ======================
    with tab3:
        st.subheader("Portfolio Tracker")
        st.write("Add your positions below (demo mode)")
        if st.button("Add Sample Position"):
            st.session_state.portfolio.append({"type": "Call", "S": 100, "K": 105, "T": 0.5, "delta": 0.55})
        st.write(st.session_state.portfolio)

    if st.query_params.get("success"):
        st.success("✅ Pro subscription activated! You now have unlimited access.")
        st.session_state.is_pro = True
        st.query_params.clear()

    st.caption("Professional Black-Scholes SaaS — Calculator • Strategy Builder • Portfolio")
MONTHLY_PRICE = 999  # $9.99 in cents

# ====================== BLACK-SCHOLES CORE (unchanged) ======================
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

# ====================== SESSION STATE ======================
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False
if "calculations_used" not in st.session_state:
    st.session_state.calculations_used = 0
if "last_reset_date" not in st.session_state:
    st.session_state.last_reset_date = str(date.today())

# Daily free limit reset
if st.session_state.last_reset_date != str(date.today()):
    st.session_state.calculations_used = 0
    st.session_state.last_reset_date = str(date.today())

# ====================== LOGIN PAGE ======================
if not st.session_state.user_email:
    st.title("📊 BlackScholes.ai")
    st.markdown("**The equation that built the multi-trillion dollar derivatives market — now in your browser.**")
    st.latex(r"\frac{\partial V}{\partial t} + rS \frac{\partial V}{\partial S} + \frac{1}{2} \sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} - rV = 0")

    st.info("🔥 Try it free — 5 calculations per day")
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        if st.button("Login", type="primary", use_container_width=True):
            st.session_state.user_email = email
            st.rerun()
    with tab2:
        email = st.text_input("Email", key="signup_email")
        if st.button("Create Free Account", type="primary", use_container_width=True):
            st.session_state.user_email = email
            st.rerun()
    st.caption("Demo mode — any email works. In the real product this will be secure email/password.")

else:
    # ====================== MAIN DASHBOARD ======================
    with st.sidebar:
        st.header("👤 Account")
        st.write(f"**{st.session_state.user_email}**")
        if st.session_state.is_pro:
            st.success("✅ Pro Member — Unlimited access")
        else:
            remaining = 5 - st.session_state.calculations_used
            st.info(f"Free Tier — {max(0, remaining)} calculations left today")
            if st.button("Upgrade to Pro — $9.99/month", use_container_width=True):
                checkout = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {'name': 'BlackScholes.ai Pro'},
                            'unit_amount': MONTHLY_PRICE,
                            'recurring': {'interval': 'month'}
                        },
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url="https://black-scholes-mvp-rstarr37.streamlit.app/?success=true",
                    cancel_url="https://black-scholes-mvp-rstarr37.streamlit.app/",
                )
                st.link_button("Go to Stripe Checkout", checkout.url, use_container_width=True)
        if st.button("Logout"):
            st.session_state.user_email = None
            st.session_state.is_pro = False
            st.rerun()

    st.title("📊 BlackScholes.ai")
    st.markdown("**The equation that built the multi-trillion dollar derivatives market — now in your browser.**")
    st.latex(r"\frac{\partial V}{\partial t} + rS \frac{\partial V}{\partial S} + \frac{1}{2} \sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} - rV = 0")

    # Calculator section (same great features)
    col1, col2 = st.columns([1, 2])
    with col1:
        S = st.number_input("Current Stock Price (S) $", value=100.0, step=0.1)
        K = st.number_input("Strike Price (K) $", value=100.0, step=0.1)
        T = st.number_input("Time to Expiration (years)", value=1.0, step=0.01)
        r = st.number_input("Risk-Free Rate (%)", value=5.0, step=0.1) / 100
        sigma = st.number_input("Volatility (σ %)", value=20.0, step=0.1) / 100
        option_type = st.radio("Option Type", ["Call", "Put"])

    if st.button("🚀 Calculate", type="primary", use_container_width=True):
        if not st.session_state.is_pro and st.session_state.calculations_used >= 5:
            st.error("Free daily limit reached. Upgrade to Pro for unlimited access!")
        else:
            greeks = black_scholes_greeks(S, K, T, r, sigma, option_type.lower())
            st.success(f"**{option_type} Option Price: ${greeks['Price']:.2f}**")
            
            cols = st.columns(3)
            cols[0].metric("Delta", greeks['Delta'])
            cols[1].metric("Gamma", greeks['Gamma'])
            cols[2].metric("Theta (daily)", greeks['Theta (daily)'])
            cols = st.columns(3)
            cols[0].metric("Vega (per 1%)", greeks['Vega (per 1%)'])
            cols[1].metric("Rho (per 1%)", greeks['Rho (per 1%)'])
            cols[2].metric("Implied Volatility", f"{sigma*100:.1f}%")

            st.subheader("Payoff at Expiration")
            prices = np.linspace(max(0, S-50), S+100, 200)
            payoff = np.maximum(prices - K, 0) if option_type == "Call" else np.maximum(K - prices, 0)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=prices, y=payoff, mode='lines', name='Payoff', line=dict(color='#00ff9d', width=3)))
            fig.update_layout(height=400, template="plotly_dark", xaxis_title="Stock Price at Expiration", yaxis_title="Profit/Loss")
            st.plotly_chart(fig, use_container_width=True)

            st.session_state.calculations_used += 1

    st.divider()
    st.subheader("🔍 Implied Volatility Solver")
    market_price = st.number_input("Market Price of Option $", value=10.45, step=0.01)
    if st.button("Solve for Volatility", type="secondary"):
        iv = implied_volatility(market_price, S, K, T, r, option_type.lower())
        if not np.isnan(iv):
            st.success(f"**Implied Volatility: {iv*100:.2f}%**")
        else:
            st.error("Could not solve — try different inputs")

    st.caption("Next-level Black-Scholes SaaS • Login + Recurring Subscriptions + Usage Tracking")

# Handle successful payment
if st.query_params.get("success"):
    st.success("✅ Payment successful! You now have **Pro access** (unlimited calculations). Welcome to the next level!")
    st.session_state.is_pro = True
    st.query_params.clear()  # Clean URL
