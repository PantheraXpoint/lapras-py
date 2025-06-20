import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.new_dashboard_subscriber import EnhancedDashboardSubscriber as eds
from lapras_middleware.event_db import get_event_db, query_event_db
from design import MeetingRoomDesign
import time # May be required by DashboardClient or Streamlit app
import streamlit as st
from st_bridge import bridge
import pandas as pd
from datetime import datetime

def main():
    TARGET_LIGHT_AGENT_ID = "hue_light"
    TARGET_AC_AGENT_ID = "aircon"

    # Timer for periodic auto update
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = time.time()
    # Initialize DashboardClient instance and related session_state variables
    if 'mqtt_client' not in st.session_state:
        st.info("Initializing MQTT client...")

        try:
            mqtt_broker = "143.248.57.73"  # MQTT broker address
            mqtt_port = 1883

            # Create the client object before connecting to the broker
            client = eds(mqtt_broker=mqtt_broker, mqtt_port=mqtt_port)

            # Set Streamlit instance explicitly (additional validation)
            try:
                client.set_streamlit(st)
                print("Streamlit instance set successfully")
            except Exception as st_error:
                print(f"Error while setting Streamlit instance: {st_error}")
                import traceback
                traceback.print_exc()

            # Initialize session state
            st.session_state.mqtt_client = client
            st.session_state.last_event_type = "None"
            st.session_state.last_event_timestamp = time.time()

            # Try to connect the MQTT client
            try:
                # print(f"Attempting to connect to MQTT broker {mqtt_broker}:{mqtt_port}...")
                client.mqtt_client.connect(mqtt_broker, mqtt_port)

                # Wait briefly for initial connection and subscription
                time.sleep(2)

                # Subscribe to command result topic (EnhancedDashboardSubscriber does not subscribe by default)
                client.mqtt_client.subscribe("dashboard/control/result", qos=1)
                # print("Subscribed to command result topic 'dashboard/control/result'")

                # Start the MQTT loop
                client.mqtt_client.loop_start()

                st.success("MQTT client initialized. Waiting for messages...")
                st.rerun() # Rerun after initialization

            except ValueError as ve:
                st.error(f"Invalid MQTT broker address: {ve}")
                st.warning("Please check the MQTT broker address.")
                st.session_state.mqtt_client = None
                st.stop()
            except Exception as conn_e:
                st.error(f"Failed to connect to MQTT broker: {conn_e}")
                st.warning("Please check the MQTT broker or network status.")
                st.session_state.mqtt_client = None
                st.stop()

        except Exception as e:
            st.error(f"Failed to initialize MQTT client: {e}")
            st.warning("Unable to connect to MQTT broker. Please check your internet connection and broker address.")
            # On failure, either set client to None or stop the app
            st.session_state.mqtt_client = None
            st.stop() # 또는 st.experimental_singleton을 사용한 경우라면 None을 반환
    # Initialize MQTT message receive flag
    if 'mqtt_update_received' not in st.session_state:
        st.session_state.mqtt_update_received = False
    if 'mqtt_last_update_time' not in st.session_state:
        st.session_state.mqtt_last_update_time = 0

    client = st.session_state.get('mqtt_client')
    designer = st.session_state.room_designer
    db = get_event_db()  # Initialize the event database connection

    # --- UI Layout: Main content area and right control column ---
    col1, col2 = st.columns([0.85, 0.15])
    main_content_col = col1.empty()

    with col2:
        st.subheader("Control")
    col21, col22 = col2.columns([0.2, 0.8])
    light_icon = col21.empty()
    light_btn = col22.empty()
    with col21:
        st.write("")
    with col22:
        st.write("")
    ac_icon = col21.empty()
    ac_btn = col22.empty()

    clicked_sensor = bridge("sensor-id-bridge", default="")
    last_svg = ""
    if clicked_sensor:
        #st.write(f"Clicked sensor ID: {clicked_sensor}")
        # Querying the sensor data from database
        sensor_data = query_event_db(db, clicked_sensor)
        if sensor_data and not df.empty:
            # Convert timestamp to datetime for plotting
            df = pd.DataFrame([
                {
                    'timestamp': datetime.fromtimestamp(sensor_value['timestamp']),
                    'value': sensor_value['value']
                }
                for sensor_value in sensor_data
            ])
            # Plot the data using Streamlit's line chart
            st.line_chart(df.set_index('timestamp')['value'])
        else:
            st.info("No data found for this sensor")
    light_switch = light_btn.button("Light Switch", key="light_switch", use_container_width=True)
    ac_switch = ac_btn.button("AC Switch", key="ac_switch", use_container_width=True)

    while True:
        all_sensors = client.get_all_sensors() if client else {}
        if all_sensors:
            meeting_room_svg = designer.generate_meeting_room_svg(sensors=all_sensors)
            if meeting_room_svg != last_svg:  # Only update if SVG has changed
                last_svg = meeting_room_svg
                with main_content_col:
                    st.components.v1.html(meeting_room_svg, height=1000, scrolling=False)
        else:
            with main_content_col:
                st.info("Waiting to receive meeting room status information...")


        all_agents = client.get_all_agents() if client else {}
        if all_agents:
            power_state = all_agents[TARGET_LIGHT_AGENT_ID].get('state', {}).get('power', 'unknown')
            with light_icon:
                st.markdown(
                    f"<div style='display: flex; align-items: center; height: 100%; justify-content: center; font-size: 2em;'>{'💡' if power_state == 'on' else '⚫'}</div>",
                    unsafe_allow_html=True
                )
            if light_switch and power_state == "off":
                client.send_command(TARGET_LIGHT_AGENT_ID, "turn_on")
            elif light_switch and power_state == "on":
                client.send_command(TARGET_LIGHT_AGENT_ID, "turn_off")

            power_state = all_agents[TARGET_AC_AGENT_ID].get('state', {}).get('power', 'unknown')
            with ac_icon:
                st.markdown(
                    f"<div style='display: flex; align-items: center; height: 100%; justify-content: center; font-size: 2em;'>{'❄️' if power_state == 'on' else '⚫'}</div>",
                    unsafe_allow_html=True
                )
            if ac_switch and power_state == "off":
                client.send_command(TARGET_AC_AGENT_ID, "turn_on")
            elif ac_switch and power_state == "on":
                client.send_command(TARGET_AC_AGENT_ID, "turn_off")

        time.sleep(1)

