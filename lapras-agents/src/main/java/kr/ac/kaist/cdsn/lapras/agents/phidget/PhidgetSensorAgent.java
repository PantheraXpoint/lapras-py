package kr.ac.kaist.cdsn.lapras.agents.phidget;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.SensorChangeEvent;
import com.phidgets.event.SensorChangeListener;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Created by Daekeun Lee on 2017-03-29.
 */
public class PhidgetSensorAgent extends AgentComponent implements SensorChangeListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(PhidgetSensorAgent.class);

    private static final int ATTACHMENT_TIMEOUT = 2000;

    private static class SensorInfo {
        public enum CallbackType {
            PERIODIC_READ, VALUE_CHANGED
        }

        private Integer index;
        private CallbackType callbackType;
        private Integer interval;

        public SensorInfo(Integer index, CallbackType callbackType) {
            if(callbackType == CallbackType.PERIODIC_READ) {
                throw new IllegalArgumentException("Sensors with PERIODIC_READ type of callback should be accompanied by the interval");
            }
            this.index = index;
            this.callbackType = callbackType;
        }

        public SensorInfo(Integer index, CallbackType callbackType, Integer interval) {
            if(callbackType != CallbackType.PERIODIC_READ) {
                throw new IllegalArgumentException("Sensors only with PERIODIC_READ type of callback can take interval");
            }
            this.index = index;
            this.callbackType = callbackType;
            this.interval = interval;
        }

        public Integer getIndex() {
            return index;
        }

        public CallbackType getCallbackType() {
            return callbackType;
        }

        public Integer getInterval() {
            return interval;
        }
    }

    private InterfaceKitPhidget interfaceKit;
    private Integer interfaceKitSerial;
    private List<SensorInfo> sensorInfos = new ArrayList<>();
    private ScheduledExecutorService periodicReadExecutorService = Executors.newSingleThreadScheduledExecutor();

    public PhidgetSensorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        interfaceKitSerial = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("phidget_serial", "-1"));

        String[] sensorIndices = agent.getAgentConfig().getOptionAsArray("phidget_sensor.index");
        String[] sensorCallbacks = agent.getAgentConfig().getOptionAsArray("phidget_sensor.callback");
        String[] intervals = agent.getAgentConfig().getOptionAsArray("phidget_sensor.interval");

        int intervalIndex = 0;
        for (int i = 0; i < sensorIndices.length; i++) {
            Integer sensorIndex = Integer.parseInt(sensorIndices[i]);
            SensorInfo.CallbackType callbackType = SensorInfo.CallbackType.valueOf(sensorCallbacks[i]);
            SensorInfo sensorInfo;
            if(callbackType == SensorInfo.CallbackType.PERIODIC_READ) {
                Integer interval = Integer.parseInt(intervals[intervalIndex]);
                sensorInfo = new SensorInfo(sensorIndex, callbackType, interval);
            } else {
                sensorInfo = new SensorInfo(sensorIndex, callbackType);
            }
            sensorInfos.add(sensorInfo);
        }
    }

    private void initPhidgetInterfaceKit(int serial){
        try {
            interfaceKit = new InterfaceKitPhidget();
            interfaceKit.addSensorChangeListener(this);
            if (serial > 0) {
                interfaceKit.open(serial);
            } else {
                interfaceKit.openAny();
            }

            LOGGER.debug("Waiting for Phidget interface kit attachment...");
            interfaceKit.waitForAttachment(ATTACHMENT_TIMEOUT);
            LOGGER.debug("Inteface kit attached: {} (S/N: {})", interfaceKit.getDeviceID(), interfaceKit.getSerialNumber());
        } catch (PhidgetException e) {
            LOGGER.error("An error occurred while opening Phidget interface kit. Please check the serial number. (serial = {})",
                    serial, e);
        }
    }

    @Override
    public void setUp() {
        super.setUp();

        initPhidgetInterfaceKit(interfaceKitSerial);

        sensorInfos.stream()
                .filter(sensorInfo -> sensorInfo.getCallbackType() == SensorInfo.CallbackType.PERIODIC_READ)
                .forEach(sensorInfo -> {
                    periodicReadExecutorService.scheduleAtFixedRate(()-> {
                        try {
                            Integer value = interfaceKit.getSensorValue(sensorInfo.getIndex());
                            periodicRead(sensorInfo.getIndex(), value);
                        } catch (PhidgetException e) {
                            LOGGER.error("An error occurred while reading the sensor value of {}", sensorInfo.getIndex(), e);
                        }
                    }, 0, sensorInfo.getInterval(), TimeUnit.MILLISECONDS);
                });
    }

    @Override
    public void run() {
        while(true) {
            try {
                Thread.sleep(Integer.MAX_VALUE);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    @Override
    public synchronized void sensorChanged(SensorChangeEvent sensorChangeEvent) {
        for (SensorInfo sensorInfo : sensorInfos) {
            if(sensorInfo.getIndex() == sensorChangeEvent.getIndex()) {
                if(sensorInfo.getCallbackType() == SensorInfo.CallbackType.VALUE_CHANGED) {
                    valueChanged(sensorChangeEvent.getIndex(), sensorChangeEvent.getValue());
                } else {
                    return;
                }
            }
        }
    }

    public void periodicRead(int sensorIndex, int sensorValue) {
        // Subclasses may override this method
    }

    public void valueChanged(int sensorIndex, int sensorValue) {
        // Subclasses may override this method
    }

    public Integer indexOf(int sensorIndex) {
        for (int i = 0; i < sensorInfos.size(); i++) {
            if(sensorInfos.get(i).getIndex() == sensorIndex) {
                return i;
            }
        }
        return null;
    }
}
