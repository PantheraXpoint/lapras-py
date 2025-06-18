#!/usr/bin/env python3
"""
Interactive Manual Control Dashboard for virtual agents.
This program provides a terminal interface to send manual control commands to virtual agents.
"""

import sys
import time
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional

sys.path.append('/home/cdsn/lapras-py')

# Completely disable all logging to prevent spam
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

# Import the existing EnhancedDashboardSubscriber
from dashboard_interface.new_dashboard_subscriber import EnhancedDashboardSubscriber

class InteractiveManualControlDashboard:
    """Interactive dashboard for manual control of virtual agents."""
    
    def __init__(self):
        """Initialize the interactive dashboard."""
        self.subscriber = None
        self.running = True
        
        # Predefined agent types and their common commands
        self.agent_presets = {
            "hue_light": {
                "description": "Hue Smart Light",
                "commands": {
                    "turn_on": "Turn light ON",
                    "turn_off": "Turn light OFF",
                    "toggle": "Toggle light state",
                    "brightness_high": "Set brightness to high",
                    "brightness_medium": "Set brightness to medium", 
                    "brightness_low": "Set brightness to low"
                }
            },
            "aircon": {
                "description": "Air Conditioning System",
                "commands": {
                    "turn_on": "Turn AC ON",
                    "turn_off": "Turn AC OFF",
                    "toggle": "Toggle AC state",
                    "cool": "Set to cooling mode",
                    "heat": "Set to heating mode",
                    "fan": "Set to fan mode",
                    "temp_up": "Increase temperature",
                    "temp_down": "Decrease temperature"
                }
            },
            "dashboard": {
                "description": "Dashboard Monitor Agent",
                "commands": {
                    "status": "Get status information",
                    "refresh": "Refresh agent state",
                    "reset": "Reset agent state"
                }
            }
        }
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Print the dashboard header."""
        self.clear_screen()
        print("🎮 Interactive Manual Control Dashboard")
        print("=" * 50)
    
    def initialize_subscriber(self):
        """Initialize the enhanced dashboard subscriber."""
        if not self.subscriber:
            print("📡 Connecting to MQTT broker...")
            try:
                self.subscriber = EnhancedDashboardSubscriber()
                # Give it a moment to connect
                time.sleep(2)
                
                if hasattr(self.subscriber, 'mqtt_client') and self.subscriber.mqtt_client.is_connected():
                    print("✅ Connected successfully!")
                    return True
                else:
                    print("❌ Connection failed: MQTT connection not established")
                    return False
                    
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                return False
        return True
    
    def show_main_menu(self):
        """Display the main menu options."""
        self.print_header()
        print("1. 🎯 Send command to predefined agent")
        print("2. ⚙️  Send custom command")
        print("3. 📋 List available agent presets")
        print("4. ❓ Help - Show examples")
        print("5. 🚪 Quit")
        print("=" * 50)
    
    def get_user_choice(self) -> str:
        """Get user's menu choice."""
        while True:
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                if choice in ['1', '2', '3', '4', '5']:
                    return choice
                else:
                    print("❌ Invalid choice. Please enter a number between 1-5.")
            except (EOFError, KeyboardInterrupt):
                return '5'  # Quit on Ctrl+C or EOF
    
    def show_agent_presets(self):
        """Show available agent presets."""
        self.clear_screen()
        print("📋 Available Agent Presets:")
        print("-" * 40)
        
        for i, (agent_id, info) in enumerate(self.agent_presets.items(), 1):
            print(f"{i}. {agent_id:<15} - {info['description']}")
            commands = list(info['commands'].keys())
            print(f"   Commands: {', '.join(commands[:3])}{'...' if len(commands) > 3 else ''}")
        
        input("\nPress Enter to continue...")
    
    def select_agent_from_presets(self) -> Optional[str]:
        """Let user select an agent from presets."""
        self.clear_screen()
        print("🎯 Select Target Agent:")
        print("-" * 25)
        
        agent_list = list(self.agent_presets.keys())
        for i, agent_id in enumerate(agent_list, 1):
            description = self.agent_presets[agent_id]['description']
            print(f"{i}. {agent_id:<15} - {description}")
        
        while True:
            try:
                choice = input(f"\nSelect agent (1-{len(agent_list)}) or 'c' to cancel: ").strip()
                
                if choice.lower() == 'c':
                    return None
                
                agent_choice = int(choice) - 1
                if 0 <= agent_choice < len(agent_list):
                    return agent_list[agent_choice]
                else:
                    print(f"❌ Invalid choice. Please enter 1-{len(agent_list)} or 'c'.")
                    
            except ValueError:
                print("❌ Please enter a valid number or 'c' to cancel.")
            except (EOFError, KeyboardInterrupt):
                return None
    
    def select_command_for_agent(self, agent_id: str) -> Optional[str]:
        """Let user select a command for the specified agent."""
        if agent_id not in self.agent_presets:
            return None
        
        self.clear_screen()
        commands = self.agent_presets[agent_id]['commands']
        command_list = list(commands.keys())
        
        print(f"💫 Available Commands for {agent_id}:")
        print("-" * 35)
        
        for i, command in enumerate(command_list, 1):
            description = commands[command]
            print(f"{i}. {command:<20} - {description}")
        
        while True:
            try:
                choice = input(f"\nSelect command (1-{len(command_list)}) or 'c' to cancel: ").strip()
                
                if choice.lower() == 'c':
                    return None
                
                cmd_choice = int(choice) - 1
                if 0 <= cmd_choice < len(command_list):
                    return command_list[cmd_choice]
                else:
                    print(f"❌ Invalid choice. Please enter 1-{len(command_list)} or 'c'.")
                    
            except ValueError:
                print("❌ Please enter a valid number or 'c' to cancel.")
            except (EOFError, KeyboardInterrupt):
                return None
    
    def get_custom_agent_and_command(self) -> tuple[Optional[str], Optional[str]]:
        """Get custom agent ID and command from user."""
        try:
            self.clear_screen()
            print("⚙️  Custom Command Entry:")
            print("-" * 25)
            
            agent_id = input("Enter target agent ID: ").strip()
            if not agent_id:
                print("❌ Agent ID cannot be empty.")
                return None, None
            
            command = input("Enter command: ").strip()
            if not command:
                print("❌ Command cannot be empty.")
                return None, None
            
            return agent_id, command
            
        except (EOFError, KeyboardInterrupt):
            return None, None
    
    def send_manual_command(self, agent_id: str, command: str) -> bool:
        """Send a manual command and wait for results."""
        if not self.subscriber:
            if not self.initialize_subscriber():
                return False
        
        self.clear_screen()
        print(f"💫 Sending command to {agent_id}: {command}")
        print("=" * 40)
        
        # Check connection status
        if not hasattr(self.subscriber, 'mqtt_client') or not self.subscriber.mqtt_client.is_connected():
            print("❌ MQTT connection lost. Trying to reconnect...")
            if not self.initialize_subscriber():
                input("\nPress Enter to continue...")
                return False
        
        # Send the command using the existing send_command method
        command_id = self.subscriber.send_command(agent_id, command)
        
        if command_id:
            print(f"📤 Command sent with ID: {command_id}")
            print("⏳ Waiting for command result...")
        else:
            print("❌ Failed to send command")
            print("   Possible causes:")
            print("   • MQTT connection issue")
            print("   • Network connectivity problem")
            print("   • Incorrect broker address")
            input("\nPress Enter to continue...")
            return False
        
        # Wait and monitor for results
        start_time = time.time()
        max_wait_time = 15  # Wait up to 15 seconds
        
        while time.time() - start_time < max_wait_time:
            time.sleep(1)
            
            # Get command results from the subscriber
            command_results = self.subscriber.get_command_results()
            result = command_results.get(command_id)
            
            if result:
                success = result.get('success', False)
                message = result.get('message', 'No message')
                
                print(f"\n✅ Command Result Received:")
                print(f"   Success: {success}")
                print(f"   Message: {message}")
                
                if success:
                    print("🎉 Manual command was successful!")
                else:
                    print("❌ Manual command failed!")
                
                print(f"\n📋 Manual Override Status:")
                print(f"   During manual override, automatic rules are disabled for 300 seconds")
                print(f"   This allows you to control devices without rule interference")
                
                input("\nPress Enter to continue...")
                return success
        
        print("\n⏰ Timeout waiting for command result")
        print("   The command was sent but no response was received.")
        print("   This might mean:")
        print("   • The target agent is not running")
        print("   • The context manager is not running")
        print("   • Network connectivity issues")
        input("\nPress Enter to continue...")
        return False
    
    def show_help(self):
        """Show help and examples."""
        self.clear_screen()
        print("📖 HELP - MANUAL CONTROL EXAMPLES")
        print("=" * 50)
        
        print("\n🎯 How Manual Control Works:")
        print("   • Commands are sent directly to virtual agents")
        print("   • Manual commands trigger a 300-second rule override")
        print("   • During override, automatic rules are suspended")
        print("   • This prevents conflicts between manual and automatic control")
        
        print("\n🏷️  Common Agent Types:")
        for agent_id, info in self.agent_presets.items():
            print(f"   • {agent_id:<15} - {info['description']}")
        
        print("\n💫 Command Examples:")
        print("   Hue Light:")
        print("     • turn_on, turn_off, toggle")
        print("     • brightness_high, brightness_medium, brightness_low")
        print("   ")
        print("   Air Conditioning:")
        print("     • turn_on, turn_off, toggle")
        print("     • cool, heat, fan")
        print("     • temp_up, temp_down")
        
        print("\n⚙️  Custom Commands:")
        print("   You can also send custom commands to any agent")
        print("   Just enter the agent ID and command manually")
        
        print("\n🔧 Troubleshooting:")
        print("   • Make sure the Context Rule Manager is running")
        print("   • Make sure the target virtual agents are running")
        print("   • Check network connectivity to MQTT broker")
        
        input("\nPress Enter to continue...")
    
    def handle_predefined_command(self):
        """Handle sending a command to a predefined agent."""
        # Select agent
        agent_id = self.select_agent_from_presets()
        if not agent_id:
            return
        
        # Select command
        command = self.select_command_for_agent(agent_id)
        if not command:
            return
        
        # Confirm and send
        self.clear_screen()
        print(f"🎯 Ready to send:")
        print(f"   Agent: {agent_id}")
        print(f"   Command: {command}")
        
        confirm = input("\nProceed? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            self.send_manual_command(agent_id, command)
    
    def handle_custom_command(self):
        """Handle sending a custom command."""
        agent_id, command = self.get_custom_agent_and_command()
        if not agent_id or not command:
            return
        
        # Confirm and send
        self.clear_screen()
        print(f"🎯 Ready to send custom command:")
        print(f"   Agent: {agent_id}")
        print(f"   Command: {command}")
        
        confirm = input("\nProceed? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            self.send_manual_command(agent_id, command)
    
    def run(self):
        """Run the interactive dashboard."""
        self.print_header()
        print("🚀 Starting Interactive Manual Control Dashboard...")
        print("💡 Make sure the virtual agents and context manager are running!")
        
        # Initialize connection
        if not self.initialize_subscriber():
            input("\nPress Enter to exit...")
            return
        
        try:
            while self.running:
                self.show_main_menu()
                choice = self.get_user_choice()
                
                if choice == '1':
                    self.handle_predefined_command()
                elif choice == '2':
                    self.handle_custom_command()
                elif choice == '3':
                    self.show_agent_presets()
                elif choice == '4':
                    self.show_help()
                elif choice == '5':
                    self.running = False
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user")
            self.running = False
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        self.clear_screen()
        print("👋 Goodbye!")
    
    def stop(self):
        """Stop the dashboard."""
        self.running = False
        if self.subscriber:
            self.subscriber.stop()

def main():
    """Main entry point."""
    try:
        # Create and run interactive dashboard
        dashboard = InteractiveManualControlDashboard()
        dashboard.run()
        dashboard.stop()
        return 0
        
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 