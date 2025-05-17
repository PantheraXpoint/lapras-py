package kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning;

import kr.ac.kaist.cdsn.lapras.action.Action;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityExecutor;
import kr.ac.kaist.cdsn.lapras.preference.algorithm.LearningAlgorithm;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

/**
 * Created by Daekeun Lee on 2017-02-15.
 * Designed for single-user, single-task Q-learning
 */
public class QLearning implements LearningAlgorithm {
    private static final Logger LOGGER = LoggerFactory.getLogger(QLearning.class);

    private static final double LEARNING_RATE = 0.75;
    private static final double DISCOUNT_FACTOR = 0.25;
    private static final double POSITIVE_REWARD = 1.0;
    private static final double NEGATIVE_REWARD = -1.0;
    private static final double RANDOM_ACTION_CHANCE = 0.05;
    private static final long FUNCTIONALITY_COOL_TIME = 3000; // ms
    private static final QTableManager qTableManager = new QTableManager();

    // For saving & loading Q-tables
    private int savePeriod = 1;
    private boolean enableSave = false;
    private boolean modelLoaded = false;
    private String saveFileName = null;
    private int updateCount = 0;

    private FunctionalityExecutor functionalityExecutor;
    private ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    private String currentUser;
    private String currentTask;
    private ConcurrentMap<String, Object> state = new ConcurrentHashMap<>();
    private List<ActionResult> actionResults = new LinkedList<>();
    private ConcurrentMap<String, ConcurrentMap<FrozenState, Integer>> visitCounts = new ConcurrentHashMap<>();
    private CopyOnWriteArraySet<Action> actionHistory = new CopyOnWriteArraySet<>();
    private Set<String> seenContexts = new HashSet<>();

    private final Set<String> contextsOfInterest;
    private final Set<String> actionsOfInterest;
    private boolean startLearning = false;

    public QLearning(FunctionalityExecutor functionalityExecutor, Set<String> contextsOfInterest, Set<String> actionsOfInterest) {
        this.functionalityExecutor = functionalityExecutor;
        this.contextsOfInterest = contextsOfInterest;
        this.actionsOfInterest = actionsOfInterest;

        currentTask = "Idle";
        ConcurrentMap<String, QTable> qTables = qTableManager.getQTables();
        qTables.put(currentTask, new QTable());
        visitCounts.put(currentTask, new ConcurrentHashMap<>());
    }

    @Override
    public void taskNotified(String name) {
        // Give positive reward to all actions in the queue before task transition
        for (ActionResult actionResult : actionResults) {
            if (actionResult.getFuture().isDone()) continue;

            // Cancel the scheduled job first
            actionResult.getFuture().cancel(true);
            // Give positive reward
            updateQValue(actionResult.getCurrentState(), actionResult.getAction(), actionResult.getExpectedFutureReward(), POSITIVE_REWARD);
        }

        LOGGER.debug("Task notified: {}", name);
        currentTask = name;

        // Flush action history per every task initiation
        actionHistory.clear();
        ConcurrentMap<String, QTable> qTables = qTableManager.getQTables();

        if (!qTables.containsKey(currentTask)) {
            LOGGER.debug("Task first seen: {}", currentTask);
            qTables.put(currentTask, new QTable());
        }

        doBestAction();
    }

