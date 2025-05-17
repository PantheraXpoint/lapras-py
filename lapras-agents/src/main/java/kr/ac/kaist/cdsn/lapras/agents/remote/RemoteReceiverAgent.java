package kr.ac.kaist.cdsn.lapras.agents.remote;

import com.phidgets.PhidgetException;
import com.phidgets.event.CodeEvent;
import com.phidgets.event.CodeListener;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agents.phidget.PhidgetIRController;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityInvocation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

public class RemoteReceiverAgent extends AgentComponent implements CodeListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(RemoteReceiverAgent.class);

    private final PhidgetIRController phidgetIRController;
    private final Map<String, String> codeFunctionalityMap = new HashMap<>();

    public RemoteReceiverAgent(EventDispatcher eventDispatcher, Agent agent) throws LaprasException {
        super(eventDispatcher, agent);

        String[] codes = agent.getAgentConfig().getOptionAsArray("ir.code");
        String[] functionalities = agent.getAgentConfig().getOptionAsArray("ir.functionality");

        if(codes.length != functionalities.length) {
            LOGGER.error("Number of codes and functionalities does not match");
            throw new LaprasException("Agent initialization failed");
        }

        for (int i = 0; i < codes.length; i++) {
            codeFunctionalityMap.put(codes[i], functionalities[i]);
        }

        int serial = Integer.parseInt(agent.getAgentConfig().getOption("phidget_serial"));
        try {
            phidgetIRController = new PhidgetIRController(serial, this);
        } catch (PhidgetException e) {
            LOGGER.error("Failed to initialize PhidgetIR", e);
            throw new LaprasException("Agent initialization failed");
        }
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
    public void code(CodeEvent codeEvent) {
        if(codeEvent.getRepeat()) return;

        String functionality = codeFunctionalityMap.get(codeEvent.getCode().toString().toLowerCase());
        if(functionality == null) return;

        FunctionalityInvocation functionalityInvocation = FunctionalityInvocation.fromString(functionality);
        functionalityInvocation.setByUser(true);
        functionalityExecutor.invokeRemoteFunctionality(functionalityInvocation.getName(), functionalityInvocation.getArguments());
        actionManager.taken(functionalityInvocation.getName());
    }
}
