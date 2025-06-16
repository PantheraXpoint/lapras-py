#!/usr/bin/env python3
"""
Test script for dynamic rule configuration changes
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lapras_middleware.rules_client import RulesClient
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_dynamic_rules():
    """Test dynamic rule switching functionality."""
    
    print("🧪 Starting Dynamic Rules Test")
    print("=" * 50)
    
    # Initialize the rules client
    client = RulesClient(client_id="TestClient")
    
    try:
        # Test 1: List available presets
        print("\n📋 Test 1: List Available Presets")
        event_id = client.list_available_presets()
        print(f"✅ Command sent (Event ID: {event_id})")
        time.sleep(2)  # Wait for processing
        
        # Test 2: List currently loaded rules
        print("\n📋 Test 2: List Currently Loaded Rules")
        event_id = client.list_loaded_rules()
        print(f"✅ Command sent (Event ID: {event_id})")
        time.sleep(2)
        
        # Test 3: Switch to motion-only preset
        print("\n🔄 Test 3: Switch to Motion-Only Rules")
        event_id = client.switch_to_preset("hue_motion_only")
        print(f"✅ Switching to hue_motion_only (Event ID: {event_id})")
        time.sleep(3)
        
        # Verify the change
        print("\n📋 Verify: List rules after switch")
        event_id = client.list_loaded_rules()
        print(f"✅ Command sent (Event ID: {event_id})")
        time.sleep(2)
        
        # Test 4: Switch to activity-only preset
        print("\n🔄 Test 4: Switch to Activity-Only Rules")
        event_id = client.switch_to_preset("hue_activity_only")
        print(f"✅ Switching to hue_activity_only (Event ID: {event_id})")
        time.sleep(3)
        
        # Test 5: Switch to all sensors preset
        print("\n🔄 Test 5: Switch to All Sensors Rules")
        event_id = client.switch_to_preset("hue_all_sensors") 
        print(f"✅ Switching to hue_all_sensors (Event ID: {event_id})")
        time.sleep(3)
        
        # Test 6: Switch to custom rule files
        print("\n🔄 Test 6: Switch to Custom Rule Files")
        custom_rules = [
            "lapras_middleware/rules/hue_ir_motion.ttl",
            "lapras_middleware/rules/aircon_activity.ttl"
        ]
        event_id = client.switch_to_rules(custom_rules)
        print(f"✅ Switching to custom rules (Event ID: {event_id})")
        time.sleep(3)
        
        # Test 7: Clear all rules
        print("\n🗑️ Test 7: Clear All Rules")
        event_id = client.clear_all_rules()
        print(f"✅ Clearing all rules (Event ID: {event_id})")
        time.sleep(2)
        
        # Test 8: Load rules back
        print("\n📥 Test 8: Load Rules Back")
        event_id = client.switch_to_preset("both_devices_motion")
        print(f"✅ Loading both_devices_motion preset (Event ID: {event_id})")
        time.sleep(2)
        
        print("\n🎉 All tests completed!")
        print("Check the ContextRuleManager logs to see the rule changes in action.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    
    finally:
        # Clean up
        client.stop()
        print("\n🛑 Test client stopped.")

def test_interactive_mode():
    """Interactive testing mode."""
    
    print("🎮 Interactive Rule Testing Mode")
    print("=" * 50)
    
    client = RulesClient(client_id="InteractiveClient")
    
    presets = {
        "hue_motion_only": "Hue light - Motion sensor only",
        "hue_activity_only": "Hue light - Activity sensor only", 
        "hue_ir_only": "Hue light - IR proximity sensor only",
        "hue_ir_motion": "Hue light - IR + Motion (OR logic)",
        "hue_activity_motion": "Hue light - Activity + Motion (OR logic)",
        "hue_ir_activity": "Hue light - IR + Activity (OR logic)", 
        "hue_all_sensors": "Hue light - All sensors (OR logic)",
        "aircon_motion_only": "Aircon - Motion sensor only",
        "aircon_activity_only": "Aircon - Activity sensor only",
        "aircon_ir_only": "Aircon - IR proximity sensor only",
        "aircon_all_sensors": "Aircon - All sensors (OR logic)",
        "both_devices_motion": "Both devices - Motion only",
        "both_devices_all": "Both devices - All sensors"
    }
    
    try:
        while True:
            print("\n🎯 Available Commands:")
            print("1. List presets")
            print("2. List loaded rules")
            print("3. Switch to preset")
            print("4. Switch to custom files")
            print("5. Clear rules")
            print("6. Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                print("📋 Listing available presets...")
                client.list_available_presets()
                
            elif choice == "2":
                print("📋 Listing loaded rules...")
                client.list_loaded_rules()
                
            elif choice == "3":
                print("\n📋 Available Presets:")
                preset_list = list(presets.keys())
                for i, (preset_key, description) in enumerate(presets.items(), 1):
                    print(f"  {i:2d}. {preset_key:<20} - {description}")
                
                try:
                    preset_choice = int(input(f"\nSelect preset (1-{len(presets)}): ")) - 1
                    if 0 <= preset_choice < len(presets):
                        selected_preset = preset_list[preset_choice]
                        print(f"🔄 Switching to {selected_preset}...")
                        client.switch_to_preset(selected_preset)
                    else:
                        print("❌ Invalid preset number")
                except ValueError:
                    print("❌ Please enter a valid number")
                    
            elif choice == "4":
                print("\n📁 Custom Rule Files Selection")
                print("Available rule files:")
                available_files = [
                    "lapras_middleware/rules/hue_motion.ttl",
                    "lapras_middleware/rules/hue_activity.ttl", 
                    "lapras_middleware/rules/hue_ir.ttl",
                    "lapras_middleware/rules/hue_ir_motion.ttl",
                    "lapras_middleware/rules/hue_activity_motion.ttl",
                    "lapras_middleware/rules/hue_ir_activity.ttl",
                    "lapras_middleware/rules/hue_ir_activity_motion.ttl",
                    "lapras_middleware/rules/aircon_motion.ttl",
                    "lapras_middleware/rules/aircon_activity.ttl",
                    "lapras_middleware/rules/aircon_ir.ttl",
                    "lapras_middleware/rules/aircon_ir_motion.ttl",
                    "lapras_middleware/rules/aircon_activity_motion.ttl",
                    "lapras_middleware/rules/aircon_ir_activity.ttl",
                    "lapras_middleware/rules/aircon_ir_acitivity_motion.ttl"
                ]
                
                for i, file in enumerate(available_files, 1):
                    filename = file.split('/')[-1]
                    print(f"  {i:2d}. {filename}")
                
                print("\nEnter file numbers separated by spaces (e.g., '1 3 5'):")
                file_input = input("Selection: ").strip()
                
                try:
                    selected_indices = [int(x.strip()) - 1 for x in file_input.split()]
                    selected_files = [available_files[i] for i in selected_indices if 0 <= i < len(available_files)]
                    
                    if selected_files:
                        print(f"🔄 Switching to custom files: {[f.split('/')[-1] for f in selected_files]}")
                        client.switch_to_rules(selected_files)
                    else:
                        print("❌ No valid files selected")
                        
                except (ValueError, IndexError):
                    print("❌ Invalid input format")
                    
            elif choice == "5":
                print("🗑️ Clearing all rules...")
                client.clear_all_rules()
                
            elif choice == "6":
                break
                
            else:
                print("❌ Invalid choice")
            
            time.sleep(1)  # Brief pause between commands
                
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
    
    finally:
        client.stop()
        print("🛑 Interactive client stopped.")

if __name__ == "__main__":
    print("Choose testing mode:")
    print("1. Automated test sequence")
    print("2. Interactive mode")
    
    mode = input("Enter your choice (1 or 2): ").strip()
    
    if mode == "1":
        test_dynamic_rules()
    elif mode == "2":
        test_interactive_mode()
    else:
        print("Invalid choice. Running automated test...")
        test_dynamic_rules() 