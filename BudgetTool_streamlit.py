import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Interactive Budgeting & APY Tool",
    page_icon="📊",
    layout="wide",
)

APY_RATE = 0.033        # 3.3% savings APY
IRS_401K_LIMIT = 23500  # per person 2025

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .section-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        color: white; padding: 0.4rem 0.8rem; border-radius: 6px;
        font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem;
        letter-spacing: 0.02em;
    }
    .result-card {
        background: #f8f9fa; border-left: 4px solid #4CAF50;
        border-radius: 6px; padding: 0.6rem 1rem; margin-bottom: 0.5rem;
    }
    .result-card-red  { border-left-color: #e74c3c !important; }
    .result-card-blue { border-left-color: #2b579a !important; }
    .result-card-gray { border-left-color: #888 !important; }
    .result-card-orange { border-left-color: #e67e22 !important; }
    .result-label { font-size: 0.82rem; color: #555; margin: 0; }
    .result-value { font-size: 1.25rem; font-weight: 800; margin: 0; }
    .result-value-green  { color: #27ae60; }
    .result-value-red    { color: #e74c3c; }
    .result-value-blue   { color: #2b579a; }
    .result-value-orange { color: #e67e22; }
    .result-value-dark   { color: #222; }
    .tax-card {
        background: #fcfcfc; border: 1px solid #e0e0e0;
        border-radius: 6px; padding: 0.5rem 0.8rem;
        margin-bottom: 0.3rem; font-size: 0.85rem;
    }
    .tax-row { display: flex; justify-content: space-between; }
    .tax-label { color: #666; }
    .tax-value { font-weight: 700; color: #333; }
    .thin-divider { border-top: 1px solid #ddd; margin: 0.6rem 0; }
    /* tighten tab bar */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 6px 14px; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DEFAULTS
# ─────────────────────────────────────────────
DEFAULT_INCOME = {
    "my_income": 100000.0, "Spouse_income": 100000.0,
    "my_emp_ret": 5.0,     "my_vol_ret": 0.0,
    "Spouse_emp_ret": 5.0, "Spouse_vol_ret": 0.0,
    "my_apy_pct": 10.0,    "Spouse_apy_pct": 10.0,
    "years": 1,
}

DEFAULT_EXPENSES = {
    "insurance": {
        "Health Prem (Mine)": 0.0, "Health Prem (Spouse)": 0.0,
        "Dental Ins": 0.0, "Vision Ins": 0.0,
        "Life Ins": 0.0, "Homeowners Ins": 0.0, "Vehicle Ins": 0.0,
    },
    "housing": {
        "Rent": 0.0, "Storage Unit Rent": 0.0, "Electric Bill": 0.0,
        "Gas Bill": 0.0, "Water Bill": 0.0, "Trash Bill": 0.0,
    },
    "childcare": {"Babysitting": 0.0, "Preschool": 0.0},
    "services": {
        "Dropbox": 0.0, "Amazon": 0.0, "Spotify": 0.0,
        "iCloud": 0.0, "House Cleaners": 0.0,
        "Cell Service": 0.0, "Cable (Comcast)": 0.0,
    },
    "food_gas": {"Groceries": 0.0, "Gas": 0.0},
}

CATEGORY_ICONS = {
    "insurance": "🛡️ Insurance",
    "housing":   "🏠 Housing",
    "childcare": "👶 Childcare",
    "services":  "⚙️ Services",
    "food_gas":  "⛽ Food & Gas",
}

CHART_COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"]

# ─────────────────────────────────────────────
# WIDGET KEY HELPERS
# ─────────────────────────────────────────────
def income_key(k):       return f"w_inc__{k}"
def expense_key(cat, k): return f"w_exp__{cat}__{k}"
def custom_key(name):    return f"w_custom__{name}"

# ─────────────────────────────────────────────
# SESSION STATE BOOTSTRAP
# ─────────────────────────────────────────────
if "_bootstrapped" not in st.session_state:
    st.session_state._bootstrapped = True
    st.session_state.custom_services = {}
    st.session_state._load_success = False
    for k, v in DEFAULT_INCOME.items():
        st.session_state[income_key(k)] = v
    for cat, items in DEFAULT_EXPENSES.items():
        for k, v in items.items():
            st.session_state[expense_key(cat, k)] = v

# ─────────────────────────────────────────────
# LOAD / SAVE
# ─────────────────────────────────────────────
def apply_load(raw: str):
    data = json.loads(raw)
    rates = data.get("rates", {})
    for k, default in DEFAULT_INCOME.items():
        raw_val = rates.get(k, default)
        try:
            v = int(float(raw_val)) if k == "years" else float(raw_val)
        except (ValueError, TypeError):
            v = default
        st.session_state[income_key(k)] = v

    saved_exp = data.get("expenses", {})
    for cat, items in DEFAULT_EXPENSES.items():
        cat_data = saved_exp.get(cat, {})
        for k in items:
            try:
                v = float(cat_data.get(k, 0))
            except (ValueError, TypeError):
                v = 0.0
            st.session_state[expense_key(cat, k)] = v

    custom = data.get("custom_services", {})
    st.session_state.custom_services = {}
    for name, raw_val in custom.items():
        try:
            v = float(raw_val)
        except (ValueError, TypeError):
            v = 0.0
        st.session_state.custom_services[name] = v
        st.session_state[custom_key(name)] = v

    st.session_state._load_success = True

def build_save_payload() -> str:
    rates    = {k: st.session_state.get(income_key(k), DEFAULT_INCOME[k]) for k in DEFAULT_INCOME}
    expenses = {cat: {k: st.session_state.get(expense_key(cat, k), 0.0) for k in items}
                for cat, items in DEFAULT_EXPENSES.items()}
    custom   = {n: st.session_state.get(custom_key(n), 0.0) for n in st.session_state.custom_services}
    return json.dumps({"rates": rates, "expenses": expenses, "custom_services": custom}, indent=4)

# ─────────────────────────────────────────────
# CALCULATION ENGINE
# ─────────────────────────────────────────────
def calculate() -> dict:
    def gi(k):       return float(st.session_state.get(income_key(k),       0) or 0)
    def ge(cat, k):  return float(st.session_state.get(expense_key(cat, k), 0) or 0)

    my_gross_annual      = gi("my_income")
    spouse_gross_annual  = gi("Spouse_income")
    total_gross_annual   = my_gross_annual + spouse_gross_annual
    my_gross_monthly     = my_gross_annual  / 12
    spouse_gross_monthly = spouse_gross_annual / 12

    my_ret_rate     = (gi("my_emp_ret") + gi("my_vol_ret"))     / 100
    spouse_ret_rate = (gi("Spouse_emp_ret") + gi("Spouse_vol_ret")) / 100
    my_ret_monthly     = my_gross_monthly     * my_ret_rate
    spouse_ret_monthly = spouse_gross_monthly * spouse_ret_rate

    total_pretax_ret = (my_ret_monthly + spouse_ret_monthly) * 12
    taxable_income   = max(0, total_gross_annual - total_pretax_ret - 30_000)

    brackets = [
        (23_200, .10), (94_300, .12), (201_050, .22),
        (383_900, .24), (487_450, .32), (609_350, .35), (float("inf"), .37),
    ]
    fed_tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if taxable_income > limit:
            fed_tax += (limit - prev) * rate; prev = limit
        else:
            fed_tax += (taxable_income - prev) * rate; break

    my_fica     = (min(my_gross_annual,    176_100) * .062) + (my_gross_annual    * .0145)
    spouse_fica = (min(spouse_gross_annual,176_100) * .062) + (spouse_gross_annual * .0145)
    total_annual_tax = fed_tax + my_fica + spouse_fica
    monthly_tax      = total_annual_tax / 12
    eff_rate         = (total_annual_tax / total_gross_annual * 100) if total_gross_annual else 0

    my_apy_dep     = my_gross_monthly     * (gi("my_apy_pct")     / 100)
    spouse_apy_dep = spouse_gross_monthly * (gi("Spouse_apy_pct") / 100)
    years = max(1, int(gi("years")))

    # Month-by-month APY growth series
    r = APY_RATE / 12
    total_months = years * 12
    months       = list(range(1, total_months + 1))
    my_balance, spouse_balance, combined_balance = [], [], []
    mb = sb = 0.0
    for m in months:
        mb = mb * (1 + r) + my_apy_dep
        sb = sb * (1 + r) + spouse_apy_dep
        my_balance.append(mb)
        spouse_balance.append(sb)
        combined_balance.append(mb + sb)

    my_apy_fv     = my_balance[-1]     if my_balance     else 0.0
    spouse_apy_fv = spouse_balance[-1] if spouse_balance else 0.0

    # Expense aggregation
    pie_data = {}
    total_monthly_expenses = 0.0
    for cat, items in DEFAULT_EXPENSES.items():
        cat_sum = sum(ge(cat, k) for k in items)
        if cat == "services":
            cat_sum += sum(float(st.session_state.get(custom_key(n), 0) or 0)
                           for n in st.session_state.custom_services)
        label = CATEGORY_ICONS.get(cat, cat.replace("_", " & ").capitalize())
        pie_data[label] = cat_sum
        total_monthly_expenses += cat_sum

    total_savings = my_ret_monthly + spouse_ret_monthly + my_apy_dep + spouse_apy_dep
    monthly_disc  = (my_gross_monthly + spouse_gross_monthly) - monthly_tax - total_savings - total_monthly_expenses

    # Income waterfall segments (monthly $)
    total_monthly_gross = my_gross_monthly + spouse_gross_monthly
    waterfall = {
        "Taxes":       monthly_tax,
        "Retirement":  my_ret_monthly + spouse_ret_monthly,
        "APY Savings": my_apy_dep + spouse_apy_dep,
        **{k: v for k, v in pie_data.items() if v > 0},
        "Discretionary": max(0, monthly_disc),
    }

    # Retirement contributions vs IRS limit
    my_annual_ret     = my_ret_monthly     * 12
    spouse_annual_ret = spouse_ret_monthly * 12

    return {
        # KPIs
        "monthly_disc":       monthly_disc,
        "my_ret_monthly":     my_ret_monthly,
        "spouse_ret_monthly": spouse_ret_monthly,
        "total_monthly_exp":  total_monthly_expenses,
        "fed_tax_monthly":    fed_tax / 12,
        "my_fica_monthly":    my_fica / 12,
        "spouse_fica_monthly":spouse_fica / 12,
        "eff_rate":           eff_rate,
        "my_apy_fv":          my_apy_fv,
        "spouse_apy_fv":      spouse_apy_fv,
        "combined_apy":       my_apy_fv + spouse_apy_fv,
        # Chart data
        "pie_data":           pie_data,
        "months":             months,
        "my_balance":         my_balance,
        "spouse_balance":     spouse_balance,
        "combined_balance":   combined_balance,
        "waterfall":          waterfall,
        "total_monthly_gross":total_monthly_gross,
        "my_annual_ret":      my_annual_ret,
        "spouse_annual_ret":  spouse_annual_ret,
        "my_apy_dep":         my_apy_dep,
        "spouse_apy_dep":     spouse_apy_dep,
        "years":              years,
    }

# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────
LAYOUT_BASE = dict(
    height=400,
    margin=dict(t=50, b=40, l=10, r=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12),
)

def chart_expense_pie(res):
    pie_data = {k: v for k, v in res["pie_data"].items() if v > 0}
    if not pie_data:
        return None
    fig = go.Figure(go.Pie(
        labels=list(pie_data.keys()),
        values=list(pie_data.values()),
        hole=0.38, textinfo="label+percent", textfont_size=12,
        marker=dict(colors=CHART_COLORS, line=dict(color="white", width=2)),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}/mo<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        title=dict(text="Monthly Expense Breakdown", font_size=15, x=0.5),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    )
    return fig

def chart_savings_growth(res):
    months = res["months"]
    if not months:
        return None

    # X-axis as year fractions for readability
    x = [m / 12 for m in months]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=res["my_balance"],
        name="Your APY", mode="lines",
        line=dict(color="#2196F3", width=2),
        hovertemplate="Year %{x:.1f}<br>$%{y:,.0f}<extra>Your APY</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=res["spouse_balance"],
        name="Spouse's APY", mode="lines",
        line=dict(color="#9C27B0", width=2),
        hovertemplate="Year %{x:.1f}<br>$%{y:,.0f}<extra>Spouse APY</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=res["combined_balance"],
        name="Combined", mode="lines",
        line=dict(color="#4CAF50", width=3, dash="dot"),
        hovertemplate="Year %{x:.1f}<br>$%{y:,.0f}<extra>Combined</extra>",
    ))
    # Shade area under combined
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=res["combined_balance"] + [0] * len(x),
        fill="toself", fillcolor="rgba(76,175,80,0.07)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(**LAYOUT_BASE,
        title=dict(text=f"APY Savings Growth Over {res['years']} Year(s) @ {APY_RATE*100:.1f}%", font_size=15, x=0.5),
        xaxis=dict(title="Years", gridcolor="#eee", zeroline=False),
        yaxis=dict(title="Balance ($)", tickprefix="$", tickformat=",.0f", gridcolor="#eee"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        hovermode="x unified",
    )
    return fig

def chart_income_waterfall(res):
    wf      = res["waterfall"]
    labels  = list(wf.keys())
    values  = list(wf.values())
    total   = res["total_monthly_gross"]

    colors = [
        "#e74c3c",   # Taxes
        "#e67e22",   # Retirement
        "#2196F3",   # APY Savings
        "#9C27B0", "#00BCD4", "#FF9800", "#795548", "#607D8B",  # expense cats
        "#27ae60",   # Discretionary (last)
    ]
    bar_colors = (colors[:3] + CHART_COLORS[:max(0, len(labels)-4)] + [colors[-1]])[:len(labels)]

    pcts = [v / total * 100 if total else 0 for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker_color=bar_colors,
        text=[f"${v:,.0f}  ({p:.1f}%)" for v, p in zip(values, pcts)],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>$%{x:,.2f}/mo<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        height=max(380, 38 * len(labels) + 80),
        title=dict(text=f"Where Your ${total:,.0f}/mo Goes", font_size=15, x=0.5),
        xaxis=dict(title="Monthly Amount ($)", tickprefix="$", tickformat=",.0f", gridcolor="#eee"),
        yaxis=dict(autorange="reversed"),
        bargap=0.35,
    )
    return fig

def chart_cashflow(res):
    gross  = res["total_monthly_gross"]
    tax    = res["fed_tax_monthly"] + res["my_fica_monthly"] + res["spouse_fica_monthly"]
    ret    = res["my_ret_monthly"] + res["spouse_ret_monthly"]
    apy    = res["my_apy_dep"] + res["spouse_apy_dep"]
    bills  = res["total_monthly_exp"]
    disc   = res["monthly_disc"]

    cats   = ["Gross Income", "Taxes", "Retirement", "APY Savings", "Bills", "Discretionary"]
    vals   = [gross, -tax, -ret, -apy, -bills, disc]
    clrs   = ["#27ae60", "#e74c3c", "#e67e22", "#2196F3", "#9C27B0",
               "#27ae60" if disc >= 0 else "#e74c3c"]

    fig = go.Figure(go.Bar(
        x=cats, y=vals,
        marker_color=clrs,
        text=[f"${abs(v):,.0f}" for v in vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#333", line_width=1)
    fig.update_layout(**LAYOUT_BASE,
        title=dict(text="Monthly Cash Flow", font_size=15, x=0.5),
        xaxis=dict(gridcolor="#eee"),
        yaxis=dict(title="$ / Month", tickprefix="$", tickformat=",.0f", gridcolor="#eee"),
        showlegend=False,
    )
    return fig

def chart_retirement_gauge(res):
    my_contrib    = res["my_annual_ret"]
    spouse_contrib= res["spouse_annual_ret"]
    limit         = IRS_401K_LIMIT

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Your 401(k) vs IRS Limit", "Spouse's 401(k) vs IRS Limit"),
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
    )
    for col, val, name in [(1, my_contrib, "You"), (2, spouse_contrib, "Spouse")]:
        pct = min(val / limit * 100, 100) if limit else 0
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=val,
            delta={"reference": limit, "valueformat": "$,.0f",
                   "increasing": {"color": "#e74c3c"}, "decreasing": {"color": "#27ae60"}},
            number={"prefix": "$", "valueformat": ",.0f"},
            gauge={
                "axis": {"range": [0, limit], "tickprefix": "$", "tickformat": ",.0f"},
                "bar":  {"color": "#27ae60" if pct < 80 else "#e67e22" if pct < 100 else "#e74c3c"},
                "steps": [
                    {"range": [0, limit * 0.5],  "color": "#e8f5e9"},
                    {"range": [limit * 0.5, limit * 0.8], "color": "#fff9c4"},
                    {"range": [limit * 0.8, limit], "color": "#ffebee"},
                ],
                "threshold": {"line": {"color": "#c0392b", "width": 3},
                              "thickness": 0.85, "value": limit},
            },
            title={"text": f"{name}<br><span style='font-size:11px'>IRS limit ${limit:,}</span>"},
        ), row=1, col=col)

    fig.update_layout(**LAYOUT_BASE,
        height=320,
        title=dict(text="Annual Retirement Contributions vs IRS Limit", font_size=15, x=0.5),
    )
    return fig

# ─────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────
def result_card(label, value, color="dark", card_class=""):
    st.markdown(f"""
    <div class="result-card {'result-card-' + card_class if card_class else ''}">
        <p class="result-label">{label}</p>
        <p class="result-value result-value-{color}">{value}</p>
    </div>""", unsafe_allow_html=True)

def tax_card(rows):
    inner = "".join(
        f'<div class="tax-row"><span class="tax-label">{l}</span>'
        f'<span class="tax-value">{v}</span></div>'
        for l, v in rows
    )
    st.markdown(f'<div class="tax-card">{inner}</div>', unsafe_allow_html=True)

def expense_section(category, title):
    st.markdown(f'<div class="section-header">{title} — Monthly $</div>', unsafe_allow_html=True)
    items = list(DEFAULT_EXPENSES[category].keys())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j, key in enumerate(items[i: i + 2]):
            with cols[j]:
                st.number_input(key, min_value=0.0, step=1.0,
                                key=expense_key(category, key))

def show_chart(fig, empty_msg="Enter data to see this chart."):
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(empty_msg)

# ─────────────────────────────────────────────
# TITLE & FILE CONTROLS
# ─────────────────────────────────────────────
st.title("📊 Interactive Budgeting & APY Tool")

hdr_l, hdr_r = st.columns([3, 1])
with hdr_r:
    st.download_button("💾 Save Profile", data=build_save_payload(),
                       file_name="budget_data.json", mime="application/json",
                       use_container_width=True)
    uploaded = st.file_uploader("📁 Load Profile", type="json", label_visibility="collapsed")
    if uploaded is not None:
        try:
            apply_load(uploaded.read().decode())
        except Exception as e:
            st.error(f"Could not parse file: {e}")

if st.session_state.get("_load_success"):
    st.success("✅ Profile loaded successfully!")
    st.session_state._load_success = False

# ─────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────
left_col, right_col = st.columns([2, 3], gap="large")

# ══════════════════════════════════════════
# LEFT — inputs
# ══════════════════════════════════════════
with left_col:
    st.markdown('<div class="section-header">💰 Income & Savings Rates</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Your Gross Annual Income ($)",  min_value=0.0, step=1000.0, key=income_key("my_income"))
        st.number_input("Your Employee Ret. (%)",        min_value=0.0, max_value=100.0, step=0.5, key=income_key("my_emp_ret"))
        st.number_input("Your Voluntary Ret. (%)",       min_value=0.0, max_value=100.0, step=0.5, key=income_key("my_vol_ret"))
        st.number_input("Your APY Alloc. (%)",           min_value=0.0, max_value=100.0, step=0.5, key=income_key("my_apy_pct"))
    with c2:
        st.number_input("Spouse's Gross Annual Income ($)", min_value=0.0, step=1000.0, key=income_key("Spouse_income"))
        st.number_input("Spouse's Employee Ret. (%)",       min_value=0.0, max_value=100.0, step=0.5, key=income_key("Spouse_emp_ret"))
        st.number_input("Spouse's Voluntary Ret. (%)",      min_value=0.0, max_value=100.0, step=0.5, key=income_key("Spouse_vol_ret"))
        st.number_input("Spouse's APY Alloc. (%)",          min_value=0.0, max_value=100.0, step=0.5, key=income_key("Spouse_apy_pct"))
    st.number_input("Year Target for APY (#)", min_value=1, max_value=50, step=1, key=income_key("years"))

    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    expense_section("insurance", "🛡️ Insurance")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    expense_section("housing",   "🏠 Housing")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    expense_section("childcare", "👶 Childcare")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    expense_section("food_gas",  "⛽ Food & Gas")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    expense_section("services",  "⚙️ Services")

    for svc_name in st.session_state.custom_services:
        st.number_input(svc_name, min_value=0.0, step=1.0, key=custom_key(svc_name))

    with st.expander("➕ Add Custom Service"):
        new_name = st.text_input("Service name", key="new_svc_name")
        new_amt  = st.number_input("Monthly cost ($)", min_value=0.0, step=1.0, key="new_svc_amt")
        if st.button("Add Service"):
            name = new_name.strip()
            if not name:
                st.warning("Please enter a service name.")
            elif name in st.session_state.custom_services or name in DEFAULT_EXPENSES["services"]:
                st.warning(f"'{name}' already exists.")
            else:
                st.session_state.custom_services[name] = new_amt
                st.session_state[custom_key(name)] = new_amt
                st.rerun()

# ══════════════════════════════════════════
# RIGHT — KPIs + tabbed charts
# ══════════════════════════════════════════
with right_col:
    res = calculate()

    # ── KPI row ──────────────────────────────
    st.markdown('<div class="section-header">📊 Budget Dashboard</div>', unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    disc = res["monthly_disc"]
    with k1: result_card("💵 Discretionary/mo", f"${disc:,.0f}",
                         "green" if disc >= 0 else "red", "" if disc >= 0 else "red")
    with k2: result_card("📈 Monthly Bills",   f"${res['total_monthly_exp']:,.0f}", "dark", "gray")
    with k3: result_card("🏦 Combined APY",    f"${res['combined_apy']:,.0f}", "blue", "blue")
    with k4: result_card("📊 Tax Rate",        f"{res['eff_rate']:.1f}%", "dark", "gray")

    t1, t2, t3, t4 = st.columns(4)
    with t1: result_card("🧑 Your Ret./mo",     f"${res['my_ret_monthly']:,.0f}",    "dark", "gray")
    with t2: result_card("👫 Spouse Ret./mo",   f"${res['spouse_ret_monthly']:,.0f}", "dark", "gray")
    with t3: result_card("📆 Your APY Target",  f"${res['my_apy_fv']:,.0f}",         "blue", "blue")
    with t4: result_card("📆 Spouse APY Target",f"${res['spouse_apy_fv']:,.0f}",     "blue", "blue")

    # Tax detail (collapsed by default to save space)
    with st.expander("📋 Monthly Tax Breakdown"):
        tax_card([
            ("• Federal Income Tax",  f"${res['fed_tax_monthly']:,.2f}"),
            ("• Your FICA Tax",       f"${res['my_fica_monthly']:,.2f}"),
            ("• Spouse's FICA Tax",   f"${res['spouse_fica_monthly']:,.2f}"),
            ("• Effective Tax Rate",  f"{res['eff_rate']:.1f}%"),
        ])

    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    # ── Tabbed charts ─────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🥧 Expense Breakdown",
        "📈 Savings Growth",
        "💧 Income Waterfall",
        "📊 Cash Flow",
        "🎯 Retirement Limits",
    ])

    with tab1:
        show_chart(chart_expense_pie(res),
                   "Enter non-zero expenses to see the breakdown.")

    with tab2:
        show_chart(chart_savings_growth(res),
                   "Enter APY allocation percentages to see growth.")

    with tab3:
        show_chart(chart_income_waterfall(res),
                   "Enter income and expenses to see the waterfall.")

    with tab4:
        show_chart(chart_cashflow(res),
                   "Enter income and expenses to see cash flow.")

    with tab5:
        show_chart(chart_retirement_gauge(res),
                   "Enter retirement percentages to see contribution gauges.")
