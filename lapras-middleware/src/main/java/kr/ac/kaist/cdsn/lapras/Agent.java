package kr.ac.kaist.cdsn.lapras;

import kr.ac.kaist.cdsn.lapras.action.ActionManager;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.context.ContextManager;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityExecutor;
import kr.ac.kaist.cdsn.lapras.task.TaskManager;
import kr.ac.kaist.cdsn.lapras.user.UserManager;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.apache.log4j.PropertyConfigurator;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.util.LinkedList;
import java.util.List;
import java.util.Locale;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public class Agent {
    private final static Logger LOGGER = LoggerFactory.getLogger(Agent.class);

    private long startTime;

    private final AgentConfig agentConfig;
    private final EventDispatcher eventDispatcher;

    private final List<Component> components = new LinkedList<>();
    private final MqttCommunicator mqttCommunicator;
    private final ContextManager contextManager;
    private final FunctionalityExecutor functionalityExecutor;
    private final ActionManager actionManager;
    private final TaskManager taskManager;
    private final UserManager userManager;

    private AgentComponent agentComponent;

    public Agent(Class<? extends AgentComponent> agentClass, String configFilePath) throws LaprasException, IOException {
        this(agentClass, AgentConfig.fromStream(Resource.getStream(configFilePath)));
    }

    public Agent(Class<? extends AgentComponent> agentClass, AgentConfig agentConfig) throws LaprasException {
        PropertyConfigurator.configure(Resource.pathOf("log4j.properties"));
        Locale.setDefault(new Locale("ko","KR"));

        this.agentConfig = agentConfig;

        eventDispatcher = new EventDispatcher();

        try {
            mqttCommunicator = new MqttCommunicator(eventDispatcher, this);
            components.add(mqttCommunicator);
        } catch (MqttException e) {
            LOGGER.error("Cannot initialize MqttCommunicator", e);
            throw new LaprasException("Failed to initialize the agent", e);
        }

        contextManager = new ContextManager(eventDispatcher, this);
        components.add(contextManager);

        functionalityExecutor = new FunctionalityExecutor(eventDispatcher, this);
        components.add(functionalityExecutor);

        actionManager = new ActionManager(eventDispatcher, this);
        components.add(actionManager);

        taskManager = new TaskManager(eventDispatcher, this);
        components.add(taskManager);

        userManager = new UserManager(eventDispatcher, this);
        components.add(userManager);

        addComponent(agentClass);
        agentComponent = getComponent(agentClass);
    }

    public void addComponent(Class<? extends Component> componentClass) throws LaprasException {
        try {
            Component component = componentClass.getConstructor(EventDispatcher.class, Agent.class).newInstance(eventDispatcher, this);
            components.add(component);
        } catch (InstantiationException e) {
            LOGGER.error("Cannot instantiate component {}", componentClass.getName(), e);
            throw new LaprasException("Failed to add a component", e);
        } catch (InvocationTargetException e) {
            LOGGER.error("An error occurred while instantiating component {}", componentClass.getName(), e);
            throw new LaprasException("Failed to add a component", e);
        } catch (NoSuchMethodException e) {
            throw new LaprasException("Unexpected exception has occurred", e);
        } catch (IllegalAccessException e) {
            throw new LaprasException("Unexpected exception has occurred", e);
        }
    }

    public void start() {
        startTime = System.currentTimeMillis();

        eventDispatcher.start();

        for(Component component : components) {
            component.start();
        }
    }

    public <T extends Component> T getComponent(Class<T> componentClass) {
        for(Component component : components) {
            if(componentClass.isInstance(component)) {
                return (T) component;
            }
        }
        return null;
    }

    public AgentComponent getAgentComponent() { return agentComponent; }

    public MqttCommunicator getMqttCommunicator() {
        return mqttCommunicator;
    }

    public AgentConfig getAgentConfig() {
        return agentConfig;
    }

    public FunctionalityExecutor getFunctionalityExecutor() {
        return functionalityExecutor;
    }

    public ContextManager getContextManager() {
        return contextManager;
    }

    public ActionManager getActionManager() {
        return actionManager;
    }

    public UserManager getUserManager() {return userManager;}

    public long getStartTime() {
        return startTime;
    }

    public long getUptime() {
        return System.currentTimeMillis() - getStartTime();
    }

    public TaskManager getTaskManager() {return taskManager;}
}
