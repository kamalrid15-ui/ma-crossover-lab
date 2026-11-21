import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(page_title="اختبار تقاطع المتوسطات", layout="wide")
st.title("اختبار استراتيجية تقاطع المتوسطات المتحركة")
st.caption("أداة تعليمية فقط وليست نصيحة استثمارية. الأداء السابق لا يضمن النتائج المستقبلية.")


@st.cache_data(ttl=3600)
def load(ticker, years):
    d = yf.download(ticker, period=f"{years}y", auto_adjust=True, progress=False)
    if d.empty:
        return d
    d.columns = d.columns.get_level_values(0)
    d["Return"] = d["Close"].pct_change()
    return d


def describe(curve, years):
    annual = curve.iloc[-1] ** (1 / years) - 1
    drawdown = (curve / curve.cummax() - 1).min()
    return annual, drawdown


# ---------- القائمة الجانبية ----------
st.sidebar.header("الإعدادات")
ticker = st.sidebar.selectbox(
    "الأصل", ["SPY", "QQQ", "AAPL", "MSFT", "GC=F", "BTC-USD", "EURUSD=X"]
)
years = st.sidebar.slider("عدد السنوات", 3, 20, 10)
fast = st.sidebar.slider("المتوسط السريع", 5, 60, 20, step=5)
slow = st.sidebar.slider("المتوسط البطيء", 30, 250, 50, step=10)
cost_pct = st.sidebar.slider("تكلفة كل صفقة (%)", 0.0, 1.0, 0.1, step=0.05)

if fast >= slow:
    st.warning("يجب أن يكون المتوسط السريع أصغر من البطيء.")
    st.stop()

df = load(ticker, years)
if df.empty:
    st.error("تعذّر جلب البيانات لهذا الأصل. جرّب أصلاً آخر.")
    st.stop()

df = df.copy()

# ---------- حساب الاستراتيجية ----------
df["fast"] = df["Close"].rolling(fast).mean()
df["slow"] = df["Close"].rolling(slow).mean()
# الإشارة تُنفَّذ في اليوم التالي (shift) لتجنب انحياز النظر إلى المستقبل
df["Position"] = (df["fast"] > df["slow"]).astype(int).shift(1)
trades = df["Position"].diff().abs()
df["Strategy"] = df["Position"] * df["Return"] - trades * cost_pct / 100
df = df.dropna()

buyhold = (1 + df["Return"]).cumprod()
strategy = (1 + df["Strategy"]).cumprod()
n_years = len(df) / 252

a1, d1 = describe(buyhold, n_years)
a2, d2 = describe(strategy, n_years)

# ---------- العرض ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("شراء وانتظار: عائد سنوي", f"{a1:.1%}")
c2.metric("الاستراتيجية: عائد سنوي", f"{a2:.1%}")
c3.metric("أسوأ تراجع (شراء وانتظار)", f"{d1:.0%}")
c4.metric("أسوأ تراجع (الاستراتيجية)", f"{d2:.0%}")
st.write(f"عدد الدخول والخروج: **{int(trades.sum())}**")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
ax1.plot(df.index, df["Close"], label="Price", color="gray")
ax1.plot(df.index, df["fast"], label=f"SMA {fast}")
ax1.plot(df.index, df["slow"], label=f"SMA {slow}")
ax1.set_title(ticker)
ax1.legend()
ax2.plot(buyhold, label="Buy & Hold")
ax2.plot(strategy, label="Strategy")
ax2.set_ylabel("Growth of $1")
ax2.legend()
st.pyplot(fig)

st.info(
    "الاختبار على أصل واحد وفترة واحدة لا يثبت شيئاً. "
    "ما يهم هو استقرار النتيجة عبر أصول وفترات مختلفة."
)
