import streamlit as st
import plotly.graph_objects as go
import json

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Interactive Budgeting & APY Tool",
    page_icon="📊",
    layout="wide",
)

APY_RATE = 0.033  # 3.3%

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Tighten up default Streamlit padding */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* Section header style */
    .section-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
        letter-spacing: 0.02em;
    }

    /* Result card */
    .result-card {
        background: #f8f9fa;
        border-left: 4px solid #4CAF50;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.5rem;
    }
    .result-card-red  { border-left-color: #e74c3c !important; }
    .result-card-blue { border-left-color: #2b579a !important; }
    .result-card-gray { border-left-color: #888 !important; }

    .result-label { font-size: 0.82rem; color: #555; margin: 0; }
    .result-value { font-size: 1.25rem; font-weight: 800; margin: 0; }
    .result-value-green { color: #27ae60; }
    .result-value-red   { color: #e74c3c; }
    .result-value-blue  { color: #2b579a; }
    .result-value-dark  { color: #222; }

    /* Tax sub-card */
    .tax-card {
        background: #fcfcfc;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.3rem;
        font-size: 0.85rem;
    }
    .tax-row { display: flex; justify-content: space-between; }
    .tax-label { color: #666; }
    .tax-value { font-weight: 700; color: #333; }

    /* Thin divider */
    .thin-divider { border-top: 1px solid #ddd; margin: 0.6rem 0; }

    /* File upload area tweak */
    .uploadedFile { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────
DEFAULT_INCOME = {
    "my_income": "100000", "Spouse_income": "100000",
    "my_emp_ret": "5",     "my_vol_ret": "0",
    "Spouse_emp_ret": "5", "Spouse_vol_ret": "0",
    "my_apy_pct": "10",    "Spouse_apy_pct": "10",
    "years": "1",
}

DEFAULT_EXPENSES = {
    "insurance": {
        "Health Prem (Mine)": "0", "Health Prem (Spouse)": "0",
        "Dental Ins": "0", "Vision Ins": "0",
        "Life Ins": "0", "Homeowners Ins": "0", "Vehicle Ins": "0",
    },
    "housing": {
        "Rent": "0", "Storage Unit Rent": "0", "Electric Bill": "0",
        "Gas Bill": "0", "Water Bill": "0", "Trash Bill": "0",
    },
    "childcare": {"Babysitting": "0", "Preschool": "0"},
    "services": {
        "Dropbox": "0", "Amazon": "0", "Spotify": "0",
        "iCloud": "0", "House Cleaners": "0",
        "Cell Service": "0", "Cable (Comcast)": "0",
    },
    "food_gas": {"Groceries": "0", "Gas": "0"},
}

CATEGORY_ICONS = {
    "insurance": "🛡️ Insurance",
    "housing":   "🏠 Housing",
    "childcare": "👶 Childcare",
    "services":  "⚙️ Services",
    "food_gas":  "⛽ Food & Gas",
}

if "income" not in st.session_state:
    st.session_state.income = dict(DEFAULT_INCOME)
if "expenses" not in st.session_state:
    import copy
    st.session_state.expenses = copy.deepcopy(DEFAULT_EXPENSES)
if "custom_services" not in st.session_state:
    st.session_state.custom_services = {}  # name -> value string


# ─────────────────────────────────────────────
# CALCULATION ENGINE  (pure logic, no UI)
# ─────────────────────────────────────────────
def calculate(income: dict, expenses: dict, custom_services: dict) -> dict:
    def f(key, d=income):
        try:
            return float(d.get(key, 0) or 0)
        except ValueError:
            return 0.0

    my_gross_annual     = f("my_income")
    spouse_gross_annual = f("Spouse_income")
    total_gross_annual  = my_gross_annual + spouse_gross_annual

    my_gross_monthly     = my_gross_annual / 12
    spouse_gross_monthly = spouse_gross_annual / 12

    my_ret_rate     = (f("my_emp_ret") + f("my_vol_ret")) / 100
    spouse_ret_rate = (f("Spouse_emp_ret") + f("Spouse_vol_ret")) / 100

    my_ret_monthly     = my_gross_monthly * my_ret_rate
    spouse_ret_monthly = spouse_gross_monthly * spouse_ret_rate

    # Progressive federal tax
    total_pretax_ret = (my_ret_monthly + spouse_ret_monthly) * 12
    standard_deduction = 30_000
    taxable_income = max(0, total_gross_annual - total_pretax_ret - standard_deduction)

    brackets = [
        (23_200,       0.10), (94_300,   0.12), (201_050, 0.22),
        (383_900,      0.24), (487_450,  0.32), (609_350, 0.35),
        (float("inf"), 0.37),
    ]
    fed_tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if taxable_income > limit:
            fed_tax += (limit - prev) * rate
            prev = limit
        else:
            fed_tax += (taxable_income - prev) * rate
            break

    my_fica     = (min(my_gross_annual,     176_100) * 0.062) + (my_gross_annual     * 0.0145)
    spouse_fica = (min(spouse_gross_annual, 176_100) * 0.062) + (spouse_gross_annual * 0.0145)

    total_annual_tax = fed_tax + my_fica + spouse_fica
    monthly_tax      = total_annual_tax / 12
    eff_rate         = (total_annual_tax / total_gross_annual * 100) if total_gross_annual else 0

    # APY savings
    my_apy_dep     = my_gross_monthly     * (f("my_apy_pct")     / 100)
    spouse_apy_dep = spouse_gross_monthly * (f("Spouse_apy_pct") / 100)
    years = max(1, int(f("years")))

    def fv(pmt):
        r = APY_RATE / 12
        return pmt * (((1 + r) ** (12 * years) - 1) / r) * (1 + r)

    my_apy_fv     = fv(my_apy_dep)
    spouse_apy_fv = fv(spouse_apy_dep)

    # Expenses aggregation
    pie_data = {}
    total_monthly_expenses = 0.0

    for cat, items in expenses.items():
        cat_sum = sum(float(v or 0) for v in items.values())
        # add custom services into services bucket
        if cat == "services":
            cat_sum += sum(float(v or 0) for v in custom_services.values())
        label = CATEGORY_ICONS.get(cat, cat.replace("_", " & ").capitalize())
        pie_data[label] = cat_sum
        total_monthly_expenses += cat_sum

    total_savings = my_ret_monthly + spouse_ret_monthly + my_apy_dep + spouse_apy_dep
    monthly_disc  = (my_gross_monthly + spouse_gross_monthly) - monthly_tax - total_savings - total_monthly_expenses

    return {
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
        "pie_data":           pie_data,
    }


# ─────────────────────────────────────────────
# SAVE / LOAD HELPERS
# ─────────────────────────────────────────────
def build_save_payload() -> str:
    payload = {
        "rates":           st.session_state.income,
        "expenses":        st.session_state.expenses,
        "custom_services": st.session_state.custom_services,
    }
    return json.dumps(payload, indent=4)


def apply_loaded_payload(raw: str):
    import copy
    try:
        data = json.loads(raw)
        st.session_state.income          = {**DEFAULT_INCOME,  **data.get("rates", {})}
        st.session_state.expenses        = {**copy.deepcopy(DEFAULT_EXPENSES), **data.get("expenses", {})}
        st.session_state.custom_services = data.get("custom_services", {})
        st.success("✅ Profile loaded successfully!")
    except Exception as e:
        st.error(f"Could not parse file: {e}")


# ─────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────
def result_card(label: str, value: str, color: str = "dark", card_class: str = ""):
    color_class = f"result-value-{color}"
    card_extra  = f"result-card-{card_class}" if card_class else ""
    st.markdown(f"""
    <div class="result-card {card_extra}">
        <p class="result-label">{label}</p>
        <p class="result-value {color_class}">{value}</p>
    </div>""", unsafe_allow_html=True)


def tax_card(rows: list[tuple]):
    inner = "".join(
        f'<div class="tax-row"><span class="tax-label">{lbl}</span>'
        f'<span class="tax-value">{val}</span></div>'
        for lbl, val in rows
    )
    st.markdown(f'<div class="tax-card">{inner}</div>', unsafe_allow_html=True)


def expense_section(category: str, title: str):
    st.markdown(f'<div class="section-header">{title} — Monthly $</div>', unsafe_allow_html=True)
    items = st.session_state.expenses[category]
    keys  = list(items.keys())
    for i in range(0, len(keys), 2):
        cols = st.columns(2)
        for j, key in enumerate(keys[i : i + 2]):
            with cols[j]:
                val = cols[j].number_input(
                    key,
                    min_value=0.0, step=1.0,
                    value=float(items[key] or 0),
                    key=f"{category}__{key}",
                    label_visibility="visible",
                )
                st.session_state.expenses[category][key] = str(val)


# ─────────────────────────────────────────────
# APP TITLE & FILE CONTROLS
# ─────────────────────────────────────────────
st.title("📊 Interactive Budgeting & APY Tool")

top_left, top_right = st.columns([3, 1])
with top_right:
    # Save
    save_json = build_save_payload()
    st.download_button(
        label="💾 Save Profile",
        data=save_json,
        file_name="budget_data.json",
        mime="application/json",
        use_container_width=True,
    )
    # Load
    uploaded = st.file_uploader("📁 Load Profile", type="json", label_visibility="collapsed")
    if uploaded:
        apply_loaded_payload(uploaded.read().decode())
        st.rerun()

# ─────────────────────────────────────────────
# MAIN LAYOUT  — inputs left, results right
# ─────────────────────────────────────────────
left_col, right_col = st.columns([2, 3], gap="large")

# ══════════════════════════════════════════════
# LEFT COLUMN — all inputs
# ══════════════════════════════════════════════
with left_col:

    # ── Income & Savings Rates ──────────────────
    st.markdown('<div class="section-header">💰 Income & Savings Rates</div>', unsafe_allow_html=True)
    inc = st.session_state.income

    c1, c2 = st.columns(2)
    with c1:
        inc["my_income"] = str(st.number_input(
            "Your Gross Annual Income ($)", min_value=0.0, step=1000.0,
            value=float(inc["my_income"] or 0), key="my_income"))
        inc["my_emp_ret"] = str(st.number_input(
            "Your Employee Ret. (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=float(inc["my_emp_ret"] or 0), key="my_emp_ret"))
        inc["my_vol_ret"] = str(st.number_input(
            "Your Voluntary Ret. (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=float(inc["my_vol_ret"] or 0), key="my_vol_ret"))
        inc["my_apy_pct"] = str(st.number_input(
            "Your APY Alloc. (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=float(inc["my_apy_pct"] or 0), key="my_apy_pct"))
    with c2:
        inc["Spouse_income"] = str(st.number_input(
            "Spouse's Gross Annual Income ($)", min_value=0.0, step=1000.0,
            value=float(inc["Spouse_income"] or 0), key="Spouse_income"))
        inc["Spouse_emp_ret"] = str(st.number_input(
            "Spouse's Employee Ret. (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=float(inc["Spouse_emp_ret"] or 0), key="Spouse_emp_ret"))
        inc["Spouse_vol_ret"] = str(st.number_input(
            "Spouse's Voluntary Ret. (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=float(inc["Spouse_vol_ret"] or 0), key="Spouse_vol_ret"))
        inc["Spouse_apy_pct"] = str(st.number_input(
            "Spouse's APY Alloc. (%)", min_value=0.0, max_value=100.0, step=0.5,
            value=float(inc["Spouse_apy_pct"] or 0), key="Spouse_apy_pct"))

    inc["years"] = str(st.number_input(
        "Year Target for APY (#)", min_value=1, max_value=50, step=1,
        value=max(1, int(inc["years"] or 1)), key="years"))

    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    # ── Expense Categories ──────────────────────
    expense_section("insurance", "🛡️ Insurance")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    expense_section("housing",   "🏠 Housing")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    expense_section("childcare", "👶 Childcare")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    expense_section("food_gas",  "⛽ Food & Gas")
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    # ── Services (with custom add) ──────────────
    expense_section("services", "⚙️ Services")

    # Custom services
    for svc_name, svc_val in st.session_state.custom_services.items():
        val = st.number_input(
            svc_name, min_value=0.0, step=1.0,
            value=float(svc_val or 0),
            key=f"custom__{svc_name}",
        )
        st.session_state.custom_services[svc_name] = str(val)

    # Add custom service expander
    with st.expander("➕ Add Custom Service"):
        new_name = st.text_input("Service name", key="new_svc_name")
        new_amt  = st.number_input("Monthly cost ($)", min_value=0.0, step=1.0, key="new_svc_amt")
        if st.button("Add Service"):
            name = new_name.strip()
            if name and name not in st.session_state.custom_services \
                    and name not in st.session_state.expenses["services"]:
                st.session_state.custom_services[name] = str(new_amt)
                st.rerun()
            elif not name:
                st.warning("Please enter a service name.")
            else:
                st.warning(f"'{name}' already exists.")

# ══════════════════════════════════════════════
# RIGHT COLUMN — results + chart
# ══════════════════════════════════════════════
with right_col:
    res = calculate(
        st.session_state.income,
        st.session_state.expenses,
        st.session_state.custom_services,
    )

    st.markdown('<div class="section-header">📊 Budget Visual Dashboard</div>', unsafe_allow_html=True)

    # ── Primary KPIs ────────────────────────────
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        disc = res["monthly_disc"]
        color     = "green" if disc >= 0 else "red"
        card_cls  = "" if disc >= 0 else "red"
        result_card("💵 Monthly Discretionary", f"${disc:,.2f}", color, card_cls)
    with kpi2:
        result_card("📈 Total Monthly Bills", f"${res['total_monthly_exp']:,.2f}", "dark", "gray")
    with kpi3:
        result_card("🏦 Combined APY Pool", f"${res['combined_apy']:,.2f}", "blue", "blue")

    ret1, ret2 = st.columns(2)
    with ret1:
        result_card("🧑 Your Retirement / Mo", f"${res['my_ret_monthly']:,.2f}", "dark", "gray")
    with ret2:
        result_card("👫 Spouse's Retirement / Mo", f"${res['spouse_ret_monthly']:,.2f}", "dark", "gray")

    # ── Tax Breakdown ───────────────────────────
    st.markdown("**📋 Monthly Tax Breakdown**")
    tax_card([
        ("• Federal Income Tax",  f"${res['fed_tax_monthly']:,.2f}"),
        ("• Your FICA Tax",       f"${res['my_fica_monthly']:,.2f}"),
        ("• Spouse's FICA Tax",   f"${res['spouse_fica_monthly']:,.2f}"),
        ("• Effective Tax Rate",  f"{res['eff_rate']:.1f}%"),
    ])

    # ── APY Detail ──────────────────────────────
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    apy1, apy2 = st.columns(2)
    with apy1:
        result_card("📆 Your End-of-Year APY",    f"${res['my_apy_fv']:,.2f}",     "blue", "blue")
    with apy2:
        result_card("📆 Spouse's End-of-Year APY", f"${res['spouse_apy_fv']:,.2f}", "blue", "blue")

    # ── Pie Chart ───────────────────────────────
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    pie_data = {k: v for k, v in res["pie_data"].items() if v > 0}

    if pie_data:
        fig = go.Figure(go.Pie(
            labels=list(pie_data.keys()),
            values=list(pie_data.values()),
            hole=0.35,
            textinfo="label+percent",
            textfont_size=13,
            marker=dict(
                colors=[
                    "#2196F3", "#4CAF50", "#FF9800",
                    "#9C27B0", "#F44336", "#00BCD4",
                ],
                line=dict(color="white", width=2),
            ),
            hovertemplate="<b>%{label}</b><br>$%{value:,.2f}/mo<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Monthly Expense Breakdown", font_size=16, x=0.5),
            margin=dict(t=50, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Enter non-zero expenses above to see the expense breakdown chart.")