    @Override
    public void actionTaken(Action action) {
        if (!actionsOfInterest.contains(action.getName())) return;
        LOGGER.debug("Action taken: {}", action.getName());
        if (!startLearning) return;

        actionResults.removeIf((actionResult) -> actionResult.getFuture().isDone());

        // Remove opposing action from the history
        for (Action pastAction : actionHistory) {
            if (pastAction.isOpposite(action)) {
                actionHistory.remove(pastAction);
            }
        }
        // Add action to the history
        actionHistory.add(action);

        // Give negative reward to opposing action
        for (ActionResult actionResult : actionResults) {
            if (actionResult.getAction().isOpposite(action) ||
                    (actionResults.indexOf(actionResult) == actionResults.size() - 1 &&
                            actionResult.getAction().isStillAction())) {
                actionResult.getFuture().cancel(true);
                updateQValue(actionResult.getCurrentState(), actionResult.getAction(), actionResult.getExpectedFutureReward(), NEGATIVE_REWARD);
                updateQValue(actionResult.getCurrentState(), action, actionResult.getExpectedFutureReward(), POSITIVE_REWARD); //why?
            }
        }

        FrozenState currentState = new FrozenState(state);
        scheduler.schedule(() -> {
            QTable qTable = qTableManager.getQTable(currentTask);
            Double expectedFutureReward = qTable.get(new FrozenState(state)).get(getBestAction());
            updateQValue(currentState, action, expectedFutureReward, POSITIVE_REWARD);
        }, 3, TimeUnit.SECONDS);
    }

    private void updateQValue(FrozenState currentState, Action action, double expectedFutureReward, double reward) {
        if (action.getName().equals("Still")) return;

        QTable qTable = qTableManager.getQTable(currentTask);
        Map<Action, Double> actionValue = qTable.get(currentState);

        Double oldQValue = actionValue.getOrDefault(action, 0.0);
        Double learnedValue = reward + DISCOUNT_FACTOR * expectedFutureReward;
        Double learningRate = LEARNING_RATE / incVisitCount(currentTask, currentState);
        //actionValue.put(action, oldQValue * (1 - LEARNING_RATE) + learnedValue * LEARNING_RATE);
        actionValue.put(action, oldQValue * (1 - learningRate) + learnedValue * learningRate);
        LOGGER.debug("Q value updated; current state = {}, action = {}, old value = {}, new value = {}",
                currentState.toString(), action, oldQValue, actionValue.get(action));
        qTableManager.printQTableAll();

        if (enableSave && (this.updateCount % savePeriod) == 0)
            if (currentUser == null) {
                qTableManager.saveQTables(saveFileName);
            } else {
                qTableManager.saveQTables(currentUser);
            }
        this.updateCount += 1;
    }

    private int incVisitCount(String task, FrozenState state) {
        if (!visitCounts.containsKey(task)) {
            visitCounts.put(task, new ConcurrentHashMap<>());
        }

        int currentCount = visitCounts.get(task).getOrDefault(state, 0);
        visitCounts.get(task).put(state, currentCount+1);

        return currentCount + 1;
    }

    @Override
    public void contextUpdated(String contextName, Object contextValue) {
        if (contextName.endsWith(AgentComponent.OPERATING_STATUS_SUFFIX)) return;

        LOGGER.debug("Updating context {} = {}", contextName, contextValue);

        if (!modelLoaded) { // We assume that learnt model already construct state space.
            constructStateSpace(contextName, contextValue);
        }

        state.put(contextName, contextValue);

        if (!startLearning) {
            if (state.keySet().containsAll(contextsOfInterest)) {
                startLearning = true;
            } else {
                LOGGER.debug("Learning not yet started; current state is {}; missing {}", state,
                        contextsOfInterest.stream().filter(a -> !state.keySet().contains(a)).collect(Collectors.toSet()));
                return;
            }
        }

        FrozenState currentState = new FrozenState(state);

        visitCounts.get(currentTask).put(currentState, visitCounts.get(currentTask).getOrDefault(currentState, 0) + 1);

        doBestAction();
    }

    @Override
    public void userNotified(String name) {
        LOGGER.debug("User notified: {}", name);

        if (currentUser != null && currentUser.equals(name)) { // When user go out
            LOGGER.debug("User {} goes out. Saving preferences...", name);

            if (enableSave) {
                qTableManager.saveQTables(name);
            }
            currentUser = null;
            currentTask = "Idle";
            initializeQTables();
        } else if (currentUser == null) { // When user come in
            LOGGER.debug("User {} comes in. Loading  preferences...", name);
            currentUser = name;
            loadLearnedModel(name);
        }
    }

