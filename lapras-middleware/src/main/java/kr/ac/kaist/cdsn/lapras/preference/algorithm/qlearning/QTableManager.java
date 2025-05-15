package kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import kr.ac.kaist.cdsn.lapras.action.Action;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * Created by JWP on 2018. 5. 27..
 *
 * Class for
 *  - Loading & saving Q Table from file
 *  - Managing Q Table for group of users
 *  - Manage visitCounts(?)
 */
public class QTableManager {

    private static final Logger LOGGER = LoggerFactory.getLogger(QTableManager.class);
    private final ConcurrentMap<String, QTable> qTables;

    public QTableManager() {
        qTables = new ConcurrentHashMap<>();
    }

    public ConcurrentMap<String, QTable> getQTables() {
        return qTables;
    }

    public QTable getQTable(String task) {

        QTable qTable = qTables.get(task);
        if (qTable == null) {
            qTable = new QTable();
            qTables.put(task, qTable);
            return qTable;
        } else {
            return qTable;
        }
    }

    public void printQTableAll() {
        StringBuilder sb = new StringBuilder();
        for (String task : qTables.keySet()) {
            sb.append(String.format("Task: %s ==============================\n", task));
            QTable qTable = qTables.get(task);

            for (FrozenState frozenState : qTable.getStates()) {
                sb.append(frozenState.toString());
                sb.append("\n");
                for (Action action : qTable.get(frozenState).keySet()) {
                    sb.append(String.format("\t-> %20s: %f\n", "\"" + action.toString() + "\"", qTable.get(frozenState).get(action)));
                }
            }
            sb.append("\n");
            LOGGER.debug("Printing Q table:\n{}", sb.toString());
        }
    }

    public void loadQTables(String fileName) throws IOException {
        /**
         * To-do: save & load visitcounts
         */
        String fileContents = new String(Files.readAllBytes(Paths.get(fileName)));

        qTables.clear();

        QTableParser qTableParser = new QTableParser();
        JsonParser jsonParser = new JsonParser();
        JsonObject jsonObj = (JsonObject)jsonParser.parse(fileContents);

        // Parse Q Table from the given string
        List<String> tasks = qTableParser.getJsonKeys(jsonObj);

        for (String task : tasks) {
            JsonObject jsonObj2 = jsonObj.get(task).getAsJsonObject().get("qTable").getAsJsonObject();
            List<String> frozenStatesStr = qTableParser.getJsonKeys(jsonObj2);

            QTable qTable = new QTable();

            for (String frozenStateStr : frozenStatesStr) {

                JsonObject jsonObj3 = jsonObj2.get(frozenStateStr).getAsJsonObject();

                FrozenState frozenState = qTableParser.parseFrozenState(frozenStateStr);
                //Map<String, Double> frozenStateValue = qTableParser.parseFrozenStateValue(jsonObj3);

                //qTable.put(frozenState, frozenStateValue);
            }

            qTables.put(task, qTable);
        }

        printQTableAll();
    }


    public void saveQTables(String filename) {
        Gson gsonBuilder = new GsonBuilder().disableHtmlEscaping().create();

        String qtable2json = gsonBuilder.toJson(qTables);

        List<String> lines = Arrays.asList(qtable2json);
        Path file = Paths.get(filename);

        try {
            Files.write(file, lines, Charset.forName("UTF-8"));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
