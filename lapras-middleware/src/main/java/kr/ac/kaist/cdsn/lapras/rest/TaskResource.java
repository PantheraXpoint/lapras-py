package kr.ac.kaist.cdsn.lapras.rest;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import kr.ac.kaist.cdsn.lapras.task.TaskInstance;
import org.glassfish.grizzly.http.server.Request;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;

/**
 * Created by JWP on 2018. 4. 4..
 */
@Path("/task")
public class TaskResource {
    @Context
    private Request request;

    @GET
    @Produces("application/json")
    public String listTasks() {
        Gson gson = new Gson();
        JsonArray result = new JsonArray();
        for(TaskInstance taskInstance : RestServer.getInstance(request.getLocalPort()).getAgent().getTaskManager().listTasks()) {
            result.add(gson.toJsonTree(taskInstance));
        }
        return result.toString();
    }
}
