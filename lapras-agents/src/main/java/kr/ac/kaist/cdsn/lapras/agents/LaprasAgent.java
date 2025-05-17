package kr.ac.kaist.cdsn.lapras.agents;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.apache.log4j.PropertyConfigurator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URL;

/**
 * Created by Daekeun Lee on 2017-04-19.
 */
public class LaprasAgent {
    private static final Logger LOGGER = LoggerFactory.getLogger(LaprasAgent.class);

    private static final String AGENT_PACKAGE = "kr.ac.kaist.cdsn.lapras.agents.";
    private static final String COMPONENT_PACKAGE = "kr.ac.kaist.cdsn.lapras.";

    public static void main(String... args) {
        PropertyConfigurator.configure(Resource.pathOf("log4j.properties"));

        if(args.length < 1) {
            LOGGER.error("Configuration file path must be specified in the first argument");
            System.exit(1); return;
        }

        String configFilePath = args[0];
        AgentConfig agentConfig;
        if(configFilePath.startsWith("http")) {
            LOGGER.debug("Loading configuration file from web at {}", configFilePath);
            try {
                URL url = new URL(configFilePath);
                agentConfig = AgentConfig.fromStream(url.openStream());
            } catch (MalformedURLException e) {
                LOGGER.error("Invalid config file path {}", configFilePath, e);
                System.exit(1);
                return;
            } catch (IOException e) {
                LOGGER.error("An error occurred while loading the configuration file {}", configFilePath, e);
                System.exit(1);
                return;
            }
        } else {
            try {
                LOGGER.debug("Loading configuration file at {}", configFilePath);
                agentConfig = AgentConfig.fromStream(Resource.getStream(configFilePath));
            } catch (IOException e) {
                LOGGER.error("An error occurred while loading the configuration file {}", configFilePath, e);
                System.exit(1);
                return;
            }
        }

        String agentClassName = AGENT_PACKAGE + agentConfig.getOption("agent_class_name");
        String[] componentNames = agentConfig.getOptionAsArray("component_class_names");
        try {
            LOGGER.debug("Loading agent class {}", agentClassName);
            Agent agent = new Agent((Class<? extends AgentComponent>) Class.forName(agentClassName), agentConfig);

            for (String componentClassName : componentNames) {
                LOGGER.debug("Loading component {}", COMPONENT_PACKAGE+ componentClassName);
                agent.addComponent((Class<? extends Component>) Class.forName(COMPONENT_PACKAGE + componentClassName));
            }

            LOGGER.debug("Starting {}", agentConfig.getAgentName());
            agent.start();
        } catch (LaprasException e) {
            LOGGER.error("An error occurred while launching the agent", e);
            System.exit(1); return;
        } catch (ClassNotFoundException e) {
            LOGGER.error("No such agent class for name", e);
            System.exit(1); return;
        }
    }
}
