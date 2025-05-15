package kr.ac.kaist.cdsn.lapras.agents.alert;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.communicator.MqttTopic;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.glassfish.grizzly.http.server.HttpServer;
import org.glassfish.jersey.grizzly2.httpserver.GrizzlyHttpServerFactory;
import org.glassfish.jersey.server.ResourceConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.net.ssl.HttpsURLConnection;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.*;
import java.util.Set;
import java.util.concurrent.*;

/**
 * Created by Daekeun Lee on 2017-01-10.
 */
public class AlertAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(AlertAgent.class);

    private static AlertAgent instance = null;

    private String token;
    private String managers_filename;

    private final ScheduledExecutorService aliveExpierer = Executors.newScheduledThreadPool(1);
    private ConcurrentMap<String, Set<String>> managerMap;
    private final ConcurrentMap<String, Long> lastAliveTimestamp = new ConcurrentHashMap<>();
    private final ConcurrentMap<String, Boolean> statusMap = new ConcurrentHashMap<>();
    private static final ConcurrentMap<String, String> userIdMap = new ConcurrentHashMap<>();

    private HttpServer webhookServer;

    public AlertAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
        instance = this;
    }

    public static AlertAgent getInstance() {
        return instance;
    }

    @Override
    public void run() {
        token = agent.getAgentConfig().getOption("slack_bot_token");
        if(token == null) {
            LOGGER.error("The bot token must be specified as slack_bot_token");
            return;
        }

        managers_filename = agent.getAgentConfig().getOption("managers_file");
        if (managers_filename == null) {
            LOGGER.error("The manager list file must be specified as manager_file");
            return;
        }

        managerMap = loadManagerList(managers_filename);

        contextManager.subscribeContext(MqttTopic.MULTILEVEL_WILDCARD);

        String webhookPort = agent.getAgentConfig().getOptionOrDefault("webhook_port", "8888");
        URI uri;
        ResourceConfig resourceConfig = new ResourceConfig()
                .register(WebhookResource.class);
        try {
            uri = new URI("http://0.0.0.0:" + webhookPort);
            webhookServer = GrizzlyHttpServerFactory.createHttpServer(uri, resourceConfig);
            webhookServer.start();
            LOGGER.info("Webhook server launched on {}", uri);
        } catch (IOException e) {
            LOGGER.error("An error occurred while starting the webhook server", e);
            return;
        } catch (URISyntaxException e) {
            LOGGER.error("Failed to parse URI", e);
            return;
        }

        while(true) {
            try {
                Thread.sleep(Integer.MAX_VALUE);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    public ConcurrentMap<String, Long> getLastAliveTimestamp() {
        return lastAliveTimestamp;
    }

    public ConcurrentMap<String, Boolean> getStatusMap() {
        return statusMap;
    }

    private ConcurrentMap<String,Set<String>> loadManagerList(String managers_filename) {
        JsonParser jsonParser = new JsonParser();
        JsonArray agentManagersList = jsonParser.parse(new InputStreamReader(Resource.getStream(managers_filename))).getAsJsonArray();
        ConcurrentMap<String, Set<String>> managerMap = new ConcurrentHashMap<>();
        for (JsonElement e : agentManagersList) {
            CopyOnWriteArraySet<String> managerSet = new CopyOnWriteArraySet<>();
            for (JsonElement managerName : e.getAsJsonObject().getAsJsonArray("managers")) {
                managerSet.add(managerName.getAsString());
            }
            managerMap.put(e.getAsJsonObject().get("agent").getAsString(), managerSet);
        }
        return managerMap;
    }

    @Override
    public boolean handleEvent(Event event) {
        switch(event.getType()) {
            case CONTEXT_UPDATED:
                ContextInstance contextInstance = (ContextInstance) event.getData();
                if(contextInstance.getName().endsWith(OPERATING_STATUS_SUFFIX)) {
                    String agentName = contextInstance.getPublisher();
                    if(managerMap.containsKey(agentName)) {
                        if (contextInstance.getValue().equals("Alive")) {
                            if (statusMap.get(agentName) == Boolean.FALSE) {
                                notifyManagers(agentName, String.format("*%s* came back alive.", agentName));
                            }
                            lastAliveTimestamp.put(agentName, contextInstance.getTimestamp());
                            statusMap.put(agentName, true);
                            aliveExpierer.schedule(() -> {
                                if (lastAliveTimestamp.get(agentName) == contextInstance.getTimestamp()) {
                                    statusMap.put(agentName, false);
                                    notifyManagers(agentName, String.format("Operating status of *%s* has not been reported for %d seconds.",
                                            contextInstance.getPublisher(), AgentComponent.OPERATING_STATUS_INTERVAL * 2));
                                }
                            }, AgentComponent.OPERATING_STATUS_INTERVAL * 2, TimeUnit.SECONDS);
                        } else if (contextInstance.getValue().equals("Dead")) {
                            statusMap.put(agentName, false);
                            notifyManagers(agentName, String.format("*%s* is reported to be dead now.", contextInstance.getPublisher()));
                        }
                    }
                }
        }
        return true;
    }

    private void notifyManagers(String agentName, String message) {
        Set<String> managers = managerMap.get(agentName);
        if (managers == null) {
            LOGGER.error("No managers specified for agent {}", agentName);
            return;
        }

        for (String manager : managers) {
            try {
                sendDM(manager, message);
            } catch (IOException e) {
                LOGGER.error("Failed to send a direct message");
            }
        }
    }

    private JsonObject getAsJsonObject(String urlString) {
        try {
            URL url = new URL(urlString);
            HttpsURLConnection con = (HttpsURLConnection) url.openConnection();
            BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(con.getInputStream()));

            StringBuilder stringBuilder = new StringBuilder();
            String line;
            while((line = bufferedReader.readLine()) != null) {
                stringBuilder.append(line);
            }
            JsonObject json = new JsonParser().parse(stringBuilder.toString()).getAsJsonObject();
            return json;
        } catch (MalformedURLException e) {
            LOGGER.error("Failed to parse url: {}", urlString, e);
        } catch (IOException e) {
            LOGGER.error("An error occurred while connecting to {}", urlString, e);
        }
        return null;
    }

    private String getUserIdFromName(String username) throws IOException {
        String userId = userIdMap.get(username);
        if(!userIdMap.containsKey(username)) {
            String usersListUrl = "https://slack.com/api/users.list?token=" + token;
            JsonObject usersList = getAsJsonObject(usersListUrl);
            if (usersList == null || usersList.get("ok").getAsBoolean() != true) {
                throw new IOException("Failed to retrieve user list");
            }
            for (JsonElement member : usersList.getAsJsonArray("members")) {
                JsonObject memberObject = member.getAsJsonObject();
                userIdMap.put(memberObject.get("name").getAsString(), memberObject.get("id").getAsString());
            }
        }
        return userIdMap.get(username);
    }

    private void sendDM(String username, String message) throws IOException {
        String userId = getUserIdFromName(username);
        if(userId == null) {
            throw new IllegalArgumentException("There is no such user: " + username);
        }

        JsonObject imOpenResponse = getAsJsonObject("https://slack.com/api/im.open?token=" + token + "&user=" + userId);
        if(imOpenResponse == null || imOpenResponse.get("ok").getAsBoolean() != true) {
            throw new IOException("Failed to open a DM channel");
        }
        String channelId = imOpenResponse.getAsJsonObject("channel").get("id").getAsString();

        String chatPostMessageUrl = "https://slack.com/api/chat.postMessage?token=" + token
                + "&channel=" + channelId
                + "&text=" + URLEncoder.encode(message, "UTF-8");
        JsonObject chatPostMessageResponse = getAsJsonObject(chatPostMessageUrl);
        if(chatPostMessageResponse == null || chatPostMessageResponse.get("ok").getAsBoolean() != true) {
            throw new IOException("Failed to post a message to " + username);
        }
    }
}
