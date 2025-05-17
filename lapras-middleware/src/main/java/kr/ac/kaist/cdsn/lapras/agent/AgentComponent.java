package kr.ac.kaist.cdsn.lapras.agent;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.action.ActionManager;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.context.ContextManager;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityExecutor;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalitySignature;
import kr.ac.kaist.cdsn.lapras.user.UserManager;
import kr.ac.kaist.cdsn.lapras.util.NameUtil;
import org.apache.commons.lang3.text.WordUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public abstract class AgentComponent extends Component implements Runnable {
    private static Logger LOGGER = LoggerFactory.getLogger(AgentComponent.class);

    public static final String OPERATING_STATUS_SUFFIX = "OperatingStatus";
    public static final Integer OPERATING_STATUS_INTERVAL = 300;

    protected String agentName;
    private String operatingStatusName;

    protected final MqttCommunicator mqttCommunicator;
    protected final ContextManager contextManager;
    protected final FunctionalityExecutor functionalityExecutor;
    protected final ActionManager actionManager;
    protected final UserManager userManager;

    private AgentConfig agentConfig;
    private Thread agentThread;
    private Map<String, String> contextFieldMap;
    private Map<String, Context> contextMap = new ConcurrentHashMap<>();

    public AgentComponent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        this.agentConfig = agent.getAgentConfig();
        this.agentName = agentConfig.getAgentName();
        this.mqttCommunicator = agent.getMqttCommunicator();
        this.contextManager = agent.getContextManager();
        this.functionalityExecutor = agent.getFunctionalityExecutor();
        this.actionManager = agent.getActionManager();
        this.userManager = agent.getUserManager();

        processAnnotations();
        for (String contextName : agentConfig.getOptionAsArray("subscribe_contexts")) {
            contextManager.subscribeContext(contextName);
        }

        operatingStatusName = agentName + OPERATING_STATUS_SUFFIX;
        ContextInstance contextInstance = new ContextInstance(operatingStatusName, "Dead", System.currentTimeMillis(), agentName);
        LaprasTopic topic = new LaprasTopic(null, MessageType.CONTEXT, operatingStatusName);
        mqttCommunicator.setWill(topic, contextInstance.getPayload(), 2, true);
    }

    private void processAnnotations() {
        // ContextInstance fields
        contextFieldMap = new ConcurrentHashMap<>();
        for(Field field : this.getClass().getDeclaredFields()) {
            ContextField contextFieldAnnotation = field.getAnnotation(ContextField.class);
            if(contextFieldAnnotation != null) {
                String contextName = NameUtil.expand(contextFieldAnnotation.name(), agentConfig);
                if (contextName.isEmpty()) {
                    contextName = WordUtils.capitalize(field.getName());
                }

                if(field.getType().equals(Context.class)) {
                    Context context = new Context(contextName, null, this);
                    field.setAccessible(true);
                    try {
                        field.set(this, context);
                    } catch (IllegalAccessException e) {
                    }

                    contextMap.put(contextName, context);
                } else {
                    LOGGER.warn("This type of context field is deprecated. Please use Context type.");
                    contextFieldMap.put(contextName, field.getName());
                }
                contextManager.subscribeContext(contextName);

                if (contextFieldAnnotation.publishInterval() > 0) {
                    contextManager.setPeriodicPublish(contextName, contextFieldAnnotation.publishInterval());
                }
                if (contextFieldAnnotation.publishAsUpdated()) {
                    contextManager.setPublishAsUpdated(contextName);
                }
            }
        }

        if(contextFieldMap.size() > 0) {
            subscribeEvent(EventType.CONTEXT_UPDATED);
        }

        // Functionality methods
        for(Method method : this.getClass().getDeclaredMethods()) {
            FunctionalityMethod functionalityMethodAnnotation = method.getAnnotation(FunctionalityMethod.class);
            if(functionalityMethodAnnotation != null) {
                String functionalityName = FunctionalitySignature.getFunctionalityName(method);
                functionalityExecutor.registerFunctionality(functionalityName, method, this);
            }
        }
    }

    @Override
    public void setUp() {
        contextManager.updateContext(operatingStatusName, "Alive", agentName);
        contextManager.setPeriodicPublish(operatingStatusName, OPERATING_STATUS_INTERVAL);

        for(String contextName : contextFieldMap.keySet()) {
            this.contextManager.subscribeContext(contextName);
        }
    }

    @Override
    public void start() {
        super.start();

        this.agentThread = new Thread(this);
        this.agentThread.setName(this.getClass().getSimpleName());
        this.agentThread.start();
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.CONTEXT_UPDATED);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case CONTEXT_UPDATED:
                ContextInstance contextInstance = (ContextInstance) event.getData();
                Context context = contextMap.get(contextInstance.getName());
                String fieldName = contextFieldMap.get(contextInstance.getName());
                if(context == null && fieldName == null) return true;

                if(context != null) {
                    LOGGER.debug("Updating context instance {}", context.getName());
                    context.setInstance(contextInstance);
                } else {
                    LOGGER.debug("Setting context field {} to {}", fieldName, contextInstance.getValue());
                    try {
                        setContextField(fieldName, contextInstance.getValue());
                    } catch (NoSuchFieldException e) {
                    }
                }
                return true;
        }
        return false;
    }

    public void setContextField(String fieldName, Object value) throws NoSuchFieldException {
        Field field = this.getClass().getDeclaredField(fieldName);
        if(field == null) return;
        try {
            field.setAccessible(true);
            field.set(this, value);
        } catch (IllegalAccessException e) {
            return;
        }
    }
}
