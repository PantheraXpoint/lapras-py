package kr.ac.kaist.cdsn.lapras.learning;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by chad1231 on 2017-04-20.
 */
public class DefaultLearningBasedAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(DefaultLearningBasedAgent.class);

    public DefaultLearningBasedAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        // [STEP 1] need to register Learner's functions to this agent's functions
        registerLearnerFunction("setClassList","setClassList");
        registerLearnerFunction("startDataCollection", "startDataCollection");
        registerLearnerFunction("stopDataCollection", "stopDataCollection");
        registerLearnerFunction("setCurrentClass", "setCurrentClass");
        registerLearnerFunction("setLocalFeatureValues","setLocalFeatureValues");
        registerLearnerFunction("reloadTrainedModel", "reloadTrainedModel");

        // [STEP 2] declare the class names for supervision
        agent.getFunctionalityExecutor().invokeFunctionality("setClassList",
                agent.getAgentConfig().getOptionAsArray("class_list"));
    }

    @Override
    public void run() {

    }

    public String getClassID(String[] query){
        try {
            return ((SupervisedLearner) agent.getComponent(Class.forName("kr.ac.kaist.cdsn.lapras.learning.SupervisedLearner").
					asSubclass(Class.forName("kr.ac.kaist.cdsn.lapras.Component")))).getClassID(query);
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }

        return null;
    }

    private void registerLearnerFunction(String functionalityName, String methodName, Class<?>... parameterTypes){
        try {
            agent.getFunctionalityExecutor().registerFunctionality(functionalityName,
                    Class.forName("kr.ac.kaist.cdsn.lapras.learning.SupervisedLearner").
                            getMethod(methodName, parameterTypes),
                    agent.getComponent(Class.forName("kr.ac.kaist.cdsn.lapras.learning.SupervisedLearner").
                            asSubclass(Class.forName("kr.ac.kaist.cdsn.lapras.Component"))));
        } catch (NoSuchMethodException e) {
            e.printStackTrace();
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