    @Override
    public void enableSave(String filename, int period) {
        enableSave = true;
        savePeriod = period;
        saveFileName = filename;
    }

    @Override
    public void loadLearnedModel(String filename) {
        try {
            qTableManager.loadQTables(filename);
            modelLoaded = true;
        } catch (IOException e) {
            LOGGER.debug("File loading failed. Use current Q-Table");
        }
    }

    private void doBestAction() {
        FrozenState currentState = new FrozenState(this.state);
        Action action = getBestAction();
        LOGGER.debug("Best action is {} at {}", action, currentState.toString());
        if (!action.isStillAction()) {
            actionHistory.add(action);
            if (functionalityExecutor.getFunctionalitySignature(action.getName()) != null) {
                functionalityExecutor.invokeFunctionality(action.getName(), action.getArguments());
            } else {
                functionalityExecutor.invokeRemoteFunctionality(action.getName(), action.getArguments());
            }
        }

        scheduler.schedule(() -> {
            // State of action execution (hopefully action takes effect in 3 seconds)
            FrozenState newState = new FrozenState(this.state);
            QTable qTable = qTableManager.getQTable(currentTask);

            Double expectedFutureReward = qTable.get(newState).get(getBestAction());

            if (!currentState.equals(newState)) {
                ScheduledFuture<?> future = scheduler.schedule(() -> {
                    updateQValue(currentState, action, expectedFutureReward, POSITIVE_REWARD);
                }, 60 - 3, TimeUnit.SECONDS);
                ActionResult actionResult = new ActionResult(action, currentState, expectedFutureReward, future);
                actionResults.add(actionResult);
            } else {
                // If the action does not cause state transition, it is not preferred
                if (!action.equals("Still")) {
                    updateQValue(currentState, action, expectedFutureReward, NEGATIVE_REWARD);
                }
            }
        }, 3, TimeUnit.SECONDS);
    }

    private Action getBestAction() {
        Random random = new Random();
        QTable qTable = qTableManager.getQTable(currentTask);
        Map<Action, Double> actionValue = qTable.get(new FrozenState(state));

        synchronized (qTable) {
            Double maxQValue = null;
            Action bestAction = null;

            if (random.nextDouble() < RANDOM_ACTION_CHANCE) {
                while (true) {
                    bestAction = (Action) actionValue.keySet().toArray()[random.nextInt(actionValue.size())];
                    if (isValidAction(bestAction)) return bestAction;
                }
            } else {
                for (Action action : actionValue.keySet()) {
                    if ((maxQValue == null || maxQValue < actionValue.get(action)) && isValidAction(action)) {
                        maxQValue = actionValue.get(action);
                        bestAction = action;
                    }
                }
            }
            return bestAction;
        }
    }

    private boolean isValidAction(Action action) {
        for (Action pastAction : actionHistory) {
            if (action.isOpposite(pastAction)) {
                return false;
            }
        }
        return true;
    }

    private void initializeQTables() {
        ConcurrentMap<String, QTable> qTables = qTableManager.getQTables();
        qTables.clear();
        visitCounts.clear();

        qTables.put(currentTask, new QTable());
        visitCounts.put(currentTask, new ConcurrentHashMap<>());
    }

    private void constructStateSpace(String name, Object value) {
        ConcurrentMap<String, QTable> qTables = qTableManager.getQTables();
        if (!seenContexts.contains(name)) {
            LOGGER.debug("Context first seen: {}", name);
            synchronized (qTables) {
                for (String task : qTables.keySet()) {
                    QTable qTable = qTables.get(task);
                    Set<FrozenState> states = qTable.getStates();

                    for (FrozenState oldState : states) {
                        qTable.put(oldState.plus(name,value), qTable.get(oldState));
                        qTable.remove(oldState);
                    }
                }
            }
            seenContexts.add(name);
        }
    }
}

