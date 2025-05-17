package kr.ac.kaist.cdsn.lapras.preference;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.action.ActionInstance;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.preference.algorithm.LearningAlgorithm;
import kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning.QLearning;
import kr.ac.kaist.cdsn.lapras.task.TaskNotification;
import kr.ac.kaist.cdsn.lapras.user.UserNotification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * Created by Daekeun Lee on 2017-04-05.
 */
public class PreferenceLearner extends Component {

    private static final Logger LOGGER = LoggerFactory.getLogger(PreferenceLearner.class);



    private Set<String> contextsOfInterest;
    private Set<String> actionsOfInterest;
    private String saveFileName;
    private String loadFileName;
    private int savePeriod;

    private LearningAlgorithm learningAlgorithm;

    public PreferenceLearner(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        contextsOfInterest = new HashSet<>(Arrays.asList(agent.getAgentConfig().getOptionAsArray("learning_contexts")));
        actionsOfInterest = new HashSet<>(Arrays.asList(agent.getAgentConfig().getOptionAsArray("learning_actions")));
        saveFileName = agent.getAgentConfig().getOption("learning_save_file");
        savePeriod = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("learning_save_period", "1"));
        loadFileName = agent.getAgentConfig().getOption("learning_load_file");
    }

    @Override
    public void setUp() {
        learningAlgorithm = new QLearning(agent.getFunctionalityExecutor(), contextsOfInterest, actionsOfInterest);

        if (saveFileName != null) {
            learningAlgorithm.enableSave(saveFileName, savePeriod);
        }

        if (loadFileName != null) {
            learningAlgorithm.loadLearnedModel(loadFileName);
        }
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.CONTEXT_UPDATED);
        subscribeEvent(EventType.ACTION_TAKEN);
        subscribeEvent(EventType.TASK_NOTIFIED);
        subscribeEvent(EventType.USER_NOTIFIED);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case CONTEXT_UPDATED:
                ContextInstance context = (ContextInstance) event.getData();
                learningAlgorithm.contextUpdated(context.getName(), context.getValue());
                break;
            case ACTION_TAKEN:
                ActionInstance action = (ActionInstance) event.getData();
                learningAlgorithm.actionTaken(action.getAction());
                break;
            case TASK_NOTIFIED:
                TaskNotification task = (TaskNotification) event.getData();
                learningAlgorithm.taskNotified(task.getName());
                break;
            case USER_NOTIFIED:
                UserNotification user = (UserNotification) event.getData();
                learningAlgorithm.userNotified(user.getName());
                break;
        }
        return true;
    }

    public LearningAlgorithm getLearningAlgorithm() {
        return learningAlgorithm;
    }
}
