package kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning;

import com.google.gson.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

/**
 * Created by JWP on 2017. 8. 30..
 */
public class QTableParser {
    private static final Logger LOGGER = LoggerFactory.getLogger(QTableParser.class);

    /**
     * Get keys from the given JsonObject
     */

    List<String> getJsonKeys(JsonObject obj) {
        List<String> keys = obj.entrySet()
                .stream()
                .map(Map.Entry::getKey)
                .collect(Collectors.toCollection(ArrayList::new));
        return keys;
    }

    /**
     * Convert the given string to FrozenState
     */

    FrozenState parseFrozenState(String frozenStateStr) {
        String frozenStateStr2= frozenStateStr.replace("{", "").replace("}", "");
        String[] frozenStateParsedList = frozenStateStr2.split(",");

        ConcurrentMap<String, Object> state = new ConcurrentHashMap<>();

        for (String frozenStateParsed: frozenStateParsedList) {
            frozenStateParsed = frozenStateParsed.trim();

            String[] pair = frozenStateParsed.split("=");
            state.put(pair[0], pair[1]);  //TO-DO: type of pair[1]?? int or string?
        }

        return new FrozenState(state);
    }

    /**
     * Convert the given JsonObject to Map which is a value for FrozenState.
     */

    Map<String, Double> parseFrozenStateValue(JsonObject jsonObj) {
        List <String> keys = getJsonKeys(jsonObj);
        Map<String, Double> map = new HashMap<>();

        for (String key : keys) {
            map.put(key, jsonObj.get(key).getAsDouble());
        }

        return map;
    }

    /**
     * Get context names from frozen state
     *
     * Ex)
     * FrozenState => {A=0, B=1, C=3}
     * Contexts => {A,B,C}
     */

    Set<String> getContextsFromFrozenState(String frozenStateStr) {
        Set<String> result = new HashSet<>();

        String frozenStateStr2= frozenStateStr.replace("{", "").replace("}", "");
        String[] frozenStateParsedList = frozenStateStr2.split(",");

        ConcurrentMap<String, Object> state = new ConcurrentHashMap<>();

        for (String frozenStateParsed: frozenStateParsedList) {
            frozenStateParsed = frozenStateParsed.trim();

            String contextName = frozenStateParsed.split("=")[0];
            result.add(contextName);
        }

        return result;
    }

}
