package kr.ac.kaist.cdsn.lapras.agents.smarttv;

import com.phidgets.IRPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.*;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.context.ContextManager;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.awt.*;
import java.awt.event.KeyEvent;
import java.io.IOException;


public class SmartboardAgent extends AgentComponent implements
    SmartboardState.SmartboardStateHandler {
        private static final Logger LOGGER = LoggerFactory
                .getLogger(SmartboardAgent.class);




        /****************************************************************************************
                * AGENT IMPLEMNTATION CODE
         ****************************************************************************************/
    private IRPhidget irSmartBoard;
    private XBoxMonitor xboxMonitor;
    private PowerMonitor powerMonitor;
    private Robot robot;

    @ContextField(publishAsUpdated = true)
    public String channel;
    @ContextField(publishAsUpdated = true)
    public String volume;
    @ContextField(publishAsUpdated = true)
    public String status;
    @ContextField(publishAsUpdated = true)
    public String game;
    @ContextField(publishAsUpdated = true)
    public Context smartboardPower;
    @ContextField(publishAsUpdated = true)
    public Context smartboardInput;

    private AgentConfig agentConfig;
    private ContextManager contextManager;

    public SmartboardAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
    }




    @Override
    public void run() {
        smartboardPower.updateValue("Off");

        SmartboardState.getInstance().setSmartboardStateHandler(this);

        // Initialize robot
        try {
            this.robot = new Robot();
        } catch (AWTException e1) {

        }

        // Start power monitor
        powerMonitor = new PowerMonitor();
        powerMonitor.start();

        // Start x-box monitoring thread
        //xboxMonitor = new XBoxMonitor("n1Lounge8F", this);
        //xboxMonitor.start();

        try {
            startPhidgetIR();
        } catch (PhidgetException e) {

        } catch (InterruptedException e) {

        }


    }

    /**
     * Initializes specific features for Smartboard as follows: - starts
     * PhidgetIR for emitting IR signals - starts Phidget Interface Kit for
     * monitoring a light sensor attached to the screen (for checking on/off) -
     * initializes a soft-state (on/off, display mode)
     *
     * @throws PhidgetException
     * @throws InterruptedException
     */
    public void startPhidgetIR() throws PhidgetException, InterruptedException {

        irSmartBoard = new IRPhidget();
        irSmartBoard.addAttachListener(new AttachListener() {
            @Override
            public void attached(AttachEvent ae) {
                LOGGER.info("Phidget Attached: {}", ae.toString());
            }
        });
        irSmartBoard.addDetachListener(new DetachListener() {
            @Override
            public void detached(DetachEvent de) {
                LOGGER.info("Phidget Detached: {}", de.toString());
            }
        });
        irSmartBoard.addErrorListener(new ErrorListener() {
            @Override
            public void error(ErrorEvent ee) {
                LOGGER.error("Phidget Error Event: {}", ee.toString());
            }
        });
        // LOGGER.info("Attempting to open Phidget ID: " +
        // ir.getSerialNumber());
        irSmartBoard.openAny();
        LOGGER.info("Waiting for IR attachment...");
        irSmartBoard.waitForAttachment();
        LOGGER.debug("Serial: " + irSmartBoard.getSerialNumber());

    }
    @FunctionalityMethod
    public void turnOnSmartBoard() throws PhidgetException {
        if (smartboardPower.getValue().equals("Off")) {
            this.irSmartBoard.transmitRaw(Constants.ON_OFF);
            smartboardPower.updateValue("On");
        }
        /*
        if (!SmartboardState.getInstance().isSmartboardOn()) {
            this.irSmartBoard.transmitRaw(Constants.ON_OFF);
            SmartboardState.getInstance().setSmartboardOn(true);
            // No need to publish here since handler will publish it
        }
        */
    }
    @FunctionalityMethod
    public void turnOffSmartBoard() throws PhidgetException {
        if (smartboardPower.getValue().equals("On")) {
            this.irSmartBoard.transmitRaw(Constants.ON_OFF);
            smartboardPower.updateValue("Off");
        }
        /*
        if (SmartboardState.getInstance().isSmartboardOn()) {
            this.irSmartBoard.transmitRaw(Constants.ON_OFF);
            SmartboardState.getInstance().setSmartboardOn(false);
            // No need to publish here since handler will publish it
        }
        */
    }
    @FunctionalityMethod
    public void channelUp() throws PhidgetException {
        this.irSmartBoard.transmitRaw(Constants.CHANNEL_UP);

        contextManager.updateContext("Channel", "Up", agentName );
    }

    @FunctionalityMethod
    public void channelDown() throws PhidgetException {
        this.irSmartBoard.transmitRaw(Constants.CHANNEL_DOWN);
        contextManager.updateContext("Channel", "Down", agentName );
    }

    @FunctionalityMethod
    public void volumeUp() throws PhidgetException {
        this.irSmartBoard.transmitRaw(Constants.VOLUME_UP);
        contextManager.updateContext("Volume", "Up", agentName );
    }

    @FunctionalityMethod
    public void volumeDown() throws PhidgetException {
        this.irSmartBoard.transmitRaw(Constants.VOLUME_DOWN);
        contextManager.updateContext("Volume", "Down", agentName );
    }

    @FunctionalityMethod // For demo
    public void setVolumeHigh() throws PhidgetException {
        for (int i=1; i<11; i++) {
            this.irSmartBoard.transmitRaw(Constants.VOLUME_UP);
        }
    }

    public void turnOnOffSmartBoard() throws PhidgetException {
        if (SmartboardState.getInstance().isSmartboardOn()) {
            turnOffSmartBoard();
        } else {
            turnOnSmartBoard();
        }
    }

    //@ProvidedByFunctionality(name = "SBChangeInput", options = {"newInput"}, updates={"SBInput"})
    @FunctionalityMethod
    public void changeInput(String newInput) throws PhidgetException {
        if (newInput == null || newInput.isEmpty()) {
            return;
        }

        if (newInput.equals("TV")) {
            this.irSmartBoard.transmitRaw(Constants.TV);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("TV");
        } else if (newInput.equals("AV")) {
            this.irSmartBoard.transmitRaw(Constants.AV);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("AV");
        } else if (newInput.equals("SVIDEO")) {
            this.irSmartBoard.transmitRaw(Constants.SVIDEO);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("SVIDEO");
        } else if (newInput.equals("YPBPR")) {
            this.irSmartBoard.transmitRaw(Constants.YPBPR);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("YPBPR");
        } else if (newInput.equals("PC")) {
            this.irSmartBoard.transmitRaw(Constants.PC);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("PC");
        } else if (newInput.equals("HDMI1")) {
            this.irSmartBoard.transmitRaw(Constants.HDMI1);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("HDMI1");
        } else if (newInput.equals("HDMI2")) {
            this.irSmartBoard.transmitRaw(Constants.HDMI2);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("HDMI2");
        } else if (newInput.equals("HDMI3")) {
            this.irSmartBoard.transmitRaw(Constants.HDMI3);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("HDMI3");
        } else if (newInput.equals("SCD")) {
            this.irSmartBoard.transmitRaw(Constants.SCD);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("SCD");
        } else if (newInput.equals("SLEEP")) {
            this.irSmartBoard.transmitRaw(Constants.SLEEP);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("SLEEP");
        } else if (newInput.equals("ADD_DEL")) {
            this.irSmartBoard.transmitRaw(Constants.ADD_DEL);
            // SmartboardState.getInstance().setSmartboardInput(newInput);
            smartboardInput.updateValue("ADD_DEL");
        }
    }
    //	@ProvidedByFunctionality(name = "SBMovieStart", updates={"MovieStatus"})
    public boolean moviestartDisplay() {
        try {
            ProcessBuilder pb = new ProcessBuilder(Constants.vlc, "http://"
                    + Constants.streamServerIP + ":"
                    + Constants.streamServerPort, "--fullscreen");
            Process p = pb.start();
			/*
			 * executeCommand(vlc + " http://" + streamServerIP + ":" +
			 * streamServerPort +
			 * "/ --fullscreen --extraintf=http:logger --verbose=2");
			 */

            LOGGER.info("Movie Status Updated : Display Start");
            return true;
        } catch (Exception e) {
            return false;
        }
    }
    //	@ProvidedByFunctionality(name = "SBMoviePause", updates={"MovieStatus"})
    public void moviePause() {
        robot.keyPress(KeyEvent.VK_SPACE);
        robot.keyRelease(KeyEvent.VK_SPACE);

        contextManager.updateContext("Status", "Pause", agentName );
        LOGGER.info("Movie Status Updated : Pause");
    }
    //	@ProvidedByFunctionality(name = "SBMovieResume", updates={"MovieStatus"})
    public void movieResume() {
        robot.keyPress(KeyEvent.VK_SPACE);
        robot.keyRelease(KeyEvent.VK_SPACE);

        contextManager.updateContext("Status", "Resume", agentName );
        LOGGER.info("Movie Status Updated : Resume");
    }
    //	@ProvidedByFunctionality(name = "SBMovieExit", updates={"MovieStatus"})
    public void movieExit() {
        Runtime rt = Runtime.getRuntime();
        try {
            rt.exec("tskill vlc");

            contextManager.updateContext("Status", "Exit", agentName );
            LOGGER.info("Movie Status Updated : Exit");

        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    //	@ProvidedByFunctionality(name = "SBMovieBack", updates={"MovieStatus"})
    public void moveBackword() {
        robot.keyPress(KeyEvent.VK_LEFT);
        robot.keyRelease(KeyEvent.VK_LEFT);

        contextManager.updateContext("Status", "Move Backward", agentName );
        LOGGER.info("Movie Status Updated : Move Backward");
    }
    //	@ProvidedByFunctionality(name = "SBMovieForward", updates={"MovieStatus"})
    public void moveForward() {
        robot.keyPress(KeyEvent.VK_RIGHT);
        robot.keyRelease(KeyEvent.VK_RIGHT);

        contextManager.updateContext("Status", "Move Forward", agentName );
        LOGGER.info("Movie Status Updated : MoveForward");
    }

    //
    // public void volumeDown() {
    // robot.keyPress(KeyEvent.VK_DOWN);
    // robot.keyRelease(KeyEvent.VK_DOWN);
    //
    // try {
    // super.publish(CommandType.Context, ContextType.Status,
    // ContextValue.Volume_DOWN);
    // } catch (MqttException e) {
    // LOGGER.error(e.getMessage(), e);
    // }
    // LOGGER.info("Movie Status Updated : VolumeDown");
    // }
    //
    // public void volumeUp() {
    // robot.keyPress(KeyEvent.VK_UP);
    // robot.keyRelease(KeyEvent.VK_UP);
    //
    // try {
    // super.publish(CommandType.Context, ContextType.Status,
    // ContextValue.Volume_UP);
    // } catch (MqttException e) {
    // LOGGER.error(e.getMessage(), e);
    // }
    // LOGGER.info("Movie Status Updated : VolumeUP");
    //
    // }

    /*** xbox code ***/
//	@ProvidedByFunctionality(name = "xboxbtnY")
    public void xbox_btn_Yellow_Y() throws PhidgetException {
        System.out.println("Xbox button Yellow_Y...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_YELLOW_Y);
            contextManager.updateContext("Status", "Xbox Yellow Y", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnB")
    public void xbox_btn_Blue_X() throws PhidgetException {
        System.out.println("Xbox button Blue_X...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Blue_X);
            contextManager.updateContext("Status", "Xbox Blue X", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnG")
    public void xbox_btn_Green_A() throws PhidgetException {
        System.out.println("Xbox button Green_A...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Green_A);
            contextManager.updateContext("Status", "Xbox Green A", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnR")
    public void xbox_btn_Red_B() throws PhidgetException {
        System.out.println("Xbox button Red_B...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Red_B);
            contextManager.updateContext("Status", "Xbox Red B", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnUp")
    public void xbox_btn_Up() throws PhidgetException {
        System.out.println("Xbox button Up...");
        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Up);
            contextManager.updateContext("Status", "Xbox Up", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnDown")
    public void xbox_btn_Down() throws PhidgetException {
        System.out.println("Xbox button Down...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Down);
            contextManager.updateContext("Status", "Xbox Down", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnLeft")
    public void xbox_btn_Left() throws PhidgetException {
        System.out.println("Xbox button Left...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Left);
            contextManager.updateContext("Status", "Xbox Left", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnRight")
    public void xbox_btn_Right() throws PhidgetException {
        System.out.println("Constants.Xbox button Right...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_Right);
            contextManager.updateContext("Status", "Xbox Right", agentName );
        }
    }

    //	@ProvidedByFunctionality(name = "xboxbtnOK")
    public void xbox_btn_OK() throws PhidgetException {
        System.out.println("Xbox button OK...");

        if (irSmartBoard != null) {
            irSmartBoard.transmitRaw(Constants.IRCODE_OK);
            contextManager.updateContext("Status", "Xbox Ok", agentName );
        }
    }

    //@ProvidedByFunctionality(name = "checkPlayingGames", options={"checking"}, updates={"Game"})
    @FunctionalityMethod
    public void checkPlayingGames(boolean b) {

        boolean b1 = b;
        if (b1 == true) {
            contextManager.updateContext("Game", "Game", agentName );
            // reportCurrentlyPlayingGame()
        } else {
//			try{
//				super.publish(CommandType.Context, ContextType.Game, ContextValue.NoGame);
//			} catch (MqttException e){
//				e.printStackTrace();
//			}
        }

        // Vector<XboxGame> recentGamesList =
        // XboxDataGathering.getLastPlayedGames(GAME_COUNT);
        //
        // if (recentGamesList != null) {
        // if (lastPlayedGame == null) {
        // lastPlayedGame = recentGamesList.get(0);
        // reportCurrentlyPlayingGame(lastPlayedGame.getName());
        // } else {
        // if (!lastPlayedGame.equals(recentGamesList.get(0))) {
        // reportCurrentlyPlayingGame(lastPlayedGame.getName());
        // }
        // }
        // }
    }
    //@ProvidedByFunctionality(name = "reportPlayingGames", options={"gamename"}, updates={"GameName"})
    @FunctionalityMethod
    public void reportPlayingGame(String gameName) {

        contextManager.updateContext("Game", gameName, agentName );

    }

    public void movieexecuteCommand(String cmd) {
        Process p;
        Runtime rt = Runtime.getRuntime();
        try {
            p = rt.exec(cmd);

            StreamGobbler outputGobbler = new StreamGobbler(p.getInputStream(),
                    "OUTPUT");
            outputGobbler.start();

            int exitVal = p.waitFor();
            System.out.println("ExitValue: " + exitVal);


            contextManager.updateContext("Status", cmd, agentName );

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public void onSmartboardPowerChanged(boolean newState) {
        smartboardPower.updateValue(newState? "On" : "Off");
    }

    @Override
    public void onSmartboardInputChanged(String newInput) {
        smartboardInput.updateValue(newInput);
    }
}