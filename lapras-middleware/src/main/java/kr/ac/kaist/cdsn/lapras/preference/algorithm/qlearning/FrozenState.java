package kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning;

import org.apache.commons.lang.builder.HashCodeBuilder;

import java.util.Collections;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

/**
 * Created by Daekeun Lee on 2017-04-10.
 */
public class FrozenState {
    private final SortedMap<String, Object> stateMap;

    public FrozenState(Map<String, Object> stateMap) {
        this.stateMap = Collections.unmodifiableSortedMap(new TreeMap<>(stateMap));
    }

    @Override
    public boolean equals(Object other) {
        if(!(other instanceof FrozenState) ||
                stateMap.size() != ((FrozenState)other).stateMap.size()) {
            return false;
        }
        if(other == this) {
            return true;
        }

        for (String name : stateMap.keySet()) {
            if(!((FrozenState) other).stateMap.containsKey(name) ||
                    !((FrozenState) other).stateMap.get(name).equals(stateMap.get(name))) {
                return false;
            }
        }
        return true;
    }

    @Override
    public int hashCode() {
        HashCodeBuilder builder = new HashCodeBuilder();
        for (String name : stateMap.keySet()) {
            builder.append(name);
            builder.append(stateMap.get(name));
        }
        return builder.toHashCode();
    }

    public FrozenState plus(String key, Object value) {
        SortedMap<String, Object> map = new TreeMap<>(stateMap);
        map.put(key, value);
        return new FrozenState(map);
    }

    @Override
    public String toString() {
        return stateMap.toString();
    }
}
