package kr.ac.kaist.cdsn.lapras.preference.algorithm;

import kr.ac.kaist.cdsn.lapras.action.Action;

/**
 * Created by Daekeun Lee on 2017-04-07.
 */
public interface LearningAlgorithm {
    void taskNotified(String name);
    void actionTaken(Action action);
    void contextUpdated(String name, Object value);
    void userNotified(String name);
    void enableSave(String filename, int period);
    void loadLearnedModel(String filename);
}
