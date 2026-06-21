import streamlit as st
import pandas as pd
import numpy_financial as npf
import plotly.express as px

# Настройка страницы
st.set_page_config(page_title="Лизинговый Калькулятор", layout="wide")

st.title("🚗 Дашборд: Расчет ставки по лизингу")
st.markdown("Этот инструмент вычисляет **реальную эффективную процентную ставку** на основе ваших платежей и строит аннуитетный график погашения.")

# --- БОКОВАЯ ПАНЕЛЬ С ВВОДОМ ДАННЫХ ---
st.sidebar.header("Параметры лизинга")

car_price = st.sidebar.number_input("Стоимость авто (руб.)", min_value=10000, value=3000000, step=100000)
down_payment = st.sidebar.number_input("Первоначальный взнос (руб.)", min_value=0, value=600000, step=50000)
term_months = st.sidebar.number_input("Срок лизинга (мес.)", min_value=1, value=36, step=1)

# Пользователь может ввести либо ежемесячный платеж, либо он будет рассчитан из общей стоимости
calc_type = st.sidebar.radio("Что вам известно?", ["Ежемесячный платеж", "Общая стоимость лизинга"])

if calc_type == "Ежемесячный платеж":
    monthly_payment = st.sidebar.number_input("Ежемесячный платеж (руб.)", min_value=1000, value=85000, step=1000)
    total_lease_cost = down_payment + (monthly_payment * term_months)
    st.sidebar.info(f"Общая стоимость лизинга составит: **{total_lease_cost:,.0f} руб.**".replace(',', ' '))
else:
    # Динамическое значение по умолчанию (стоимость авто + 20%), чтобы value никогда не было меньше min_value
    default_total_cost = int(car_price * 1.2) 
    # Защита от случая, если введенная ранее стоимость закешировалась и стала меньше новой цены авто
    if default_total_cost < int(car_price):
        default_total_cost = int(car_price)

    total_lease_cost = st.sidebar.number_input("Общая стоимость лизинга (руб.)", min_value=int(car_price), value=default_total_cost, step=100000)
    monthly_payment = (total_lease_cost - down_payment) / term_months
    st.sidebar.info(f"Ежемесячный платеж составит: **{monthly_payment:,.0f} руб.**".replace(',', ' '))


# --- ОСНОВНЫЕ ВЫЧИСЛЕНИЯ ---
# Тело кредита (сумма, которую финансирует лизинговая компания)
financed_amount = car_price - down_payment

# Проверка на адекватность введенных данных
if financed_amount <= 0:
    st.error("Ошибка: Первоначальный взнос больше или равен стоимости авто. Финансирование не требуется.")
    st.stop()

if total_lease_cost <= car_price:
    st.error("Ошибка: Общая стоимость лизинга должна быть больше стоимости автомобиля (иначе ставка отрицательная).")
    st.stop()

# Расчет ставки (используем numpy_financial)
# pv - present value (сумма долга), pmt - payment (платеж со знаком минус), nper - срок
monthly_rate = npf.rate(nper=term_months, pmt=-monthly_payment, pv=financed_amount, fv=0)

if pd.isna(monthly_rate):
    st.error("Не удалось рассчитать ставку по заданным параметрам. Проверьте введенные данные.")
    st.stop()

annual_rate = monthly_rate * 12 * 100  # Перевод в годовые проценты
overpayment = total_lease_cost - car_price # Переплата сверх стоимости авто

# --- ОТОБРАЖЕНИЕ КЛЮЧЕВЫХ МЕТРИК ---
st.subheader("📊 Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Эффективная годовая ставка", f"{annual_rate:.2f} %")
col2.metric("Сумма финансирования", f"{financed_amount:,.0f} ₽".replace(',', ' '))
col3.metric("Общая переплата", f"{overpayment:,.0f} ₽".replace(',', ' '))
col4.metric("Ежемесячный платеж", f"{monthly_payment:,.0f} ₽".replace(',', ' '))

st.divider()

# --- ГЕНЕРАЦИЯ ГРАФИКА ПЛАТЕЖЕЙ (Аннуитет) ---
schedule = []
balance = financed_amount

for month in range(1, term_months + 1):
    interest_payment = balance * monthly_rate
    principal_payment = monthly_payment - interest_payment
    balance -= principal_payment
    
    # Защита от микрокопеек в последнем месяце
    if balance < 0.01: 
        balance = 0

    schedule.append({
        "Месяц": month,
        "Платеж (руб)": round(monthly_payment, 2),
        "Погашение долга (руб)": round(principal_payment, 2),
        "Погашение процентов (руб)": round(interest_payment, 2),
        "Остаток долга (руб)": round(balance, 2)
    })

df_schedule = pd.DataFrame(schedule)

# --- ВИЗУАЛИЗАЦИЯ ---
st.subheader("📈 Структура ежемесячного платежа")

# Подготовка данных для графика
df_melted = df_schedule.melt(id_vars=['Месяц'], 
                             value_vars=['Погашение долга (руб)', 'Погашение процентов (руб)'],
                             var_name='Тип платежа', value_name='Сумма')

fig = px.bar(df_melted, x='Месяц', y='Сумма', color='Тип платежа',
             title="Соотношение долга и процентов в платежах (Аннуитет)",
             color_discrete_sequence=['#1f77b4', '#ff7f0e'])
st.plotly_chart(fig, use_container_width=True)

# --- ТАБЛИЦА С ГРАФИКОМ ---
st.subheader("📅 Детальный график погашения")
st.dataframe(
    df_schedule.style.format({
        "Платеж (руб)": "{:,.2f} ₽",
        "Погашение долга (руб)": "{:,.2f} ₽",
        "Погашение процентов (руб)": "{:,.2f} ₽",
        "Остаток долга (руб)": "{:,.2f} ₽",
    }),
    use_container_width=True,
    height=400
)