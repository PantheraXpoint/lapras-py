package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import org.glassfish.grizzly.http.server.Request;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;
import java.util.Iterator;

/**
 * Created by Daekeun Lee on 2017-08-01.
 */
@Path("/")
public class RootResource {
    @Context
    private Request request;

    @GET
    @Produces("application/json")
    public String agentInfo() {
        JsonObject result = new JsonObject();

        Agent agent = RestServer.getInstance(request.getLocalPort()).getAgent();

        AgentConfig agentConfig = agent.getAgentConfig();
        JsonObject configJson = new JsonObject();
        for(Iterator<String> iter = agentConfig.listOptionNames(); iter.hasNext();) {
            String optionName = iter.next();
            String[] optionValue = agentConfig.getOptionAsArray(optionName);
            if(optionValue.length > 1) {
                JsonArray optionValueJson = new JsonArray();
                for (String value : optionValue) {
                    optionValueJson.add(value);
                }
                configJson.add(optionName, optionValueJson);
            } else {
                configJson.addProperty(optionName, optionValue[0]);
            }
        }
        result.add("config", configJson);

        JsonObject connectionJson = new JsonObject();
        JsonArray subscriptionListJson = new JsonArray();
        for (LaprasTopic laprasTopic : agent.getMqttCommunicator().getSubscriptionList()) {
            subscriptionListJson.add(laprasTopic.toString());
        }
        connectionJson.add("subscriptions", subscriptionListJson);

        result.addProperty("uptime", agent.getUptime());

        return result.toString();
    }
}
