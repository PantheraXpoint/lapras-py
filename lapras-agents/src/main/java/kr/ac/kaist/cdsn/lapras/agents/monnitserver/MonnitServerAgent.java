package kr.ac.kaist.cdsn.lapras.agents.monnitserver;

import com.monnit.mine.BaseApplication.BitConverter;
import com.monnit.mine.BaseApplication.Datum;
import com.monnit.mine.BaseApplication.applicationclasses.PIRBase;
import com.monnit.mine.BaseApplication.applicationclasses.TiltBase;
import com.monnit.mine.MonnitMineAPI.*;
import com.monnit.mine.MonnitMineAPI.enums.eFirmwareGeneration;
import com.monnit.mine.MonnitMineAPI.enums.eGatewayType;
import com.monnit.mine.MonnitMineAPI.enums.eMineListenerProtocol;
import com.monnit.mine.MonnitMineAPI.enums.eSensorApplication;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.context.ContextManager;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.nio.ByteBuffer;

import java.io.IOException;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.*;

/**
 * Created by JWP on 2017. 8. 1.
 *
 * MonnitServerAgent handles all sensors developed by Monnit.
 * Currently, it handles seat occupancy sensor and IR motion sensor, and door sensor.
 */

public class MonnitServerAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(MonnitServerAgent.class);

    private static final Map<Integer, String> seatSerialMap = new HashMap<>();
    private static final Map<Integer, String> motionSerialMap = new HashMap<>();
    private static final Map<Integer, String> doorSerialMap = new HashMap<>();
    private static final Map<Integer, String> tiltSerialMap = new HashMap<>(); // This is what I handle 4/27/2018-Kingberly

    private static final Map<String, Boolean> seatCountMap = new HashMap<>(); // map for total seat count

    private final List<Sensor> seatSensors = new ArrayList<>();
    private final List<Sensor> motionSensors = new ArrayList<>();
    private final List<Sensor> doorSensors = new ArrayList<>();
    private final List<Sensor> tiltSensors = new ArrayList<>(); // This is what I handle 4/27/2018-Kingberly

    private AgentConfig agentConfig;
    private ContextManager contextManager;
    private MineServer mineServer;

    /**
     * Initialize member variabless with the given configuration file
     */

    public MonnitServerAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        agentConfig = agent.getAgentConfig();
        contextManager = agent.getContextManager();

        String[] seatSensorIds = agentConfig.getOptionAsArray("seat_sensor_ids");
        String[] seatSensorNames = agentConfig.getOptionAsArray("seat_sensor_names");
        String[] motionSensorIds = agentConfig.getOptionAsArray("motion_sensor_ids");
        String[] motionSensorNames = agentConfig.getOptionAsArray("motion_sensor_names");
        String[] doorSensorIds = agentConfig.getOptionAsArray("door_sensor_ids");
        String[] doorSensorNames = agentConfig.getOptionAsArray("door_sensor_names");
        String[] tiltSensorIds = agentConfig.getOptionAsArray("tilt_sensor_ids");
        String[] tiltSensorNames = agentConfig.getOptionAsArray("tilt_sensor_names");

        initializeSeatCount();

        initializeSensors(seatSensorIds, seatSensorNames, seatSensors, seatSerialMap, eSensorApplication.Seat_Occupancy);
        initializeSensors(motionSensorIds, motionSensorNames, motionSensors, motionSerialMap, eSensorApplication.Infared_Motion);
        initializeSensors(doorSensorIds, doorSensorNames, doorSensors, doorSerialMap, eSensorApplication.Open_Closed);
        initializeSensors(tiltSensorIds, tiltSensorNames, tiltSensors, tiltSerialMap, eSensorApplication.Accelerometer_Tilt); //There are som addition for Pitch, Tilt
    }

    /**
     * Setup Monnit Mineserver
     * - register gateway to server
     * - register sensor to gateway
     * - attach sensor message handler to server
     */

    @Override
    public void setUp() {
        super.setUp();

        eMineListenerProtocol Protocol = eMineListenerProtocol.TCP;
        int port = Integer.parseInt(agentConfig.getOption("mineserver_port"));
        int gatewayID = Integer.parseInt(agentConfig.getOption("gateway_id"));
        String ipaddr = agentConfig.getOption("mineserver_ip");

        InetAddress ip;

        try {
            ip = InetAddress.getByName(ipaddr);
            mineServer = new MineServer(Protocol, ip, port);
            mineServer.StartServer();

            LOGGER.info("MineServer Constructed");

            //Add handler
            if (mineServer.addSensorDataProcessingHandler(new SensorMessageHandler())) {
                LOGGER.info("Successfully added SensorHandler");
            } else {
                LOGGER.info("Failed to add handler.");
            }

            //Register Gateway
            Gateway usbGate = new Gateway(gatewayID, eGatewayType.USBService);
            usbGate.UpdateReportInterval(1);
            mineServer.RegisterGateway(usbGate);

            //Register sensors
            for (Sensor seatSensor : seatSensors) {
                mineServer.RegisterSensor(usbGate.GatewayID, seatSensor);
            }

            for (Sensor motionSensor : motionSensors) {
                mineServer.RegisterSensor(usbGate.GatewayID, motionSensor);
                PIRBase.SensorEdit(motionSensor, null, 0.1, 2, 1, null);
            }

            for (Sensor doorSensor : doorSensors) {
                mineServer.RegisterSensor(usbGate.GatewayID, doorSensor);
            }

            for (Sensor tiltSensor : tiltSensors) {
                mineServer.RegisterSensor(usbGate.GatewayID, tiltSensor);
                TiltBase.UpdateSensorHeartBeat(tiltSensor, 1, true); //To-do: slowly?
            }
        } catch (UnknownHostException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    @Override
    public void run() {

        while (true) {
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                LOGGER.debug("Stop Server!");
                try {
                    mineServer.StopServer();
                } catch (InterruptedException e1) {
                    e1.printStackTrace();
                } catch (IOException e1) {
                    e1.printStackTrace();
                }
                e.printStackTrace();
            }
        }
    }

    /**
     * Intialize sensors & contexts
     */

    private void initializeSensors (String[] sensorIds, String[] sensorNames, final List <Sensor> sensors,
                                   final Map<Integer, String> serialMap, eSensorApplication sensorType) {
        int index = 0;

        for (String sensorId : sensorIds) {
            int sensorIdNum = Integer.parseInt(sensorId);
            try {
                sensors.add(new Sensor(sensorIdNum, sensorType, "2.5.4.0", eFirmwareGeneration.Commercial));
                serialMap.put(sensorIdNum, sensorNames[index]);
                contextManager.updateContext(sensorNames[index], false, agentName);
                if(sensorNames[index].contains("tilt")){  //Tilt needs two component. 'Pitch' & 'Roll'
                    contextManager.setPublishAsUpdated(String.format("%s_%s",sensorNames[index],"Pitch"));
                    contextManager.setPublishAsUpdated(String.format("%s_%s",sensorNames[index],"Roll"));
                }else {
                    contextManager.setPublishAsUpdated(sensorNames[index]);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            index ++;
        }

    }

    /**
     * Initalize seat count
     */

    private void initializeSeatCount() {
        String[] seatSensorNames = agentConfig.getOptionAsArray("seat_sensor_names");

        for (String seatSensorName : seatSensorNames) {
            seatCountMap.put(seatSensorName, false);
        }

        contextManager.updateContext("totalSeatCount", 0, agentName);
        contextManager.setPublishAsUpdated("totalSeatCount");
    }

    /**
     * Class for parsing sensor messages & publishing the appropriate context message.
     */

    private class SensorMessageHandler implements iSensorMessageHandler {

        @Override
        public void ProcessSensorMessages(List<SensorMessage> sensorMessageList, Gateway gateway) throws Exception {

            for (SensorMessage msg : sensorMessageList) {
                LOGGER.info(msg.toString());

                if (seatSerialMap.get(msg.SensorID) != null) {
                    handleSeatSensorMessage(msg);
                } else if (motionSerialMap.get(msg.SensorID) != null) {
                    handleMotionSensorMessage(msg);
                } else if (doorSerialMap.get(msg.SensorID) != null) {
                    handleDoorSensorMessage(msg);
                } else if (tiltSerialMap.get(msg.SensorID) != null) {
                    handleTiltSensorMessage(msg);

                } else {
                    LOGGER.info("Sensor is not registered");
                }
            }
        }

        private void handleSeatSensorMessage(SensorMessage msg) {
            String contextName = seatSerialMap.get(msg.SensorID);
            Long messageTime = msg.getMessageDate().getTimeInMillis();

            if (contextName != null) {
                LOGGER.info("{} updated", contextName);
                contextManager.updateContext(contextName, msg.State == 2, agentName, messageTime);
                seatCountMap.put(contextName, msg.State == 2);
            }

            int totalSeatCount = Collections.frequency(seatCountMap.values(), true);
            LOGGER.debug("seat count: " + seatCountMap);
            contextManager.updateContext("totalSeatCount", totalSeatCount, agentName, messageTime);
        }

        private void handleMotionSensorMessage(SensorMessage msg) {
            String contextName = motionSerialMap.get(msg.SensorID);
            Long messageTime = msg.getMessageDate().getTimeInMillis();

            if (contextName != null) {
                LOGGER.info("{} updated", contextName);
                contextManager.updateContext(contextName, msg.State == 2, agentName, messageTime);
            }
        }

        private void handleDoorSensorMessage(SensorMessage msg) {
            String contextName = doorSerialMap.get(msg.SensorID);
            Long messageTime = msg.getMessageDate().getTimeInMillis();

            if (contextName != null) {
                LOGGER.info("{} updated", contextName);
                contextManager.updateContext(contextName, msg.State == 2, agentName, messageTime);
            }
        }
        public byte[] swapByte(byte[] data) {
            byte temp;
            temp = data[1];
            data[1] = data[0];
            data[0] = temp;
            return data;
        }
        public short convertToShort(byte[] array) {
            ByteBuffer buffer = ByteBuffer.wrap(array);
            return buffer.getShort();
        }

        private void handleTiltSensorMessage(SensorMessage msg) throws Exception {
            String contextName = tiltSerialMap.get(msg.SensorID);
            Long messageTime = msg.getMessageDate().getTimeInMillis();

            if (contextName != null) {
                LOGGER.info("{} updated", contextName);

                List<Datum> data = msg.getData(); // Pitch, Roll value
                for (Datum element : data) {
                    String description = element.Description;

                    //Change Network bit to Host bit (Big-Endian)
                    Double doubleData = (double)element.Data*100;  //consider second decimal place.
                    short intData = doubleData.shortValue();    //convert to short
                    byte[] byteData = BitConverter.getBytes(intData); //read intData to byteData
                    byteData = swapByte(byteData);  //byte swap!(NetworkBit to HostBit)
                    short temp = convertToShort(byteData); //convert to short
                    Object value = (double) temp/100; //convert to double

                    //To-do: how to publish context value?
                    contextManager.updateContext(String.format("%s_%s", contextName, description), value, agentName, messageTime);
                }
            }
        }
    }
}
