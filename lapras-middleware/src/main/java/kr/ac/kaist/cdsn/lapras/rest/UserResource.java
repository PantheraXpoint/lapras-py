package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import org.glassfish.grizzly.http.server.Request;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;
import java.util.concurrent.ConcurrentMap;

/**
 * Created by JWP on 2018. 4. 3..
 */
@Path("/user")
public class UserResource {
    @Context
    private Request request;

    @GET
    @Produces("application/json")
    public String listUsers() {
        Gson gson = new Gson();
        JsonArray result = new JsonArray();

        ConcurrentMap<String, Boolean> userPresenceMap = RestServer.getInstance(request.getLocalPort()).getAgent().getUserManager().getUserPresenceMap();
        result.add(gson.toJson(userPresenceMap));
        return result.toString();
    }

}
