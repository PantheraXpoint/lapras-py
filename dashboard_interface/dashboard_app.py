import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.new_dashboard_subscriber import EnhancedDashboardSubscriber as eds
from design import MeetingRoomDesign
import time # May be required by DashboardClient or Streamlit app
import streamlit as st
from st_bridge import bridge

def main():
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

    # Timer for periodic auto update
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = time.time()

    # Initialize MQTT message receive flag
    if 'mqtt_update_received' not in st.session_state:
        st.session_state.mqtt_update_received = False
    if 'mqtt_last_update_time' not in st.session_state:
        st.session_state.mqtt_last_update_time = 0

    # Perform rerun in main thread when MQTT message is received
    if st.session_state.get('mqtt_update_received', False):
        # 플래그 초기화
        st.session_state.mqtt_update_received = False
        mqtt_update_time = st.session_state.get('mqtt_last_update_time', 0)
        current_time = time.time()

        # 디버깅 정보
        print(f"메인 스레드에서 MQTT 업데이트 감지 - 경과 시간: {current_time - mqtt_update_time:.2f}초")

        # 1초 이내에 업데이트된 경우에만 rerun 실행
        if current_time - mqtt_update_time < 5:  # 5초 이내의 업데이트만 처리
            print("메인 스레드에서 rerun 실행")
            st.rerun()

    client = st.session_state.get('mqtt_client')
    designer = st.session_state.room_designer

    # --- UI Layout: Main content area and right control column ---
    col1, controls_col = st.columns([0.85, 0.15])
    main_content_col = col1.empty()

    with controls_col:
        client = st.session_state.get('mqtt_client')
        st.subheader("Control")

        # Use only the default light
        TARGET_LIGHT_AGENT_ID = "hue_light"  # 기본 조명 ID

        # --- Light Control Buttons ---
        if st.button("💡 ON", key="light_on_button", use_container_width=True):
            if client and TARGET_LIGHT_AGENT_ID:
                st.info("Turning on...")
                command_id = client.send_command(agent_id=TARGET_LIGHT_AGENT_ID, action_name="turn_on")
                if command_id:
                    st.toast("Turned on", icon="✅")

        st.write("")  # 간격 추가

        if st.button("⚫ OFF", key="light_off_button", use_container_width=True):
            if client and TARGET_LIGHT_AGENT_ID:
                st.info("Turning off...")
                command_id = client.send_command(agent_id=TARGET_LIGHT_AGENT_ID, action_name="turn_off")
                if command_id:
                    st.toast("Turned off", icon="✅")

    clicked_sensor = bridge("sensor-id-bridge", default="")
    last_svg = "";
    if clicked_sensor:
        st.write(f"Clicked sensor ID: {clicked_sensor}")

    while True:
        all_sensors = client.get_all_sensors() if client else {}
        main_content_col.empty() # Clear the main content area before redrawing
        if all_sensors:
            meeting_room_svg = designer.generate_meeting_room_svg(sensors=all_sensors)
            if meeting_room_svg != last_svg:  # Only update if SVG has changed
                last_svg = meeting_room_svg
                with main_content_col:
                    st.components.v1.html(meeting_room_svg, height=1000, scrolling=False)
        else:  # If there is no sensor data
            with main_content_col:
                st.info("Waiting to receive meeting room status information...")

        time.sleep(5)

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

