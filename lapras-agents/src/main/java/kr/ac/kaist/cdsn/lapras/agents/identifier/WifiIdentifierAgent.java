package kr.ac.kaist.cdsn.lapras.agents.identifier;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * Created by Daekeun Lee on 2017-07-14.
 */
public class WifiIdentifierAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(WifiIdentifierAgent.class);
    private static final String PRESENCE_CONTEXT_SUFFIX = "Presence";
    private static final int POWER_THRESHOLD = -65;
    private static final long DISAPPEAR_TIME_THRESHOLD = 60000; // 60 seconds
    private final String networkDevice;

    private class WifiDevice {
        public final DateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

        public String mac;
        public Date firstTimeSeen;
        public Date lastTimeSeen;
        public int power;

        public WifiDevice(String mac, String firstTimeSeenString, String lastTimeSeenString, int power) {
            this.mac = mac;
            try {
                this.firstTimeSeen = dateFormat.parse(firstTimeSeenString);
                this.lastTimeSeen = dateFormat.parse(lastTimeSeenString);
            } catch (ParseException e) {
                throw new IllegalArgumentException(e);
            }
            this.power = power;
        }

        public WifiDevice(String mac, Date firstTimeSeen, Date lastTimeSeen, int power) {
            this.mac = mac;
            this.firstTimeSeen = firstTimeSeen;
            this.lastTimeSeen = lastTimeSeen;
            this.power = power;
        }
    }

    private class DeviceProfile {
        public String type;
        public String mac;
        public String owner;

        public DeviceProfile(String type, String mac, String owner) {
            this.type = type;
            this.mac = mac.replace("-", ":").toUpperCase();
            this.owner = owner;
        }
    }

    private Process airodumpProcess;
    private Set<String> userNameList = new HashSet<>();
    private Map<String, DeviceProfile> deviceProfileMap = new HashMap<>();
    private Map<String, Long> lastTimeSeenMap = new HashMap<>();
    private Map<String, Integer> lastDevicePowerMap = new HashMap<>();

    public WifiIdentifierAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        networkDevice = agent.getAgentConfig().getOption("network_device");
        String macAddressConfigFilename = agent.getAgentConfig().getOption("mac_address_config_filename");
        InputStream is = Resource.getStream(macAddressConfigFilename);
        JsonParser jsonParser = new JsonParser();
        JsonObject jsonObject = jsonParser.parse(new InputStreamReader(is)).getAsJsonObject();
        for (JsonElement _user : jsonObject.getAsJsonArray("users")) {
            JsonObject user = _user.getAsJsonObject();
            String name = user.get("name").getAsString();
            userNameList.add(name);

            for (JsonElement _device : user.getAsJsonArray("devices")) {
                JsonObject device = _device.getAsJsonObject();
                DeviceProfile deviceProfile = new DeviceProfile(device.get("type").getAsString(), device.get("mac").getAsString(), name);
                deviceProfileMap.put(deviceProfile.mac, deviceProfile);
            }
        }

        for (String userName : userNameList) {
            contextManager.setPublishAsUpdated(makeContextName(userName));
        }

        try {
            Process p = Runtime.getRuntime().exec("id -u");
            BufferedReader in = new BufferedReader(new InputStreamReader(p.getInputStream()));
            Integer userId = Integer.parseInt(in.readLine());
            if(userId != 0) {
                LOGGER.error("WifiIdentifierAgent agent must be called with sudo privilege.");
                System.exit(1);
            }
        } catch (IOException e) {
            LOGGER.error("Failed to check user permission");
            System.exit(1);
        }

        runAirodump();
    }

    private void runAirodump() {
        Runtime runtime = Runtime.getRuntime();
        String[] mkdirCmd = {"mkdir", "-p", "/var/lapras"};
        String[] removeCmd = {"sh", "-c", "rm -f /var/lapras/airodump*.csv"}; // Remove all previous dump files
        String[] runCmd = {"screen", "-dm", "airodump-ng", networkDevice,       // Run airodump on mon0 (should be configured beforehand)
                "--write", "/var/lapras/airodump",    // Dump file are created in the resource directory with prefix lapras-airodump
                "--output-format", "csv"};              // Dump format is CSV

        try {
            Process p = runtime.exec(mkdirCmd);
            p.waitFor();
            p = runtime.exec(removeCmd);
            p.waitFor();
            airodumpProcess = runtime.exec(runCmd, null, new File(Resource.RESOURCE_PATH));
            runtime.addShutdownHook(new Thread(()-> {
                try {
                    runtime.exec(new String[] {"killall", "airodump-ng"});
                } catch (IOException e) {
                }
            }));
        }catch(Exception e) {
            LOGGER.error("An error occurred while launching airodump-ng", e);
        }
    }

    private String makeContextName(String userName) {
        return userName.replaceAll(" ", "") + PRESENCE_CONTEXT_SUFFIX;
    }

    @Override
    public void run() {
        while(true) {
            Set<WifiDevice> devices = parseDump("/var/lapras/airodump-01.csv");
            if (devices == null) {
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                }
                continue;
            }

            LOGGER.debug("Device list =======================");
            for (WifiDevice device : devices) {
                if(deviceProfileMap.containsKey(device.mac)) {
                    DeviceProfile deviceProfile = deviceProfileMap.get(device.mac);
                    LOGGER.debug("{} of {} detected with power {} about {} seconds ago", deviceProfile.type, deviceProfile.owner, device.power, (System.currentTimeMillis() - device.lastTimeSeen.getTime()) / 1000);
                    if(device.power < -1) {
                        lastTimeSeenMap.put(device.mac, device.lastTimeSeen.getTime());
                        lastDevicePowerMap.put(device.mac, device.power);
                    }
                }
            }
            LOGGER.debug("===================================");

            Map<String, Boolean> contextTempValue = new HashMap<>();
            for (String mac : lastTimeSeenMap.keySet()) {
                boolean presence = System.currentTimeMillis() - lastTimeSeenMap.get(mac) < DISAPPEAR_TIME_THRESHOLD && lastDevicePowerMap.get(mac) > POWER_THRESHOLD;
                String contextName = makeContextName(deviceProfileMap.get(mac).owner);
                contextTempValue.put(contextName, contextTempValue.getOrDefault(contextName, false) | presence);
            }

            for (String contextName : contextTempValue.keySet()) {
                ContextInstance contextInstance = contextManager.getContext(contextName);
                if (contextInstance == null || (boolean) contextInstance.getValue() != contextTempValue.get(contextName)) {
                    contextManager.updateContext(contextName, contextTempValue.get(contextName), agentName);
                }
            }

            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    private Set<WifiDevice> parseDump(String filename) {
        Set<WifiDevice> devices = new HashSet<>();

        try (BufferedReader br = new BufferedReader(new FileReader(filename))) {
            String line = null;
            while ((line = br.readLine()) != null) {
                System.out.println(line);
            }
        } catch (FileNotFoundException e) {
            LOGGER.info("Dump file not ready");
            return null;
        } catch (IOException e) {
            LOGGER.info("Dump file not ready");
            return null;
        }

        try {
            BufferedReader br = new BufferedReader(new FileReader(filename));
            String line = br.readLine();
            if(line == null) return devices;
            while(line.trim().equals("")) { line = br.readLine(); }

            // Skip APs
            while(!line.trim().equals("")) { line = br.readLine(); }

            // Read devices
            br.readLine(); br.readLine();
            line = br.readLine();
            while(line != null && !line.trim().equals("")) {
                String[] fields = line.split(",");
                assert fields.length == 7;
                WifiDevice device = new WifiDevice(fields[0].trim(), fields[1].trim(), fields[2].trim(), Integer.parseInt(fields[3].trim()));
                devices.add(device);
                line = br.readLine();
            }
        } catch (IOException e) {
            LOGGER.info("Dump file not ready");
            return null;
        } catch (Exception e) {
            LOGGER.error("Unknown exception occurred while parsing the dump", e);
            return null;
        }
        return devices;
    }
}
