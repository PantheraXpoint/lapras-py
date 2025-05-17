package kr.ac.kaist.cdsn.lapras.agents.twosomeIRAgent;

import com.monnit.mine.BaseApplication.applicationclasses.PIRBase;
import com.monnit.mine.MonnitMineAPI.*;
import com.monnit.mine.MonnitMineAPI.enums.eFirmwareGeneration;
import com.monnit.mine.MonnitMineAPI.enums.eGatewayType;
import com.monnit.mine.MonnitMineAPI.enums.eMineListenerProtocol;
import com.monnit.mine.MonnitMineAPI.enums.eSensorApplication;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;


/**
 * Created by Bumjin Gwak on 2017-04-20.
 * Modified by Jeongwook Park on 2017-07-25.
 */

public class twosomeIRAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(twosomeIRAgent.class);

    private final List<Sensor> sensors = new ArrayList<>();
    private final String[] sensorIds, sensorNames;
    private final ConcurrentMap<Integer, String> sensorMap = new ConcurrentHashMap<>();

    /**
     * Initialize the member variables : sensors, sensorIds, sensorNames, sensorMap
     */

    public twosomeIRAgent(EventDispatcher eventDispatcher, Agent agent) {

        super(eventDispatcher, agent);

        sensorIds = agent.getAgentConfig().getOptionAsArray("motion_sensor_ids ");
        sensorNames = agent.getAgentConfig().getOptionAsArray("motion_sensor_names");

        int index = 0;
        for (String sensorId : sensorIds) {
            int sensorIdNumber = Integer.parseInt(sensorId);

            try {
                sensors.add (new Sensor(sensorIdNumber, eSensorApplication.Infared_Motion, "2.5.4.0", eFirmwareGeneration.Commercial));
                sensorMap.put(sensorIdNumber, sensorNames[index]);
            } catch (Exception e) {
                e.printStackTrace();
            }

            index++;
        }
    }

    @Override
    public void run() {

        eMineListenerProtocol Protocol;
        int port = 3010;
        MineServer _Server;
        String ipaddr = "127.0.0.1";

        Protocol = eMineListenerProtocol.TCP;
        InetAddress ip;
        try {

            ip = InetAddress.getByName(ipaddr);
            _Server = new MineServer(Protocol, ip, port);
            _Server.StartServer();

            System.out.println("Constructed Server.");

            if (_Server.addSensorDataProcessingHandler(new SensorMessageHandler())) {
                System.out.println("Added SensorHandler.");
            } else {
                System.out.println("Failed to add handler.");
            }

            int gatewayID = Integer.parseInt(agent.getAgentConfig().getOption("gateway_id"));
            Gateway usbGate = new Gateway(gatewayID, eGatewayType.USBService);

            _Server.RegisterGateway(usbGate);
            System.out.println();

            // Register sensor, edit sensor settings
            for (Sensor sensor : sensors) {
                _Server.RegisterSensor(usbGate.GatewayID, sensor);
                PIRBase.SensorEdit(sensor, null, 0.1, 2, 1, null);
            }

            System.out.println();

            Scanner sc = new Scanner(System.in);

            while (true) {
                try {
                    if(sc.nextLine().equalsIgnoreCase("exit")) break;
                } catch (Exception e) {
                    e.printStackTrace();
                    continue;
                }
            }

            _Server.StopServer();

        } catch (UnknownHostException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }

        while(true) {

        }
    }

    public class SensorMessageHandler implements iSensorMessageHandler {

        @Override
        public void ProcessSensorMessages(List<SensorMessage> sensorMessageList, Gateway gateway) throws Exception {

            for (SensorMessage msg : sensorMessageList) {

                System.out.println(msg.toString());

                String IRName = sensorMap.get(msg.SensorID);

                LOGGER.info(IRName + "Updated");

                if (msg.State == 2) {
                    contextManager.updateContext(IRName, true, agentName);
                } else {
                    contextManager.updateContext(IRName, false, agentName);
                }
            }
        }
    }
}
