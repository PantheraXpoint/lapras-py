package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import org.glassfish.grizzly.http.server.Request;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;

/**
 * Created by Daekeun Lee on 2016-12-01.
 */
@Path("/context")
public class ContextResource {
    @Context
    private Request request;

    @GET
    @Produces("application/json")
    public String listContexts() {
        Gson gson = new Gson();
        JsonArray result = new JsonArray();
        for(ContextInstance contextInstance : RestServer.getInstance(request.getLocalPort()).getAgent().getContextManager().listContexts()) {
            result.add(gson.toJsonTree(contextInstance));
        }
        return result.toString();
    }

    @GET @Path("/{name}")
    @Produces("application/json")
    public String getContext(@PathParam("name") String name) {
        Gson gson = new Gson();
        ContextInstance contextInstance = RestServer.getInstance(request.getLocalPort()).getAgent().getContextManager().getContext(name);
        if(contextInstance == null) {
            return "null";
        } else {
            return gson.toJsonTree(contextInstance).toString();
        }
    }
}
