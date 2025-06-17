import sys
import time
import json
sys.path.append('/home/cdsn/lapras-py')
from dashboard_interface.new_dashboard_subscriber import EnhancedDashboardSubscriber

def test_manual_control():
    """Test manual control commands and wait for results."""
    
    print("🚀 Starting Manual Control Test")
    print("=" * 50)
    
    # Create subscriber
    subscriber = EnhancedDashboardSubscriber()
    
    # Give MQTT connection time to establish
    print("📡 Connecting to MQTT broker...")
    time.sleep(3)
    
    # Check if we have system state first
    print("🔍 Checking current system state...")
    context_data = getattr(subscriber, 'context_data', {})
    if context_data and 'agents' in context_data:
        agents = context_data['agents']
        hue_agent = agents.get('hue_light')
        if hue_agent:
            current_power = hue_agent.get('state', {}).get('power', 'unknown')
            is_responsive = hue_agent.get('is_responsive', False)
            status = "🟢 ONLINE" if is_responsive else "🔴 OFFLINE"
            print(f"   {status} hue_light: current power = {current_power}")
        else:
            print("   ❌ hue_light agent not found in system state")
            print(f"   Available agents: {list(agents.keys())}")
    else:
        print("   ⚠️ No system state available yet")
    
    print("💡 Sending manual light command...")
    
    # Test light commands - toggle between on/off
    # command_id = subscriber.send_command("hue_light", "turn_on")
    command_id = subscriber.send_command("hue_light", "turn_off")
    
    if command_id:
        print(f"📤 Command sent with ID: {command_id}")
        print("⏳ Waiting for command result and system response...")
    else:
        print("❌ Failed to send command - no command ID returned")
        return
    
    # Wait and monitor for results
    start_time = time.time()
    max_wait_time = 15  # Wait up to 15 seconds
    
    while time.time() - start_time < max_wait_time:
        time.sleep(1)
        
        # Check for command results
        command_results = subscriber.get_command_results()
        if command_id and command_id in command_results:
            result = command_results[command_id]
            success = result.get('success', False)
            message = result.get('message', 'No message')
            
            print(f"\n✅ Command Result Received:")
            print(f"   Success: {success}")
            print(f"   Message: {message}")
            
            if success:
                print("🎉 Manual command was successful!")
            else:
                print("❌ Manual command failed!")
            break
    else:
        print("\n⏰ Timeout waiting for command result")
    
    # Show current system state
    print(f"\n📊 Current System State:")
    context_data = getattr(subscriber, 'context_data', {})
    if context_data and 'agents' in context_data:
        agents = context_data['agents']
        for agent_id, agent_info in agents.items():
            if agent_id == 'hue_light':
                power_state = agent_info.get('state', {}).get('power', 'unknown')
                agent_type = agent_info.get('agent_type', 'unknown')
                is_responsive = agent_info.get('is_responsive', False)
                status = "🟢 ONLINE" if is_responsive else "🔴 OFFLINE"
                print(f"   {status} {agent_id} ({agent_type}): power = {power_state}")
                break
    else:
        print("   No agent state data available yet")
    
    print(f"\n📋 Manual Override Status:")
    print(f"   During manual override, automatic rules are disabled for 300 seconds")
    print(f"   This allows you to control the light without rule interference")
    
    print(f"\n🔚 Test completed. Press Ctrl+C to exit.")
    
    # Keep running to see ongoing updates
    try:
        while True:
            time.sleep(5)
            # Show periodic updates if available
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] Still monitoring... (Press Ctrl+C to stop)")
            
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
    finally:
        subscriber.stop()
        print("🔚 Manual control test finished")

if __name__ == "__main__":
    test_manual_control() 