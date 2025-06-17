from dashboard_subscriber import EnhancedDashboardSubscriber as eds
from design import MeetingRoomDesign
import time # May be required by DashboardClient or Streamlit app
import random
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Must be placed as the first Streamlit command
st.set_page_config(page_title="Live IoT Dashboard", layout="wide")

# Refresh every 1 second (1000ms)
count = st_autorefresh(interval=1000, limit=None, key="autorefresh")
st.markdown(f"<div style='position: fixed; bottom: 10px; right: 10px; font-size: 12px; color: #666;'>Auto-refreshed {count} times</div>", unsafe_allow_html=True)
st.title("Live IoT Dashboard - Real-time Updates Test")
client = None

# Create instance of MeetingRoomDesign
if 'room_designer' not in st.session_state:
    st.session_state.room_designer = MeetingRoomDesign()

# Initialize test mode related variables (disabled by default)
if 'test_mode' not in st.session_state:
    st.session_state.test_mode = False
    
if 'test_sensors' not in st.session_state:
    # Initialize with all sensors disabled by default
    st.session_state.test_sensors = {}
    
    # Initialize based on all sensor IDs in element_positions
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

# Initialize DashboardClient instance and related session_state variables
if 'mqtt_client' not in st.session_state:
    st.info("Initializing MQTT client...")

    try:
        mqtt_broker = "143.248.57.73"  # MQTT broker address
        mqtt_port = 1883

        # Create the client object before connecting to the broker
        client = eds(mqtt_broker=mqtt_broker, mqtt_port=mqtt_port)

        # Debug: Check if Streamlit object is passed correctly
        print(f"Type of st object passed from dashboard_app.py: {type(st)}")
        print(f"st.rerun method exists: {hasattr(st, 'rerun')}")
        print(f"st.session_state exists: {hasattr(st, 'session_state')}")

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
        
 
# (Optional) Force rerun button (for debugging)
if st.button("Rerun"):
    st.rerun()

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

# 백업용으로 5초마다 업데이트 (기존 코드)
if time.time() - st.session_state.last_update_time > 5:
    st.session_state.last_update_time = time.time()
    st.rerun()

