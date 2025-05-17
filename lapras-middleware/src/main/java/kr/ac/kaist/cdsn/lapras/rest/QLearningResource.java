package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import kr.ac.kaist.cdsn.lapras.preference.PreferenceLearner;
import kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning.FrozenState;
import kr.ac.kaist.cdsn.lapras.preference.algorithm.qlearning.QLearning;
import org.glassfish.grizzly.http.server.Request;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;

@Path("/qlearning")
public class QLearningResource {
    @Context
    private Request request;

    @GET @Path("/{task}")
    @Produces("application/json")
    public String listContexts(@PathParam("task") String taskName) {
        /*PreferenceLearner preferenceLearner = RestServer.getInstance(request.getLocalPort()).getAgent().getComponent(PreferenceLearner.class);
        ConcurrentMap<FrozenState, Map<String, Double>> qTable = ((QLearning) preferenceLearner.getLearningAlgorithm()).getQTable(taskName);
        if(qTable == null) return "";

        JsonArray result = new JsonArray();
        for (FrozenState state : qTable.keySet()) {
            JsonObject node = new JsonObject();
            node.addProperty("id", state.hashCode());
            node.addProperty("label", state.toString());
            JsonArray actions = new JsonArray();
            for (String actionName : qTable.get(state).keySet()) {
                JsonObject action = new JsonObject();
                action.addProperty("name", actionName);
                action.addProperty("qValue", qTable.get(state).get(actionName));
                actions.add(action);
            }
            node.add("actions", actions);
            result.add(node);
        }
        return result.toString();*/
        return null;
    }
}
