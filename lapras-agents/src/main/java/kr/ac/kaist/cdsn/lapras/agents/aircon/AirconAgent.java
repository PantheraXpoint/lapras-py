package kr.ac.kaist.cdsn.lapras.agents.aircon;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.SensorChangeEvent;
import com.phidgets.event.SensorChangeListener;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Created by Daekeun Lee on 2016-12-08.
 *
 * Control air conditioners by PhidgetIR controllers and sense their operating status by Phidget light sensors.
 *
 * A single agent can control as many air conditioners as it can have IR controllers and light sensors. For example, on
 * a Raspberry Pi with 4 USB ports, three IR transceivers and one interface kit can be attached, so at most three A.C.s
 * can be controlled. The A.C.s are numbered 0 and on in the order that they are listed in the configuration.
 *
 * Required configuration entries
 *     phidget_id: An array of PhidgetIR serial numbers
 *     sensor_index: An array of interface indices to which light sensors are attached
 *     sensor_threshold: Sensor threshold value ranging between 0-1000; being darker than this value will indicate 'off'
 *
 * Publishing contexts
 *     Aircon<id>Power (String): Indicates whether the A.C. of ID <id> is on or off. Can be one of "On" and "Off"
 *
 * Exposed functionalities
 *     TurnOnAircon<id>: Turn on the power of A.C. of ID <id>; changes Aircon<id>Power context
 *     TurnOffAircon<id>: Turn off the power of A.C. of ID <id>; changes Aircon<id>Power context
 *     ToggleAircon<id>: Toggle the power of A.C. of ID <id>; changes Aircon<id>Power context
 */
public class AirconAgent extends AgentComponent implements SensorChangeListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(AirconAgent.class);

    private final int threshold;

    private final List<Integer> phidget_ids;
    private final List<Integer> sensorIndices;
    private final List<AirConditionerController> controllers;

    private boolean isApplianceRunning = false;
    private static InterfaceKitPhidget phidgetInterfaceKit;

    public AirconAgent(EventDispatcher eventDispatcher, Agent agent) throws LaprasException {
        super(eventDispatcher, agent);

        phidget_ids = Arrays.stream(agent.getAgentConfig().getOptionAsArray("phidget_id"))
                .map(Integer::parseInt).collect(Collectors.toList());
        sensorIndices = Arrays.stream(agent.getAgentConfig().getOptionAsArray("sensor_index"))
                .map(Integer::parseInt).collect(Collectors.toList());
        if(phidget_ids.size() != sensorIndices.size()) {
            throw new LaprasException("Configuration file is malformed; numbers of phidget_id and sensor_index must be the same");
        }

        threshold = Integer.parseInt(agent.getAgentConfig().getOption("sensor_threshold"));

        controllers = phidget_ids.stream().map(phidget_id -> {
            try {
                return new AirConditionerController(phidget_id);
            } catch (PhidgetException e) {
                LOGGER.error("Failed to initialize controller with id {}", phidget_id, e);
                return null;
            }
        }).collect(Collectors.toList());
    }

    @Override
    public void run() {
        for (int id = 0; id < phidget_ids.size(); id++) {
            final int finalId = id;
            contextManager.setPublishAsUpdated(String.format("Aircon%dPower", id));
            functionalityExecutor.registerFunctionality("StartAircon" + id, (args)->{
                startAircon(finalId);
            });
            functionalityExecutor.registerFunctionality("StopAircon" + id, (args)->{
                stopAircon(finalId);
            });
            functionalityExecutor.registerFunctionality("ToggleAircon" + id, (args)->{
                if(contextManager.getContext(String.format("Aircon%dPower", finalId)).getValue().equals("On")) {
                    stopAircon(finalId);
                } else {
                    startAircon(finalId);
                }
            });
            functionalityExecutor.registerFunctionality("tempUpAircon" + id, (args)->{
                tempUpAircon(finalId);
            });
            functionalityExecutor.registerFunctionality("tempDownAircon" + id, (args)->{
                tempDownAircon(finalId);
            });
        }

        try {
            phidgetInterfaceKit = new InterfaceKitPhidget();
            phidgetInterfaceKit.openAny();
        } catch (PhidgetException e) {
            LOGGER.error("Failed to initialize Phidget IR", e);
            return;
        }
        phidgetInterfaceKit.addSensorChangeListener(this);

        while(true) {
            try {
                Thread.sleep(Integer.MAX_VALUE);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    public void startAircon(int id) {
        if (controllers.get(id).turnOn()) {
            isApplianceRunning = true;
            contextManager.updateContext(String.format("Aircon%dPower", id), "On", agentName);
        }
    }

    public void stopAircon(int id) {
        if (controllers.get(id).turnOff()) {
            contextManager.updateContext(String.format("Aircon%dPower", id), "Off", agentName);
        }
    }

    public void tempUpAircon(int id){
        if(controllers.get(id).tempUp()){
            isApplianceRunning = true;
            //no need to update Context (there is no information about temperature)
        }
    }

    public void tempDownAircon(int id){
        if(controllers.get(id).tempDown()){
            isApplianceRunning = true;
            //no need to update Context (there is no information about temperature)
        }
    }

    @Override
    public void sensorChanged(SensorChangeEvent sensorChangeEvent) {
        Integer id = sensorIndices.indexOf(sensorChangeEvent.getIndex());
        if(id == null) return;

        int val = sensorChangeEvent.getValue();

        LOGGER.debug(
                "Sensor value change detected. [agentIndex={}/sensorIndex={}/val={}/threshold={}/isApplianceRunning={}]",
                id, sensorChangeEvent.getIndex(), val, threshold, isApplianceRunning);

        if (val < threshold) { // Off
            if (isApplianceRunning) {
                contextManager.updateContext(String.format("Aircon%dPower", id), "Off", agentName);
                agent.getActionManager().taken("TurnOffAirCon" + id);
            }
            isApplianceRunning = false;
        } else if (val >= threshold) { // On
            if (!isApplianceRunning) {
                contextManager.updateContext(String.format("Aircon%dPower", id), "On", agentName);
                agent.getActionManager().taken("TurnOffAirCon" + id);
            }
            isApplianceRunning = true;
        }
    }

    //handleEvent which is overrided from AgentComponenet.java
    @Override
    protected boolean handleEvent(Event event) {
        super.handleEvent(event); //For handling event in super class (AgentComponent)
        switch (event.getType()) {
            case CONTEXT_UPDATED:
                ContextInstance context = (ContextInstance) event.getData();
                if(context.getName().contains("tiltAircon")) {
                    double threshold = (double) context.getValue();
                    char id = context.getName().charAt(10);
                    if (Double.compare(threshold, 0) < 0){
                        contextManager.updateContext("Aircon"+id+"Power", "On", agentName);
                    }else{
                        contextManager.updateContext("Aircon"+id+"Power", "Off", agentName);
                    }
                    return true;
                }
                else{
                    break;
                }
        }
        return false;
    }
}
