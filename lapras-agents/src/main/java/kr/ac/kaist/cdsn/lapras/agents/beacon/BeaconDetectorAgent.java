package kr.ac.kaist.cdsn.lapras.agents.beacon;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import tinyb.BluetoothDevice;
import tinyb.BluetoothException;
import tinyb.BluetoothManager;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;

/**
 * Created by Daekeun Lee on 2017-02-16.
 */
public class BeaconDetectorAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(BeaconDetectorAgent.class);

    private static final Long refreshInterval = 5000l;
    private static final String contextSuffix = "Location";

    private ConcurrentMap<String, Integer> missingCount = new ConcurrentHashMap<>();

    private class UserProfile {
        private String name;
        private String address;

        public UserProfile(String name, String address) {
            this.name = name;
            this.address = address;
        }

        public String getName() {
            return name;
        }

        public String getAddress() {
            return address;
        }
    }

    public BeaconDetectorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
    }

    private List<UserProfile> userProfiles;

    private List<BluetoothDevice> getDevices() {
        BluetoothManager bluetoothManager = BluetoothManager.getBluetoothManager();

        while(true) {
            List<BluetoothDevice> devices = bluetoothManager.getDevices();
            if (devices == null) {
                LOGGER.debug("An error occurred while scanning for bluetooth devices");
                try {
                    LOGGER.debug("Sleeping for 1 second");
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                }
                continue;
            }
            return devices;
        }
    }

    @Override
    public void run() {
        userProfiles = retrieveUserProfiles();
        if(userProfiles == null) return;

        subscribeContexts();

        for (UserProfile userProfile : userProfiles) {
            String contextName = userProfile.getName() + contextSuffix;
            contextManager.updateContext(contextName, "Unknown", agentName);
            contextManager.publishContext(contextName);
        }

        while(true) {
            BluetoothManager bluetoothManager = BluetoothManager.getBluetoothManager();
            boolean discoveryStarted = bluetoothManager.startDiscovery();
            LOGGER.debug("Bluetooth discoverty started: {}", (discoveryStarted ? "true" : "false"));

            List<BluetoothDevice> devices = getDevices();
            for (BluetoothDevice device : devices) {
                if(device.getRSSI() == 0 || device.getRSSI() < -100) continue;
                if(device.getName().equals("RECO")) {
                    LOGGER.debug("Found device: {} ({}), RSSI={}", device.getName(), device.getAddress(), device.getRSSI());
                    for (UserProfile userProfile : userProfiles) {
                        if(userProfile.getAddress().equalsIgnoreCase(device.getAddress())) {
                            boolean connected = device.getConnected();
                            if(!device.getConnected()) {
                                try {
                                    connected = device.connect();
                                } catch(BluetoothException e) {
                                }
                            }
                            LOGGER.debug("Connected to {} ({}): {}", device.getName(), device.getAddress(), connected);
                            if(!connected) continue;

                            LOGGER.debug("{} is near (estimated distance is {})", userProfile.getName(), estimateDistance((short)-50, device.getRSSI()));
                            String contextName = userProfile.getName() + contextSuffix;
                            ContextInstance oldContext = contextManager.getContext(contextName);
                            contextManager.updateContext(contextName, agent.getAgentConfig().getPlaceName(), agentName);
                            if(oldContext == null || !oldContext.getValue().equals(agent.getAgentConfig().getPlaceName())) {
                                contextManager.publishContext(contextName);
                            }

                            missingCount.put(contextName, 0);
                        }
                    }
                }
            }

            for (String contextName : missingCount.keySet()) {
                Integer count = missingCount.get(contextName);
                if(count >= 3) {
                    contextManager.updateContext(contextName, "Unknown", agentName);
                    contextManager.publishContext(contextName);
                    missingCount.remove(contextName);
                } else {
                    missingCount.put(contextName, count + 1);
                }
            }

            try {
                Thread.sleep(refreshInterval);
                bluetoothManager.stopDiscovery();
            } catch (InterruptedException e) {
                break;
            } catch (BluetoothException e) {
                LOGGER.error("Bluetooth exception!", e);
            }
        }

        BluetoothManager.getBluetoothManager().stopDiscovery();
    }

    private Double estimateDistance(short txPower, short rssi) {
        double ratio = rssi * 1.0 / txPower;
        if (ratio < 1.0) {
            return Math.pow(ratio, 10);
        } else {
            double accuracy =  (0.89976)*Math.pow(ratio,7.7095) + 0.111;
            return accuracy;
        }
    }

    private void subscribeContexts() {
        for (UserProfile userProfile : userProfiles) {
            contextManager.subscribeContext(userProfile.getName() + contextSuffix);
        }
    }

    private List<UserProfile> retrieveUserProfiles() {
        AgentConfig config = agent.getAgentConfig();
        String[] names = config.getOptionAsArray("user_name");
        String[] addresses = config.getOptionAsArray("beacon_address");
        if(names.length != addresses.length) {
            LOGGER.error("User profile configuration is malformed");
            return null;
        }

        List<UserProfile> userProfiles = new ArrayList<>(names.length);
        for (int i = 0; i < names.length; i++) {
            UserProfile userProfile = new UserProfile(names[i], addresses[i]);
            userProfiles.add(userProfile);
        }
        return userProfiles;
    }
}