# --- UI Layout: Main content area and right control column ---
main_content_col, controls_col = st.columns([0.85, 0.15]) # 왼쪽 85%, 오른쪽 15% 비율

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

    # Test Mode section - changed to collapsible expander
    with st.expander("테스트 모드 (개발용)", expanded=False):
        # 테스트 모드 토글
        test_mode = st.checkbox("테스트 모드 활성화", value=st.session_state.test_mode)
        st.session_state.test_mode = test_mode
        
        if test_mode:
            # 의자 테스트 데이터를 표시하는 작은 UI
            st.warning("⚠️ 테스트 모드 활성화됨 - 실제 센서 데이터가 아닌 테스트 데이터가 표시됩니다.")
            
            # 탭으로 센서 종류별 제어 UI 구성
            sensor_tabs = st.tabs(["의자 센서", "문 센서", "모션 센서", "IR 센서", "온도 센서", "조명 센서"])
            
            # 의자 센서 탭
            with sensor_tabs[0]:
                st.subheader("의자 센서 제어")
                # 3개의 열로 의자 컨트롤 표시
                chair_cols = st.columns(3)
                
                for i, sensor_id in enumerate(st.session_state.room_designer.element_positions.keys()):
                    if not sensor_id.startswith('activity'):
                        continue
                    # 3개 열로 의자 컨트롤 배치
                    col = chair_cols[i % 3]
                    with col:
                        # 체크박스로 각 의자의 점유 상태 제어
                        is_occupied = st.checkbox(
                            f"의자 {sensor_id}", 
                            value=st.session_state.test_sensors.get(sensor_id, {'value': False})['value'],
                            key=f"chair_test_{sensor_id}"
                        )
                        st.session_state.test_sensors[sensor_id]['value'] = is_occupied
            
            # 문 센서 탭
            with sensor_tabs[1]:
                st.subheader("문 센서 제어")
                door_cols = st.columns(2)  # 2열로 나누어 표시
                for i, sensor_id in enumerate(st.session_state.room_designer.element_positions.keys()):
                    if not sensor_id.startswith('door'):
                        continue
                    col = door_cols[i % 2]
                    with col:
                        is_open = st.checkbox(
                            f"문 {sensor_id} (열림/닫힘)", 
                            value=st.session_state.test_sensors.get(sensor_id, {'value': False})['value'],
                            key=f"door_test_{sensor_id}"
                        )
                        st.session_state.test_sensors[sensor_id]['value'] = is_open
            
            # 모션 센서 탭
            with sensor_tabs[2]:
                st.subheader("모션 센서 제어")
                motion_cols = st.columns(2)
                
                for i, sensor_id in enumerate(st.session_state.room_designer.element_positions.keys()):
                    if not sensor_id.startswith('motion'):
                        continue
                    col = motion_cols[i % 2]
                    with col:
                        is_active = st.checkbox(
                            f"모션 {sensor_id}", 
                            value=st.session_state.test_sensors.get(sensor_id, {'value': False})['value'],
                            key=f"motion_test_{sensor_id}"
                        )
                        st.session_state.test_sensors[sensor_id]['value'] = is_active
            
            # IR 센서 탭
            with sensor_tabs[3]:
                st.subheader("IR 센서 제어")
                for sensor_id in st.session_state.room_designer.element_positions.keys():
                    if not sensor_id.startswith('infrared'):
                        continue
                    ir_value = st.slider(
                        f"IR {sensor_id}", 
                        min_value=0, 
                        max_value=200, 
                        value=int(st.session_state.test_sensors.get(sensor_id, {'value': 0})['value']),
                        step=1,
                        key=f"ir_test_{sensor_id}"
                    )
                    st.session_state.test_sensors[sensor_id]['value'] = ir_value
            
            # 온도 센서 탭
            with sensor_tabs[4]:
                st.subheader("온도 센서 제어")
                for sensor_id in st.session_state.room_designer.element_positions.keys():
                    if not sensor_id.startswith('temperature'):
                        continue
                    temp_value = st.slider(
                        f"온도 {sensor_id} (°C)", 
                        min_value=15.0, 
                        max_value=30.0, 
                        value=st.session_state.test_sensors.get(sensor_id, {'value': 22.0})['value'],
                        step=0.5,
                        key=f"temp_test_{sensor_id}"
                    )
                    st.session_state.test_sensors[sensor_id]['value'] = temp_value

            # 조명 센서 탭
            with sensor_tabs[5]:
                st.subheader("조명 센서")
                for sensor_id in st.session_state.room_designer.element_positions.keys():
                    if not sensor_id.startswith('light'):
                        continue
                    light_value = st.slider("조명 값", 0, 100, 50, key=f"light_{sensor_id}")
                    st.write(f"현재 값: {light_value}")
                    st.session_state.test_sensors[sensor_id]['value'] = light_value

    # 랜덤화 버튼 섹션
    with st.expander("랜덤 데이터 생성", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("모든 센서 랜덤화", use_container_width=True):
                for sensor_id, sensor_info in st.session_state.test_sensors.items():
                    sensor_type = sensor_info.get('sensor_type')
                    if sensor_type == 'activity' or sensor_type == 'door' or sensor_type == 'motion':
                        st.session_state.test_sensors[sensor_id]['value'] = random.choice([True, False])
                    elif sensor_type == 'infrared':
                        st.session_state.test_sensors[sensor_id]['value'] = random.randint(0, 200)
                    elif sensor_type == 'temperature':
                        st.session_state.test_sensors[sensor_id]['value'] = round(random.uniform(15.0, 30.0), 1)
                st.rerun()
        
        with col2:
            if st.button("모든 센서 초기화", use_container_width=True):
                for sensor_id, sensor_info in st.session_state.test_sensors.items():
                    sensor_type = sensor_info.get('sensor_type')
                    if sensor_type == 'activity' or sensor_type == 'door' or sensor_type == 'motion':
                        st.session_state.test_sensors[sensor_id]['value'] = False
                    elif sensor_type == 'infrared':
                        st.session_state.test_sensors[sensor_id]['value'] = 0
                    elif sensor_type == 'temperature':
                        st.session_state.test_sensors[sensor_id]['value'] = 22.0
                st.rerun()

# --- Main Content Area ---
with main_content_col:
    # Remove title

    # Get sensor data from subscriber class
    client = st.session_state.get('mqtt_client')

    # Retrieve all sensor data at once
    all_sensors = client.get_all_sensors() if client else {}

    # Debug - view all sensors
    # with st.expander("All Sensor Data", expanded=False):
    #     st.json(all_sensors)

    chair_occupancy_data = {}  # Map of occupancy status for SVG function

    # Use test data if in test mode
    if st.session_state.test_mode:
        chair_occupancy_data = st.session_state.test_sensors

        # Show a small UI indicating test data is being used
        st.warning("⚠️ Test mode enabled - displaying test data instead of real sensor data.")

        # Generate and display test SVG
        designer = st.session_state.room_designer
        meeting_room_svg = designer.generate_meeting_room_svg(
            sensors=st.session_state.test_sensors
        )
        st.components.v1.html(meeting_room_svg, height=1000, scrolling=False)

    elif client is None:
        st.warning("Cannot display meeting room status because the MQTT client is not connected.")
    elif all_sensors:
        # Convert sensor data for SVG visualization
        designer = st.session_state.room_designer

        # Display number of occupied chairs
        occupied_chairs = sum(1 for status in chair_occupancy_data.values() if status)
        # total_chairs = len(designer.ordered_chair_sensor_ids)
        # st.info(f"Current meeting room status: {occupied_chairs} chairs occupied out of {total_chairs}")

        # Generate and display SVG (using components.html to enable JavaScript)
        meeting_room_svg = designer.generate_meeting_room_svg(
            sensors=all_sensors
        )
        st.components.v1.html(meeting_room_svg, height=1000, scrolling=False)

    else:  # If there is no sensor data
        st.info("Waiting to receive meeting room status information...")

if st.session_state.get('messages'):
    st.success("Data received successfully from Javascript:" + str(st.session_state.messages))