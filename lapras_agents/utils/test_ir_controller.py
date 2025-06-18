from Phidget22.Phidget import *
from Phidget22.Devices.IR import *
import time
import logging

# Logger will use the configuration set by the startup script
logger = logging.getLogger(__name__)

class PhidgetIRController:
    """Base class for PhidgetIR control functionality"""
    
    def __init__(self, serial=322207, code_handler=None):
        """
        Initialize PhidgetIR controller
        
        Args:
            serial (int): Device serial number, -1 for any device
            code_handler: Optional code event handler function
        """
        logger.debug("Initializing PhidgetIR controller")
        
        self.ir_phidget = IR()
        
        # Set up event handlers
        self.ir_phidget.setOnAttachHandler(self._on_attach)
        self.ir_phidget.setOnDetachHandler(self._on_detach)
        self.ir_phidget.setOnErrorHandler(self._on_error)
        
        if code_handler:
            self.ir_phidget.setOnCodeHandler(code_handler)
        
        self._open_ir_phidget(serial)
    
    def _open_ir_phidget(self, serial):
        """Open the IR Phidget device"""
        try:
            logger.debug(f"Attempting to open IRPhidget with serial: {serial}")
            
            if serial >= 0:
                self.ir_phidget.setDeviceSerialNumber(serial)
            
            # Open and wait for attachment
            logger.debug("Waiting for attachment...")
            self.ir_phidget.openWaitForAttachment(5000)  # 5 second timeout
            
        except PhidgetException as e:
            logger.error(f"Failed to open IRPhidget: {e}")
            raise
    
    def transmit_raw(self, raw_data):
        """
        Transmit raw IR data
        
        Args:
            raw_data (list): List of pulse/space times in microseconds
            
        Returns:
            bool: True if transmission successful, False otherwise
        """
        try:
            if not self.ir_phidget.getAttached():
                logger.error("IRPhidget not attached")
                return False
            
            self.ir_phidget.transmitRaw(raw_data, 0, 0, 100000)  # carrier=0, duty=0, gap=100ms
            return True
            
        except PhidgetException as e:
            logger.error(f"Transmission failed: {e}")
            return False
    
    def transmit_code(self, code, code_info):
        """
        Transmit IR code with code info
        
        Args:
            code (str): Hex string code
            code_info: CodeInfo object
            
        Returns:
            bool: True if transmission successful, False otherwise
        """
        try:
            self.ir_phidget.transmit(code, code_info)
            return True
            
        except PhidgetException as e:
            logger.error(f"Code transmission failed: {e}")
            return False
    
    def close(self):
        """Close the IR Phidget device"""
        try:
            if self.ir_phidget.getIsOpen():
                self.ir_phidget.close()
                logger.debug("IRPhidget closed")
        except PhidgetException as e:
            logger.error(f"Error closing IRPhidget: {e}")
    
    def _on_attach(self, phidget):
        """Handle attach event"""
        logger.debug("IRPhidget attached")
    
    def _on_detach(self, phidget):
        """Handle detach event"""
        logger.debug("IRPhidget detached")
    
    def _on_error(self, phidget, code, description):
        """Handle error event"""
        logger.debug(f"IRPhidget error: {code} - {description}")


