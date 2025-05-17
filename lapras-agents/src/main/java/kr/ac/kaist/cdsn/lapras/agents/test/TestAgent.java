package kr.ac.kaist.cdsn.lapras.agents.test;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import kr.ac.kaist.cdsn.lapras.rest.RestServer;
import kr.ac.kaist.cdsn.lapras.rule.RuleExecutor;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public class TestAgent extends AgentComponent {
    private static Logger LOGGER = LoggerFactory.getLogger(TestAgent.class);

    public TestAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        testContext.setInitialValue(0);
    }

    @ContextField(publishInterval = 10)
    public Context testContext;

    public static void main(String[] args) {
        AgentConfig agentConfig = new AgentConfig("TestAgent")
                .setPlaceName("N1Lounge8F")
                .setBrokerAddress("tcp://wonder.kaist.ac.kr:18830")
                .setOption("rule_file_path", Resource.pathOf("TestRule.txt"));

        try {
            Agent testAgent = new Agent(TestAgent.class, agentConfig);
            testAgent.addComponent(RuleExecutor.class);
            testAgent.addComponent(RestServer.class);
            testAgent.start();
        } catch (LaprasException e) {
            LOGGER.error("Failed to launch the agent", e);
        }
    }

    public void run() {
        while(true) {
            LOGGER.debug("TestContext = {}", (Integer) testContext.getValue());
            testContext.updateValue((Integer)testContext.getValue() + 1);
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }

    @FunctionalityMethod
    public void sayHello() {
        LOGGER.debug("Hello!");
    }
}
