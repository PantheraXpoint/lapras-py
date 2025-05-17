package kr.ac.kaist.cdsn.lapras.agents.ambient;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agents.ambient.xbee.SensorInfo;
import kr.ac.kaist.cdsn.lapras.agents.ambient.xbee.XbeeSensorParser;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;

/**
 * Created by Daekeun Lee on 2016-12-07.
 */
public class AmbientSensorAgent extends AgentComponent {
    private String[] sensorNames;
    private int reportInterval;

    public AmbientSensorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        sensorNames = agent.getAgentConfig().getOptionAsArray("sensor_name");
        for (String sensorName : sensorNames) {
            contextManager.setPublishAsUpdated(sensorName + "_Temperature");
            contextManager.setPublishAsUpdated(sensorName + "_Humidity");
            contextManager.setPublishAsUpdated(sensorName + "_Brightness");
        }

        reportInterval = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("reporting_period_ms", "60000"));
    }

    @Override
    public void run() {
        XbeeSensorParser xbs = new XbeeSensorParser(agent.getAgentConfig().getOption("endpoint_url"));

        while(true) {
            xbs.getSensorValue();
            for(String devName : xbs.getAvailableDeviceNames()) {
                SensorInfo sensorInfo = xbs.getSensorByName(devName);
                if (sensorInfo != null) {
                    for (String sensorName : sensorNames) {
                        if (sensorInfo.getName().contains(sensorName)) {
                            if (sensorInfo.getTemperature() != 0)
                                contextManager.updateContext(sensorName + "_Temperature", sensorInfo.getTemperature(), agentName);
                            if (sensorInfo.getHumidity() != 0)
                                contextManager.updateContext(sensorName + "_Humidity", sensorInfo.getHumidity(), agentName);
                            contextManager.updateContext(sensorName + "_Brightness", sensorInfo.getLight(), agentName);
                            break;
                        }
                    }
                }
            }
            try {
                Thread.sleep(reportInterval);
            } catch (InterruptedException e) {
                break;
            }
        }
    }
}