if __name__ == "__main__":
    st.set_page_config(page_title="Live IoT Dashboard", layout="wide")
    st.title("Live IoT Dashboard - Real-time Updates")
    client = None
    if 'room_designer' not in st.session_state:
        st.session_state.room_designer = MeetingRoomDesign()
    if 'test_mode' not in st.session_state:
        st.session_state.test_mode = False

        if 'test_sensors' not in st.session_state:
            st.session_state.test_sensors = {}

            for sensor_id in st.session_state.room_designer.element_positions.keys():
                if sensor_id.startswith('activity'):
                    st.session_state.test_sensors[sensor_id] = {'value': False, 'sensor_type': 'activity'}
                elif sensor_id.startswith('door'):
                    st.session_state.test_sensors[sensor_id] = {'value': False, 'sensor_type': 'door'}
                elif sensor_id.startswith('motion'):
                    st.session_state.test_sensors[sensor_id] = {'value': False, 'sensor_type': 'motion'}
                elif sensor_id.startswith('infrared'):
                    st.session_state.test_sensors[sensor_id] = {'value': 0, 'sensor_type': 'infrared'}
                elif sensor_id.startswith('temperature'):
                    st.session_state.test_sensors[sensor_id] = {'value': 22.0, 'sensor_type': 'temperature'}
                elif sensor_id.startswith('light'):
                    st.session_state.test_sensors[sensor_id] = {'value': 50, 'sensor_type': 'light'}

    main()