class AirConditionerController(PhidgetIRController):
    """Air Conditioner control using PhidgetIR"""
    
    # IR command data (converted from Java arrays)
    TEMP_UP = [4430, 4480, 540, 1710, 490, 590, 540, 590, 510, 590, 540, 590, 540, 590, 510,
               590, 540, 590, 510, 620, 520, 1720, 510, 590, 540, 590, 510, 620, 510, 1750, 480, 590, 540, 590, 510, 1720,
               540, 1720, 520, 590, 510, 590, 540, 22150, 4450, 4480, 520, 1710, 520, 610, 490, 590, 540, 590, 510, 620,
               520, 580, 540, 590, 520, 580, 540, 590, 540, 1700, 530, 600, 510, 590, 530, 600, 530, 1700, 540, 590, 520,
               580, 540, 1720, 520, 1720, 510, 590, 530, 600, 510, 22210, 4420, 4480, 540, 1690, 520, 590, 540, 580, 520,
               590, 540, 610, 510, 620, 490, 590, 530, 630, 480, 650, 490, 1710, 520, 590, 530, 620, 490, 610, 520, 1740,
               490, 620, 500, 630, 490, 1740, 510, 1720, 510, 620, 490, 610, 520]
    
    TEMP_DOWN = [4430, 4480, 540, 1690, 510, 590, 540, 590, 510, 590, 540, 590, 540, 590,
                 510, 600, 540, 610, 490, 620, 510, 1720, 510, 590, 540, 590, 510, 1730, 530, 600, 510, 590, 540, 590, 510,
                 1720, 540, 1690, 540, 590, 510, 600, 530, 22160, 4450, 4480, 520, 1690, 540, 590, 510, 590, 540, 590, 520,
                 610, 520, 580, 550, 610, 490, 590, 540, 590, 540, 1690, 540, 590, 510, 590, 540, 1720, 520, 590, 540, 610,
                 490, 590, 540, 1720, 510, 1720, 510, 590, 540, 620, 490]
    
    TURN_ON = [460, 530, 470, 520, 470, 520, 480, 510, 480, 520, 460, 530, 470, 520, 470,
               520, 470, 520, 480, 520, 470, 520, 470, 3010, 2940, 8960, 530, 1490, 500, 490, 500, 490, 440, 550, 460, 530,
               470, 530, 460, 530, 470, 520, 470, 520, 470, 1540, 500, 470, 460, 530, 470, 1540, 500, 460, 480, 1510, 520,
               1460, 530, 490, 440, 1570, 420, 1540, 470, 1510, 480, 1500, 470, 1520, 470, 1510, 480, 1500, 480, 1510, 470,
               520, 470, 520, 470, 550, 450, 1590, 390, 1540, 450, 1530, 470, 520, 470, 530, 470, 520, 470, 520, 470, 520,
               480, 510, 480, 510, 480, 520, 460, 1520, 470, 1540, 450, 510, 480, 1510, 470, 550, 440, 1570, 460, 500, 500,
               490, 500, 490, 480, 520, 470, 520, 470, 520, 470, 520, 470, 1540, 450, 1560, 430, 1500, 470, 1510, 530]
    
    TURN_OFF = [530, 460, 530, 3000, 2890, 8960, 480, 1550, 430, 510, 470, 550, 510, 480,
                500, 490, 500, 490, 450, 540, 450, 540, 480, 510, 480, 1510, 480, 510, 530, 460, 530, 460, 540, 450, 530,
                1450, 530, 470, 530, 1450, 480, 1500, 480, 1560, 420, 1560, 420, 1560, 500, 1480, 510, 1480, 440, 1540, 450,
                1530, 450, 520, 470, 520, 470, 520, 480, 510, 480, 540, 450, 540, 440, 550, 440, 550, 450, 540, 450, 540,
                500, 490, 470, 520, 480, 510, 480, 520, 480, 1500, 530, 1480, 500, 460, 480, 510, 480, 510, 480, 510, 480,
                510, 490, 530, 450, 540, 450, 540, 450, 550, 450, 540, 450, 540, 500, 490, 500, 490, 500, 1480, 490, 1520,
                450]
    
    def __init__(self, phidget_serial=-1):
        """
        Initialize Air Conditioner Controller
        
        Args:
            phidget_serial (int): Phidget device serial number, -1 for any device
        """
        super().__init__(phidget_serial)
    
    def temp_down(self):
        """Decrease temperature"""
        return self.transmit_raw(self.TEMP_DOWN)
    
    def temp_up(self):
        """Increase temperature"""
        return self.transmit_raw(self.TEMP_UP)
    
    def turn_on(self):
        """Turn on air conditioner"""
        return self.transmit_raw(self.TURN_ON)
    
    def turn_off(self):
        """Turn off air conditioner"""
        return self.transmit_raw(self.TURN_OFF)


# Command line interface
import argparse
import sys

