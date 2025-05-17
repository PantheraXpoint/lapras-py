package kr.ac.kaist.cdsn.lapras.agents.alert;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.QueryParam;
import java.text.SimpleDateFormat;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentMap;

/**
 * Created by Daekeun Lee on 2017-01-16.
 */
@Path("/")
public class WebhookResource {
    private static final Logger LOGGER = LoggerFactory.getLogger(WebhookResource.class);

    @GET
    @Path("/stat")
    @Produces("application/json")
    public String status(@QueryParam("token") String token,
                          @QueryParam("team_id") String teamId,
                          @QueryParam("team_domain") String teamDomain,
                          @QueryParam("channel_id") String channelId,
                          @QueryParam("channel_name") String channelName,
                          @QueryParam("user_id") String userId,
                          @QueryParam("user_name") String userName,
                          @QueryParam("command") String command,
                          @QueryParam("text") String text,
                          @QueryParam("response_url") String responseURL) {
        StringBuilder stringBuilder = new StringBuilder();
        stringBuilder.append(String.format("Greetings, @%s. Here are the status of known agents:", userName));
        ConcurrentMap<String, Boolean> statusMap = AlertAgent.getInstance().getStatusMap();
        ConcurrentMap<String, Long> lastAliveTimestampMap = AlertAgent.getInstance().getLastAliveTimestamp();

        List<String> agentNames = new ArrayList<>(statusMap.size());
        agentNames.addAll(statusMap.keySet());
        Collections.sort(agentNames);
        for (String agentName : agentNames) {
            Boolean status = statusMap.get(agentName);
            Long lastAliveTimestamp = lastAliveTimestampMap.get(agentName);
            stringBuilder.append(String.format("\n*%s*: %s", agentName, status ? "Alive" : "Dead"));
            if(lastAliveTimestamp != null) {
                stringBuilder.append(String.format("; last heartbeat at <!date^%d^{date_num} {time_secs}|%s> (%s ago)",
                        lastAliveTimestamp / 1000,
                        new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date(lastAliveTimestamp)),
                        Duration.between(Instant.ofEpochMilli(lastAliveTimestamp), Instant.now()).abs().toString()));
            }
        }
        return stringBuilder.toString();
    }
}
