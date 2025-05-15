package kr.ac.kaist.cdsn.lapras.agents.standlight;

import com.phidgets.PhidgetException;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.Agent;

import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
//

import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import kr.ac.kaist.cdsn.lapras.rest.RestServer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Bumjin Gwak on 2017-02-22.
 * Edited by Heesuk Son on 2018-04-13.
 *
 * StandLightAgent uses two controllers: StandLightInterfaceController and
 * StandLightIRController. Descriptions for each class will be given in
 * their java file (class declaration). One important note is, StandLightAgent
 * manipulates three types of contexts: power, standlightcolor, and standlightlevel.
 * The last two context values are updated and published in this class. However,
 * since power status is totally monitored by StandLightInterfaceController,
 * especially Phidget Light sensor, power value is updated and published by
 * StandLightInterfaceController.
 */
public class StandLightAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(StandLightAgent.class);

    // for power action
    private final int ON = 0;
    private final int OFF = 1;
    private final int NO_ONOFF_ACTION = 2;

    // for power context
    private final boolean TURNED_ON = true;
    private final boolean TURNED_OFF = false;

    // for level and color action
    private final boolean CHANGE = true;
    private final boolean NO_CHANGE = false;

    // for light color
    private final boolean ORANGE = true;
    private final boolean WHITE = false;

    private final int phidgetIRSN = 122106;
    private final int phidgetInterfaceSN = 442609;

    private StandLightIRController irCtrl = null;
    private StandLightInterfaceController interfaceCtrl = null;

    public StandLightAgent(EventDispatcher eventDispatcher, Agent agent) {
    	super(eventDispatcher, agent);
    }

    @Override
    public void run() {
        LOGGER.info("Initializing contexts by default values..");
        contextManager.setPublishAsUpdated("Power");
        contextManager.setPublishAsUpdated("Standlightlevel");
        contextManager.setPublishAsUpdated("Standlightcolor");

        contextManager.updateContext("Power","Off",agentName);
        contextManager.updateContext("Standlightlevel","0",agentName);
        contextManager.updateContext("Standlightcolor","White",agentName);

        LOGGER.info("Context value initialization is done.");

        LOGGER.info("Initializing {} phidgetSerial={}", StandLightAgent.class.getSimpleName(),
                this.phidgetIRSN);
        try {
            irCtrl = new StandLightIRController(phidgetIRSN);
            irCtrl.start();
            LOGGER.info("Phidget IR ready");

            interfaceCtrl = new StandLightInterfaceController(this.phidgetInterfaceSN,
                    this.irCtrl, this, this.contextManager);
            LOGGER.info("Phidget InterfaceKit ready");

            LOGGER.info("Setup Context Manager");
        } catch (PhidgetException e) {
            e.printStackTrace();
        }

        while(true){
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                LOGGER.error("InterruptException caught!");
            }
        }
    }

    public boolean isLightOn() {
        return contextManager.getContext("Power").getValue().toString().equals("On")?true:false;
    }

    public void setLightOn(boolean cmd) {
        if(cmd == TURNED_ON){
            if(!isLightOn()){
                contextManager.updateContext("Power", "On",agentName);
            }
        }else if(isLightOn() != TURNED_OFF){
            contextManager.updateContext("Power", "Off", agentName);
        }
    }

    public boolean getLightColor() {
        boolean curr = contextManager.getContext("Standlightcolor").getValue().toString().equals("Orange")?ORANGE:WHITE;
        return curr;
    }

    public void setLightColor(boolean lightColor) {
        contextManager.updateContext("Standlightcolor","Orange",agentName);
    }

    public int getLightLevel() {
        return Integer.parseInt(contextManager.getContext("Standlightlevel").getValue().toString());
    }

    public void setLightLevel(int lightLevel) {
        contextManager.updateContext("Standlightlevel",""+lightLevel,agentName);
    }

    // OnOff function calls On or Off due to state of light
    @FunctionalityMethod
    public void OnOff() {
        irCtrl.turnOnOff();
    }
    
    @FunctionalityMethod
    public void White() {
    	changeTo(WHITE, getLightLevel());
    }
    
    @FunctionalityMethod
    public void Orange() {
    	changeTo(ORANGE, getLightLevel());
    }
    
    @FunctionalityMethod
    public void Level_1() {
    	changeTo(getLightColor(), 1);
    }
    
    @FunctionalityMethod
    public void Level_2() {
    	changeTo(getLightColor(), 2);
    }
    
    @FunctionalityMethod
    public void Level_3() {
    	changeTo(getLightColor(), 3);
    }
    
    @FunctionalityMethod
    public void Level_4() {
    	changeTo(getLightColor(), 4);
    }

    public void changeTo(int level){
        changeTo(getLightColor(),level);
    }
    
    public void changeTo(boolean color, int level) {
        int powerAction = getPowerAction(level);
        boolean levelAction = needToChangeLevel(level);
        boolean colorAction = needToChangeColor(color);

        LOGGER.info(
                "changeTo({},{}) :: powerAction = {}, levelAction = {}, colorAction = {}",
                color,
                level,
                powerAction==NO_ONOFF_ACTION?"no_action":"action",
                levelAction==CHANGE?"change":"no_change",
                colorAction==CHANGE?"change":"no_change");

        if(powerAction != NO_ONOFF_ACTION){
            LOGGER.debug("powerAction == {}, turnOnOff() is called.",powerAction);
            irCtrl.turnOnOff();
            if(level > 0){
                contextManager.updateContext("Power","On",agentName);
            }else{
                contextManager.updateContext("Power","Off",agentName);
            }
        }

        if(levelAction == CHANGE){
            LOGGER.debug("levelAction == {}, setLight() is called.",levelAction);
            irCtrl.setLight(getLightColor(), level);
            contextManager.updateContext("Standlightlevel",""+level,agentName);
        }

        if(colorAction == CHANGE){
            LOGGER.debug("colorAction == {}, setLight() is called.",colorAction);
            irCtrl.setLight(color, level);
            if (color == ORANGE) {
                contextManager.updateContext("Standlightcolor","Orange",agentName);
            } else {
                contextManager.updateContext("Standlightcolor","White",agentName);
            }
        }
    }

    private int getPowerAction(int level){
        LOGGER.debug("isLightOn() = {}",isLightOn());

        if(!isLightOn() && level > 0){
            return ON;
        }else if(isLightOn() && level == 0){
            return OFF;
        }else{
            return NO_ONOFF_ACTION;
        }
    }

    private boolean needToChangeLevel(int level){
        int current = getLightLevel();
        if(current == level){
            return NO_CHANGE;
        }else{
            return CHANGE;
        }
    }

    private boolean needToChangeColor(boolean color){
        boolean current = getLightColor();
        LOGGER.debug("needToChangeColor():: -> current = {}, wanted = {}",current,color);
        if(current == color){
            return NO_CHANGE;
        }else{
            return CHANGE;
        }
    }
}
