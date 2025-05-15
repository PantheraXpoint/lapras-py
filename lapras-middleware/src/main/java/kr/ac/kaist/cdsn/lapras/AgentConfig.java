package kr.ac.kaist.cdsn.lapras;

import org.apache.commons.configuration.ConfigurationException;
import org.apache.commons.configuration.PropertiesConfiguration;

import java.io.*;
import java.util.Iterator;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public class AgentConfig {
    private final PropertiesConfiguration options = new PropertiesConfiguration();

    public AgentConfig(String agentName) {
        options.setProperty("agent_name", agentName);
    }

    private AgentConfig() {}

    public static AgentConfig fromFile(String path) throws FileNotFoundException {
        AgentConfig agentConfig = new AgentConfig();
        try {
            agentConfig.options.load(new FileReader(path));
        } catch (ConfigurationException e) {
            return null;
        }
        return agentConfig;
    }

    public static AgentConfig fromStream(InputStream inputStream) throws IOException {
        AgentConfig agentConfig = new AgentConfig();
        try {
            agentConfig.options.load(new InputStreamReader(inputStream));
        } catch (ConfigurationException e) {
            return null;
        }
        return agentConfig;
    }

    public String getAgentName() {
        return getOption("agent_name");
    }

    public AgentConfig setAgentName(String agentName) {
        setOption("agent_name", agentName);
        return this;
    }

    public String getBrokerAddress() {
        return getOption("broker_address");
    }

    public AgentConfig setBrokerAddress(String brokerAddress) {
        setOption("broker_address", brokerAddress);
        return this;
    }

    public String getPlaceName() {
        return getOption("place_name");
    }

    public AgentConfig setPlaceName(String placeName) {
        setOption("place_name", placeName);
        return this;
    }

    public String getOption(String optionName) {
        return options.getString(optionName);
    }

    public String getOptionOrDefault(String optionName, String defaultValue) {
        String option = getOption(optionName);
        if(option != null) return option;
        return defaultValue;
    }

    public String[] getOptionAsArray(String optionName) {
        return options.getStringArray(optionName);
    }

    public AgentConfig setOption(String optionName, String optionValue) {
        options.setProperty(optionName, optionValue);
        return this;
    }

    public Iterator<String> listOptionNames() {
        return options.getKeys();
    }
}
