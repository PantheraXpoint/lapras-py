package kr.ac.kaist.cdsn.lapras.agents.sound;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agents.phidget.PhidgetSensorAgent;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedList;

/**
 * Created by hyunju on 2017-01-12.
 */
public class SoundSensorAgent extends PhidgetSensorAgent {
    private static final Logger LOGGER = LoggerFactory.getLogger(SoundSensorAgent.class);

    private Integer windowSize;
    private LinkedList<Double>[] windows = new LinkedList[8];
    private Double[] sampleSums = new Double[8];
    private Integer publishRate; // in seconds
    String[] sensorNames = agent.getAgentConfig().getOptionAsArray("sensor_name");

    public SoundSensorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        windowSize = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("window_size", "60"));
        publishRate = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("publish_rate", "10"));
    }

    @Override
    public void setUp() {
        super.setUp();

        for(int i = 0; i< sensorNames.length; i++){
            contextManager.setPeriodicPublish(sensorNames[i], publishRate);
        }
    }

    @Override
    public void periodicRead(int sensorIndex, int sensorValue) {
        double value = Math.log(sensorValue) * 16.801 + 9.872;
        LOGGER.debug("Sound level read: {}", value);
        if(value == 0) return;

        Integer index = indexOf(sensorIndex);
        if(index == null) return;

        if (windows[index] == null) {
            windows[index] = new LinkedList<>();
            sampleSums[index] = 0.0;
        }

        windows[index].add(value);
        sampleSums[index] += value;
        LOGGER.debug("Sample sum: {}", sampleSums[index]);
        if(windows[index].size() > windowSize) {
            sampleSums[index] -= windows[index].poll();
        }
        contextManager.updateContext(sensorNames[index] , (sampleSums[index] / windows[index].size()), agentName);
    }
}

