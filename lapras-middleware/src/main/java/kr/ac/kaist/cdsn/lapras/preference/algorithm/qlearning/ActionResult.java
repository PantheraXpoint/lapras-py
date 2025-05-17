package kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning;

import kr.ac.kaist.cdsn.lapras.action.Action;

import java.util.concurrent.ScheduledFuture;

/**
 * Created by Daekeun Lee on 2017-04-20.
 */
public class ActionResult {
    private Action action;
    private FrozenState currentState;
    private double expectedFutureReward;
    private ScheduledFuture future;

    public ActionResult(Action action, FrozenState currentState, double expectedFutureReward, ScheduledFuture future) {
        this.action = action;
        this.currentState = currentState;
        this.expectedFutureReward = expectedFutureReward;
        this.future = future;
    }

    public Action getAction() {
        return action;
    }

    public FrozenState getCurrentState() {
        return currentState;
    }

    public double getExpectedFutureReward() {
        return expectedFutureReward;
    }

    public ScheduledFuture getFuture() {
        return future;
    }
}
