package kr.ac.kaist.cdsn.lapras.agents.smarttv;

public class SmartboardState {
    private static SmartboardState _instance = null;
    private boolean smartboardOn;
    private String smartboardInput;
    private SmartboardStateHandler handler = null;

    public static final boolean DEBUG_SMARTBOARD = false;

    private SmartboardState() {
        smartboardOn = false;
        smartboardInput = "PC";
    }

    public synchronized static SmartboardState getInstance() {
        if (_instance == null) {
            _instance = new SmartboardState();
        }

        return _instance;
    }

    public void setSmartboardStateHandler(SmartboardStateHandler handler) {
        this.handler = handler;
    }

    public boolean isSmartboardOn() {
        return smartboardOn;
    }

    public void setSmartboardOn(boolean smartboardOn) {
        if (this.smartboardOn != smartboardOn) {
            this.smartboardOn = smartboardOn;
            if (handler != null) {
                handler.onSmartboardPowerChanged(this.smartboardOn);
            }
        }
    }

    public void setSmartboardInput(String input) {
        if (!this.smartboardInput.equals(input)) {
            this.smartboardInput = input;
            if (handler != null) {
                handler.onSmartboardInputChanged(this.smartboardInput);
            }
        }
    }

    public String getSmartboardInput() {
        return this.smartboardInput;
    }

    @Override
    public String toString() {
        String str = "";
        str += "Smartboard on: " + isSmartboardOn() + "\n";
        str += "Mode: " + getSmartboardInput();

        return str;
    }

    public interface SmartboardStateHandler {
        public void onSmartboardPowerChanged(boolean newState);

        public void onSmartboardInputChanged(String newInput);
    }
}