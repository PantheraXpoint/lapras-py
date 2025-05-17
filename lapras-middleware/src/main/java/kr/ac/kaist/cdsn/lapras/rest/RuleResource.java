package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import kr.ac.kaist.cdsn.lapras.rule.RuleExecutor;
import org.apache.jena.reasoner.rulesys.ClauseEntry;
import org.apache.jena.reasoner.rulesys.Rule;
import org.glassfish.grizzly.http.server.Request;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;

/**
 * Created by Daekeun Lee on 2016-12-01.
 */
@Path("/rule")
public class RuleResource {
    @Context
    private Request request;

    @GET
    @Produces("application/json")
    public String listRules() {
        JsonArray result = new JsonArray();
        RuleExecutor ruleExecutor = RestServer.getInstance(request.getLocalPort()).getAgent().getComponent(RuleExecutor.class);
        if(ruleExecutor != null) {
            for (Rule rule : ruleExecutor.listRules()) {
                JsonObject ruleObject = new JsonObject();
                ruleObject.addProperty("name", rule.getName());
                JsonArray bodyClauseArray = new JsonArray();
                for (ClauseEntry bodyClauseEntry : rule.getBody()) {
                    bodyClauseArray.add(bodyClauseEntry.toString());
                }
                ruleObject.add("body", bodyClauseArray);
                JsonArray headClauseArray = new JsonArray();
                for (ClauseEntry headClauseEntry : rule.getHead()) {
                    headClauseArray.add(headClauseEntry.toString());
                }
                ruleObject.add("head", headClauseArray);
                result.add(ruleObject);
            }
        }
        return result.toString();
    }
}
