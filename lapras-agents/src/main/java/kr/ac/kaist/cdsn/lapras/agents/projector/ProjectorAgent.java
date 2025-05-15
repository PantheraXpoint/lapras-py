package kr.ac.kaist.cdsn.lapras.agents.projector;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.awt.event.KeyEvent;
import java.io.File;
import java.io.IOException;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public class ProjectorAgent extends AgentComponent {
    private static Logger LOGGER = LoggerFactory.getLogger(ProjectorAgent.class);

    private final String projectorAddress;
    private final int projectorPort;
    private final String pdfCommand;
    private final String pptCommand;

    public ProjectorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        projectorAddress = agent.getAgentConfig().getOption("projector_address");
        projectorPort = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("projector_port", "80"));

        pdfCommand = agent.getAgentConfig().getOption("pdf_command");
        pptCommand = agent.getAgentConfig().getOption("ppt_command");
    }

    private ProjectorController controller = null;
    private PCController pcController = null;

    private boolean isTurnedOn = false;
    private InputType currentInputType = null;

    private CurrentStateMonitorThread stateMonitorThread = null;

    @ContextField(publishAsUpdated = true)
    public Context projectorInput;

    @ContextField(publishAsUpdated = true)
    public Context projectorPower;

    @FunctionalityMethod
    public boolean keyUp() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_UP);
            LOGGER.info("keyUp: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyUp: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keyDown() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_DOWN);
            LOGGER.info("keyDown: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyDown: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keyLeft() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_LEFT);
            LOGGER.info("keyLeft: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyLeft: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keyRight() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_RIGHT);
            LOGGER.info("keyRight: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyRight: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keySpace() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_SPACE);
            LOGGER.info("keySpace: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keySpace: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keyF5() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_F5);
            LOGGER.info("keyF5: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyF5: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keyF11() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_F11);
            LOGGER.info("keyF11: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyF11: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean keyESC() {
        try {
            this.pcController.strokeKey(KeyEvent.VK_ESCAPE);
            LOGGER.info("keyESC: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("keyESC: false");
            e.printStackTrace();
            return (false);
        }
    }

    public boolean maximizePPT() {
        try {
            maximizeCurrentWindow();
            this.pcController.pressKey(KeyEvent.VK_F5);
            this.pcController.releaseKey(KeyEvent.VK_F5);
            LOGGER.info("maximizePPT: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("maximizePPT: false");
            e.printStackTrace();
            return (false);
        }
    }

    public boolean maximizePDF() {
        try {
            maximizeCurrentWindow();
            this.pcController.pressKey(KeyEvent.VK_CONTROL);
            this.pcController.pressKey(KeyEvent.VK_L);
            this.pcController.releaseKey(KeyEvent.VK_CONTROL);
            this.pcController.releaseKey(KeyEvent.VK_L);
            LOGGER.info("maximizePDF: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("maximizePDF: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean maximizeCurrentWindow() {
        try {
            this.pcController.pressKey(KeyEvent.VK_WINDOWS);
            this.pcController.pressKey(KeyEvent.VK_UP);
            this.pcController.releaseKey(KeyEvent.VK_WINDOWS);
            this.pcController.releaseKey(KeyEvent.VK_UP);
            LOGGER.info("maximizeCurrentWindow: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("maximizeCurrentWindow: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public boolean exitCurrentWindow() {
        try {
            this.pcController.pressKey(KeyEvent.VK_ALT);
            this.pcController.pressKey(KeyEvent.VK_F4);
            this.pcController.releaseKey(KeyEvent.VK_ALT);
            this.pcController.releaseKey(KeyEvent.VK_F4);
            LOGGER.info("exitCurrentWindow: true");
            return (true);
        } catch (Exception e) {
            LOGGER.info("exitCurrentWindow: false");
            e.printStackTrace();
            return (false);
        }
    }

    @FunctionalityMethod
    public void turnOffProjector() {
        try {
            controller.turnOffProjector();
            System.out.println("\n\n\n\n\n\nOFFOFFOFFOFFOFFOFFOFFOFFOFFOFFOFFOFF\n\n\n\n\n");

        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }

    @FunctionalityMethod
    public void turnOnProjector() {
        try {
            controller.turnOnProjector();
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }

    @FunctionalityMethod
    public void turnOnOffProjector() {
        try {
            if (controller.isProjectorTurnedOn()) {
                turnOffProjector();
            } else {
                turnOnProjector();
            }
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }

    @FunctionalityMethod
    public void changeInput(String strInputType) {
        try {
            InputType inputType = InputType.valueOf(strInputType.toUpperCase());
            LOGGER.info("Changing input to " + inputType);

            switch (inputType) {
                case COM1:
                    controller.changeInputIntoCOM1();
                    break;
                case COM2:
                    controller.changeInputIntoCOM2();
                    break;
                case DP:
                    controller.changeInputIntoDP();
                    break;
                case HDMI:
                    controller.changeInputIntoHDMI();
                    break;
            }
            projectorInput.updateValue(inputType.name());
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }
    @FunctionalityMethod
    public void InputToCOM1() {
        try {
            controller.changeInputIntoCOM1();
            projectorInput.updateValue("COM1");
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }
    @FunctionalityMethod
    public void InputToCOM2() {
        try {
            controller.changeInputIntoCOM2();
            projectorInput.updateValue("COM2");
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }
    @FunctionalityMethod
    public void InputToDP() {
        try {

            controller.changeInputIntoDP();
            projectorInput.updateValue("DP");
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }
    @FunctionalityMethod
    public void InputToHDMI() {
        try {

            controller.changeInputIntoHDMI();
            projectorInput.updateValue("HDMI");
        } catch (Exception e) {
            LOGGER.error(e.getMessage(), e);
            e.printStackTrace();
        }
    }

    private void openFile(File downloadedFile, String inputType) {
        // Change to the input type
        changeInput(inputType);

        // Get extension
        String filename = downloadedFile.getName();
        String[] tokens = filename.split("\\.(?=[^\\.]+$)");
        String extension;
        if (tokens.length >= 2) {
            extension = "." + tokens[1].trim();
        } else {
            extension = "." + tokens[0].trim();
        }

        // Get filetype
        ProjectorFileType fileType = ProjectorFileType.getFileType(extension);
        if (fileType == null) {
            LOGGER.error("The given file is not supported: " + downloadedFile.getAbsolutePath());
            return;
        }

        switch (fileType) {
            case PDF:
                openFilePDF(downloadedFile);
                break;
            case PPT:
                openFilePPT(downloadedFile);
                break;
        }

        return;
    }

    private void openFilePDF(File downloadedFile) {
        String filePath = downloadedFile.getAbsolutePath().replace("\\", "\\\\");

        String[] cmd = new String[]{
                pdfCommand,
                "/A",
                "\"pagemode=FullScreen\"",
                "\"" + filePath + "\""
        };

        try {
            Runtime.getRuntime().exec(cmd);

            // Short delay before maximizing the screen
            try {
                Thread.sleep(3000);
            } catch (InterruptedException e) {
                LOGGER.error(e.getMessage(), e);
            }

            maximizeCurrentWindow();
            maximizePDF();
        } catch (IOException e) {
            LOGGER.error(e.getMessage(), e);
        }
    }

    private void openFilePPT(File downloadedFile) {
        String filePath = downloadedFile.getAbsolutePath().replace("\\", "\\\\");
        String[] cmd = new String[]{
                pptCommand,
                "/s",
                "\"" + filePath + "\""
        };

        try {
            Runtime.getRuntime().exec(cmd);

            // Short delay before maximizing the screen
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                LOGGER.error(e.getMessage(), e);
            }

            maximizeCurrentWindow();
            maximizePPT();
        } catch (IOException e) {
            LOGGER.error(e.getMessage(), e);
        }
    }

    @FunctionalityMethod
    public void openFile(String fileType, File file) {
        if(fileType.toUpperCase().equals("PDF")) {
            openFilePDF(file);
        } else if(fileType.toUpperCase().equals("PPT")) {
            openFilePPT(file);
        }
    }

    @FunctionalityMethod
    private void notifyCurrentInput() {
        try {
            InputType newInputType = this.controller.getInputType();
            if (newInputType == null) {
                LOGGER.debug("Current input type is null.");
                return;
            }

            if (this.currentInputType == null || this.currentInputType != newInputType) {
                projectorInput.updateValue(newInputType.name());
                this.currentInputType = newInputType;
                LOGGER.debug("New input state: {}", this.currentInputType);
            } else {
                LOGGER.debug("No new input state {} ", this.currentInputType);
            }
        } catch (Exception e) {
            e.printStackTrace();
            LOGGER.error(e.getMessage(), e);
        }
    }

    @FunctionalityMethod
    public void notifyCurrentPowerState() {
        try {
            boolean newState = this.controller.isProjectorTurnedOn();

            if (newState != isTurnedOn) {
                projectorPower.updateValue(newState ? "On" : "Off");
                actionManager.taken(newState ? "TurnOnProjector" : "TurnOffProjector");
                isTurnedOn = newState;
                LOGGER.debug("Power state change to {}", this.isTurnedOn ? "On" : "Off");
            } else {
                LOGGER.debug("No power state change {}", this.isTurnedOn ? "On" : "Off");
            }
        } catch (Exception e) {
            e.printStackTrace();
            LOGGER.error(e.getMessage(), e);
        }
    }

    public static class CurrentStateMonitorThread extends Thread {
        private static final long MONITORING_INTERVAL = 3000L;
        private boolean isRunning = false;
        private final ProjectorAgent agent;

        public CurrentStateMonitorThread(ProjectorAgent agent) {
            this.agent = agent;
        }

        @Override
        public void run() {
            Thread.currentThread().setName(CurrentStateMonitorThread.class.getSimpleName());
            isRunning = true;
            while (isRunning) {
                try {
                    this.agent.notifyCurrentPowerState();
                    this.agent.notifyCurrentInput();
                } catch (Exception e) {
                    LOGGER.error(e.getMessage(), e);
                } finally {
                    try {
                        Thread.sleep(MONITORING_INTERVAL);
                    } catch (InterruptedException e) {
                        LOGGER.error(e.getMessage(), e);
                    }
                }
            }
        }

        public void terminate() {
            this.isRunning = false;
            this.interrupt();
        }
    }

    public void run() {
        while(true) {
            this.controller = new ProjectorController(projectorAddress, projectorPort);

            this.pcController = new PCController();

            // Publish initial power state of the projector
            notifyCurrentPowerState();
            notifyCurrentInput();

            // Start current power updater thread
            stateMonitorThread = new CurrentStateMonitorThread(this);
            stateMonitorThread.start();

            try {
                while(true)
                    Thread.sleep(1000);

            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }
}
