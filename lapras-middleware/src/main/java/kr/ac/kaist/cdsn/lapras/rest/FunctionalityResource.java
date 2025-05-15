package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalitySignature;
import org.glassfish.grizzly.http.server.Request;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;

/**
 * Created by Daekeun Lee on 2016-12-01.
 */
@Path("/functionality")
public class FunctionalityResource {
    @Context
    private Request request;

    @GET
    @Produces("application/json")
    public String listFunctionalitySignatures() {
        Gson gson = new Gson();
        JsonArray result = new JsonArray();
        for (FunctionalitySignature signature : RestServer.getInstance(request.getLocalPort()).getAgent().getFunctionalityExecutor().listFunctionalitySignatures()) {
            result.add(gson.toJsonTree(signature));
        }
        return result.toString();
    }

    @GET @Path("/{name}")
    @Produces("application/json")
    public String getFunctionalitySignature(@PathParam("name") String name) {
        Gson gson = new Gson();
        FunctionalitySignature signature = RestServer.getInstance(request.getLocalPort()).getAgent().getFunctionalityExecutor().getFunctionalitySignature(name);
        if(signature == null) {
            return "null";
        } else {
            return gson.toJsonTree(signature).toString();
        }
    }
}
