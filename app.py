from flask import Flask, render_template, request, redirect, url_for, flash
from twilio.rest import Client
import pandas as pd
import plotly.express as px
import plotly.io as pio
import threading, os

# -------------------- FLASK SETUP --------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)
pio.templates.default = "plotly_white"

# -------------------- LOAD CSV --------------------
CSV_FILE = "airline.csv"
try:
    df_global = pd.read_csv(CSV_FILE)
    print(f"Loaded {len(df_global)} records from {CSV_FILE}")
except Exception as e:
    print(f"Error loading CSV: {e}")
    df_global = pd.DataFrame()

# -------------------- TWILIO CONFIG --------------------
TWILIO_SID = "AC5bb3d9141afac5e0ed78524641"
TWILIO_AUTH_TOKEN = "fwcjocjfowjrf84956131"
TWILIO_VIRTUAL_NUMBER = "+1766565826"
TWILIO_VERIFIED_NUMBER = "+96556615991"

twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)


def send_sms_async(message_body):
    """Send SMS without blocking Flask."""
    try:
        twilio_client.messages.create(
            body=message_body,
            from_=TWILIO_VIRTUAL_NUMBER,
            to=TWILIO_VERIFIED_NUMBER
        )
        print("SMS sent successfully!")
    except Exception as e:
        print(f"Twilio error: {e}")


# -------------------- HOME --------------------
@app.route("/")
def index():
    df = df_global.copy()
    search_column = request.args.get("column")
    search_value = request.args.get("search")

    if search_column and search_value:
        df = df[df[search_column].astype(str).str.contains(search_value, case=False, na=False)]

    data = df.to_dict(orient="records")
    return render_template("index.html",
                           data=data,
                           columns=df.columns,
                           search_column=search_column,
                           search_value=search_value)


# -------------------- VISUALIZATION --------------------
@app.route("/visualize")
def visualize():
    df = df_global.copy()
    if df.empty:
        flash("No data available to visualize!", "danger")
        return redirect(url_for("index"))

    # ---------- KPI SUMMARY ----------
    total_flights = len(df)
    delayed = (df["Flight Status"] == "Delayed").sum()
    cancelled = (df["Flight Status"] == "Cancelled").sum()
    on_time = total_flights - delayed - cancelled

    # ---------- 1️⃣ Flight Status (Donut) ----------
    fig_status = px.pie(
        df,
        names="Flight Status",
        title="Flight Status Overview",
        color="Flight Status",
        color_discrete_sequence=["#007bff", "#ffc107", "#dc3545"],
        hole=0.45
    )
    fig_status.update_traces(textinfo="percent+label")

    # ---------- 2️⃣ Flights by Departure Airport ----------
    airport_counts = df["Airport Name"].value_counts().reset_index()
    airport_counts.columns = ["Airport Name", "Count"]
    fig_airport = px.bar(
        airport_counts,
        x="Airport Name",
        y="Count",
        title="Flights by Departure Airport",
        text="Count",
        color="Airport Name",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_airport.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Flights")

    # ---------- 3️⃣ Top Pilots ----------
    pilot_counts = df["Pilot Name"].value_counts().reset_index()
    pilot_counts.columns = ["Pilot Name", "Count"]
    fig_pilot = px.bar(
        pilot_counts.head(8),
        x="Pilot Name",
        y="Count",
        title="Top 8 Pilots by Assigned Flights",
        text="Count",
        color_discrete_sequence=["#1e90ff"]
    )
    fig_pilot.update_traces(marker_line_width=0.8)
    fig_pilot.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Flights")

    # ---------- 4️⃣ Passenger Age Distribution ----------
    fig_age = px.histogram(
        df,
        x="Age",
        nbins=8,
        title="Passenger Age Distribution",
        color_discrete_sequence=["#6f42c1"]
    )
    fig_age.update_layout(xaxis_title="Passenger Age", yaxis_title="Count")

    # ---------- 5️⃣ Most Common Destinations ----------
    dest_counts = df["Arrival Airport"].value_counts().reset_index()
    dest_counts.columns = ["Arrival Airport", "Count"]
    fig_dest = px.bar(
        dest_counts,
        x="Count",
        y="Arrival Airport",
        orientation="h",
        title="Most Common Destinations",
        text="Count",
        color_discrete_sequence=["#28a745"]
    )
    fig_dest.update_layout(showlegend=False, xaxis_title="Flights", yaxis_title=None)

    # ---------- Convert all to HTML ----------
    fig_status_html = pio.to_html(fig_status, full_html=False)
    fig_airport_html = pio.to_html(fig_airport, full_html=False)
    fig_pilot_html = pio.to_html(fig_pilot, full_html=False)
    fig_age_html = pio.to_html(fig_age, full_html=False)
    fig_dest_html = pio.to_html(fig_dest, full_html=False)

    return render_template("visualization.html",
                           total_flights=total_flights,
                           delayed=delayed,
                           cancelled=cancelled,
                           on_time=on_time,
                           fig_status_html=fig_status_html,
                           fig_airport_html=fig_airport_html,
                           fig_pilot_html=fig_pilot_html,
                           fig_age_html=fig_age_html,
                           fig_dest_html=fig_dest_html)


# -------------------- SEND NOTIFICATION --------------------
@app.route("/send_notification", methods=["POST"])
def send_notification():
    info = {k: request.form[k] for k in request.form}
    message_body = (
        f"Passenger Info:\n"
        f"ID: {info['passenger_id']}\n"
        f"Name: {info['first_name']} {info['last_name']}\n"
        f"Gender: {info['gender']}\nAge: {info['age']}\n"
        f"Nationality: {info['nationality']}\n"
        f"Airport: {info['airport_name']}\n"
        f"Status: {info['flight_status']}"
    )
    threading.Thread(target=send_sms_async, args=(message_body,)).start()
    flash("Notification sent successfully!", "success")
    return redirect(url_for("index"))


# -------------------- RUN APP --------------------
if __name__ == "__main__":
    app.run(debug=False)
