package kr.ac.kaist.cdsn.lapras.functionality;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.util.DataType;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;
import java.util.stream.Collectors;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
public class FunctionalityExecutor extends Component {
    private static Logger LOGGER = LoggerFactory.getLogger(FunctionalityExecutor.class);

    private final ExecutorService functionalityExecutor = Executors.newSingleThreadExecutor();
    private final ConcurrentMap<String, Consumer<Object[]>> functionalityFunctionMap = new ConcurrentHashMap<>();
    private final ConcurrentMap<String, FunctionalitySignature> functionalitySignatureMap = new ConcurrentHashMap<>();

    private final MqttCommunicator mqttCommunicator;
    private final String agentName;

    public FunctionalityExecutor(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        mqttCommunicator = agent.getMqttCommunicator();
        agentName = agent.getAgentConfig().getAgentName();
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.MESSAGE_ARRIVED);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case MESSAGE_ARRIVED:
                LaprasTopic topic = (LaprasTopic) ((Object[]) event.getData())[0];
                byte[] payload = (byte[]) ((Object[]) event.getData())[1];
                if(!topic.getMessageType().equals(MessageType.FUNCTIONALITY)) return true;
                FunctionalityInvocation functionalityInvocation = FunctionalityInvocation.fromPayload(payload);
                if(functionalityInvocation == null) return true;
                invokeFunctionality(functionalityInvocation);
                return true;
        }
        return false;
    }

    public FunctionalitySignature getFunctionalitySignature(String functionalityName) {
        return functionalitySignatureMap.get(functionalityName);
    }

    public List<FunctionalitySignature> listFunctionalitySignatures() {
        return functionalitySignatureMap.entrySet().stream().map(entry->entry.getValue()).collect(Collectors.toList());
    }

    public void registerFunctionality(String functionalityName, Consumer<Object[]> function) {
        functionalityFunctionMap.put(functionalityName, function);

        FunctionalitySignature signature = new FunctionalitySignature(functionalityName, new ArrayList<>(), "");
        functionalitySignatureMap.put(functionalityName, signature);

        LOGGER.debug("Functionality {} has been registered", functionalityName);

        LaprasTopic topic = new LaprasTopic(null, MessageType.FUNCTIONALITY, functionalityName);
        mqttCommunicator.subscribeTopic(topic);
    }

    public void registerFunctionality(String functionalityName, Method method, Object instance) {
        FunctionalitySignature signature = FunctionalitySignature.fromMethodWithName(functionalityName, method);
        registerFunctionality(functionalityName, (arguments)->{
            try {
                method.invoke(instance, arguments);
            } catch (IllegalAccessException e) {
                LOGGER.error("Cannot invoke the method {} of {}", method.getName(), instance.toString(), e);
            } catch (InvocationTargetException e) {
                LOGGER.error("An error occurred while executing functionality {}", functionalityName, e);
            }
        });
        functionalitySignatureMap.put(functionalityName, signature);
    }

    public void invokeFunctionality(String functionalityName, Object[] arguments) {
        FunctionalityInvocation functionalityInvocation = new FunctionalityInvocation(functionalityName, arguments, System.currentTimeMillis(), agentName);
        invokeFunctionality(functionalityInvocation);
    }

    public void invokeRemoteFunctionality(String functionalityName, Object[] arguments) {
        FunctionalityInvocation functionalityInvocation = new FunctionalityInvocation(functionalityName, arguments, System.currentTimeMillis(), agentName);
        LaprasTopic topic = new LaprasTopic(null, MessageType.FUNCTIONALITY, functionalityName);
        mqttCommunicator.publish(topic, functionalityInvocation);
    }

    private void invokeFunctionality(FunctionalityInvocation functionalityInvocation) {
        final String functionalityName = functionalityInvocation.getName();
        final Consumer<Object[]> function = functionalityFunctionMap.get(functionalityName);
        final Object[] arguments = processArguments(functionalityInvocation.getArguments(), functionalitySignatureMap.get(functionalityName));
        functionalityExecutor.execute(() -> {
            LOGGER.debug("Invoking functionality {}", functionalityName);
            function.accept(arguments);
        });
    }

    private Object[] processArguments(Object[] arguments, FunctionalitySignature signature) {
        if(arguments == null) {
            if(signature.getParameters().size() != 0) {
                throw new IllegalArgumentException("Number of arguments don't agree");
            }
            return null;
        } else if(arguments.length != signature.getParameters().size()) {
            throw new IllegalArgumentException("Number of arguments don't agree");
        }

        Object[] result = new Object[arguments.length];
        for (int i = 0; i < signature.getParameters().size(); i++) {
            FunctionalitySignature.ParameterSignature parameterSignature = signature.getParameters().get(i);
            if(parameterSignature.getType() == DataType.FILE) {
                String fileBase64 = ((String) arguments[i]).replaceAll("\n", "");
                byte[] bytes = Base64.getDecoder().decode(fileBase64);
                try {
                    File tempfile = File.createTempFile("lapras", null);
                    FileUtils.writeByteArrayToFile(tempfile, bytes);
                    String path = tempfile.getAbsolutePath();
                    result[i] = new File(path);
                } catch (IOException e) {
                    LOGGER.error("Error while saving to temp file", e);
                    result[i] = null;
                    continue;
                }
            } else {
                result[i] = arguments[i];
            }
        }
        return result;
    }
}
