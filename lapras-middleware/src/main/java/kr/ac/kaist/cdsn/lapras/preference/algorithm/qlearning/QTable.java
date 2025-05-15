package kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning;

import kr.ac.kaist.cdsn.lapras.action.Action;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * Created by JWP on 2018. 6. 7..
 *
 * Class for Q-table abstraction
 *
 */
public class QTable {

    private static final Logger LOGGER = LoggerFactory.getLogger(QTable.class);
    private final ConcurrentMap<FrozenState, ConcurrentHashMap<Action, Double>> qTable;

    public QTable(ConcurrentMap<FrozenState, ConcurrentHashMap<Action, Double>> qTable) {
        this.qTable = qTable;
    }

    public QTable() {
        this.qTable = new ConcurrentHashMap<>();
    }

    public void put(FrozenState state, ConcurrentHashMap<Action, Double> actionValue) {
        qTable.put(state, actionValue);
    }

    public ConcurrentHashMap<Action, Double> get(FrozenState state) {

        if (qTable == null) {
            throw new IllegalStateException("QTable not properly initialized");
        }

        if (!qTable.containsKey(state)) {
            qTable.put(state, addStillAction());
        }
        return qTable.get(state);
    }

    public void remove(FrozenState state) {
        qTable.remove(state);
    }


    public Set<FrozenState> getStates() {
        return qTable.keySet();
    }

    private ConcurrentHashMap<Action, Double> addStillAction() {
        ConcurrentHashMap<Action, Double> map = new ConcurrentHashMap<>();
        map.put(new Action("Still"), 1.0);
        return map;
    }
}