def execute_command(ac_controller, command):
    """Execute a single command on the air conditioner"""
    command_map = {
        'on': ('Turning ON air conditioner', ac_controller.turn_on),
        'off': ('Turning OFF air conditioner', ac_controller.turn_off),
        'temp_up': ('Increasing temperature', ac_controller.temp_up),
        'temp_down': ('Decreasing temperature', ac_controller.temp_down),
        'up': ('Increasing temperature', ac_controller.temp_up),  # Alias
        'down': ('Decreasing temperature', ac_controller.temp_down)  # Alias
    }
    
    if command not in command_map:
        print(f"Error: Unknown command '{command}'")
        print("Available commands: on, off, temp_up, temp_down, up, down")
        return False
    
    description, func = command_map[command]
    print(f"{description}...")
    
    success = func()
    if success:
        print(f"✓ Command '{command}' sent successfully")
        return True
    else:
        print(f"✗ Command '{command}' failed")
        return False

def main():
    """Main function with command line argument support"""
    parser = argparse.ArgumentParser(
        description='Control air conditioner using PhidgetIR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s on                    # Turn on air conditioner
  %(prog)s off                   # Turn off air conditioner
  %(prog)s temp_up               # Increase temperature
  %(prog)s temp_down             # Decrease temperature
  %(prog)s up                    # Increase temperature (alias)
  %(prog)s down                  # Decrease temperature (alias)
  %(prog)s --serial 12345 on     # Use specific device serial number
  %(prog)s --test                # Run all commands in sequence
  %(prog)s on off                # Execute multiple commands
        """
    )
    
    parser.add_argument(
        'commands', 
        nargs='*', 
        choices=['on', 'off', 'temp_up', 'temp_down', 'up', 'down'],
        help='Commands to execute (on, off, temp_up, temp_down, up, down)'
    )
    
    parser.add_argument(
        '--serial', '-s',
        type=int,
        default=-1,
        help='PhidgetIR device serial number (default: any device)'
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=1.0,
        help='Delay between commands in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Run test sequence with all commands'
    )
    
    parser.add_argument(
        '--list-commands', '-l',
        action='store_true',
        help='List all available commands and exit'
    )
    
    args = parser.parse_args()
    
    # Handle list commands
    if args.list_commands:
        print("Available commands:")
        print("  on, off          - Turn air conditioner on/off")
        print("  temp_up, up      - Increase temperature")
        print("  temp_down, down  - Decrease temperature")
        return
    
    # Handle no arguments
    if not args.commands and not args.test:
        parser.print_help()
        return
    
    try:
        # Create controller
        print(f"Initializing Air Conditioner Controller (serial: {args.serial if args.serial >= 0 else 'any'})...")
        ac_controller = AirConditionerController(args.serial)
        print("Air Conditioner Controller ready!")
        
        success_count = 0
        total_commands = 0
        
        if args.test:
            # Run test sequence
            print("\nRunning test sequence...")
            test_commands = ['on', 'temp_up', 'temp_down', 'off']
            
            for i, command in enumerate(test_commands):
                print(f"\n[{i+1}/{len(test_commands)}] ", end="")
                if execute_command(ac_controller, command):
                    success_count += 1
                total_commands += 1
                
                # Add delay between commands (except for the last one)
                if i < len(test_commands) - 1:
                    time.sleep(args.delay)
        
        else:
            # Execute provided commands
            for i, command in enumerate(args.commands):
                if len(args.commands) > 1:
                    print(f"\n[{i+1}/{len(args.commands)}] ", end="")
                
                if execute_command(ac_controller, command):
                    success_count += 1
                total_commands += 1
                
                # Add delay between commands (except for the last one)
                if i < len(args.commands) - 1:
                    time.sleep(args.delay)
        
        # Summary
        if total_commands > 1:
            print(f"\nSummary: {success_count}/{total_commands} commands executed successfully")
        
        # Close controller
        ac_controller.close()
        print("\nController closed.")
        
        # Exit with appropriate code
        sys.exit(0 if success_count == total_commands else 1)
        
    except PhidgetException as e:
        print(f"Phidget error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()